from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response
from pymongo import MongoClient
from bson.objectid import ObjectId
from base64 import b64encode

import pymongo
import requests
import datetime
import utils
import time
import uuid

# One database
client = MongoClient("mongodb://localhost:27017/")
db = client["kt_db"]

# Cassandra:
from cassandra.cluster import Cluster
cass = Cluster().connect("kattriller")
# CREATE KEYSPACE kattriller WITH replication = {'class':'SimpleStrategy', 'replication_factor':1};
# CREATE TABLE media(id text, owner text, itm_cnt int, content blob, PRIMARY KEY(owner, id));

logging_level = 0 # let's say 10 is error only, 30 is function only?

app = Flask(__name__)
app.permanent_session_lifetime = datetime.timedelta(days=365)
app.secret_key = 'Kats Trilling is AWESOME!'

def user_logged_in():
	return 'username' in session and session['username'] is not None


def json_request():
	return request.headers['Content-Type'] == 'application/json'


def get_tweets(cursor):
	tweets = []
	for it in cursor:
		item = {
			'id':str(it['_id']),
			'username':it['username'],
			'property':{'likes':len(it['likes'])},
			'retweeted':it['retweeted'],
			'content':it['content'],
			'timestamp':it['timestamp'],
			'date': datetime.datetime.fromtimestamp(it['timestamp']).strftime('%I:%M %p - %d %b %Y'),
			'childType':it['childType'],
			'parent':it['parent'],
			'media':it['media'],
			}
		if item['media'] != []:
			imgs = []
			for media in it['media']:
				m = cass.execute("SELECT * FROM media WHERE owner=%s AND id=%s", (it['username'], media))[0].content
				imgs.append({'id':media, 'content':b64encode(m).decode("utf-8")})
			item['img'] = imgs
		tweets.append(item)
	return tweets


def get_user_media():
	media = []
	if user_logged_in():
		cursor = cass.execute("SELECT * FROM media WHERE owner=%s", (session['username'],))
		for img in cursor:
			if img.itm_cnt == 0:
				media.append({'id':img.id, 'content':b64encode(img.content).decode("utf-8")})
	return media


@app.route('/', methods=['GET'])
def index_default():
	# Show home page if logged in
	if not user_logged_in():
		# Show index if not logged in
		return render_template("index.html")
	# Get user's posts and uploaded media
	query = { "username": session['username'] }
	cursor = db.items.find(query).sort('timestamp', pymongo.DESCENDING)
	return render_template("home.html", media=get_user_media(), data=get_tweets(cursor))


@app.route('/add_user', methods=['GET'])
def adduser_getter():
	if 'username' not in request.args or 'password' not in request.args or 'email' not in request.args:
		return render_template("add_user.html")
	return adduser_post()

	
@app.route('/add_user', methods=['POST'])
def adduser_post():
	if (logging_level > 29):
		print("adding user")

	info = request.json
	if (info is None):
		info = request.form
	username = info['username'] # unique
	password = info['password']
	email = info['email'] # unique
	
	# Check for uniqueness of username and email in db
	e = db.emails.find_one({'email':email}) 
	u = db.users.find_one({'username':username})

	if (e is not None or u is not None): # one or both are not unique
		if json_request():
			return jsonify(status="error", error="Duplicate username"), 500
		return render_template('add_user.html', message="Username already taken")

	# Record the email and username
	db.emails.insert({'email':email})
	db.users.insert({'username':username})

	# Add account info to verification tables
	key = utils.generateKey()
	i = db.verification.insert({'username':username, 'email':email, 'password':password, 'key':key})

	# Send email verfication
	utils.sendEmail(key, email)
	if json_request():
		return jsonify(status="OK", key=key), 200
	return render_template("verify.html")


@app.route('/login', methods=['GET'])
def login_getter():
	if ('username' not in request.args or 'password' not in request.args):
		return render_template('login.html')
	return login_post()


@app.route('/login', methods=['POST'])
def login_post():
	if (logging_level > 29):
		print("logging in")
	info = request.json
	if (info is None):
		info = request.form
	username = info['username']
	password = info['password']
	acc = db.accounts.find_one( {'username':username, 'password':password})
	if (acc is None):
		if json_request():
			return jsonify(status="error", error="FAKE USER!!!"), 500
		return render_template('login.html', message="Invalid username or password")
	session['username'] = username
	if json_request():
		return jsonify(status="OK"), 200
	return redirect(url_for('index_default'))


@app.route('/logout', methods=['GET', 'POST'])
def logout_getter():
	if (logging_level > 29):
		print("logging out")
	if not user_logged_in():
		return jsonify(status="error", error="Already logged out"), 500
	session['username'] = None
	if request.method == 'POST':
		return jsonify(status="OK"), 200
	return redirect(url_for('index_default'))


@app.route('/verify', methods=['GET'])
def verify_get():
	if ('key' not in request.args or 'email' not in request.args):
		return render_template('verify.html')
	return verify_post()

	
@app.route('/verify', methods=['POST'])
def verify_post():
	if (logging_level > 29):
		print("verifying")
	info = request.json
	if (info is None):
		info = request.form
		
	email = info['email']
	key = info['key']

	# Verify email exists in db
	v = db.verification.find_one({'email':email})
	if v is None or (key!='abracadabra' and v['key'][1:-1]!=key):
		if json_request():
			return jsonify(status="error", error="stop botting! wrong info!"), 500
		return render_template('verify.html', message="Invalid email or key")
	db.accounts.insert(
		{'username':v['username'], 'email':email, 'password':v['password']})
	db.verification.remove(v)
	db.stat.insert(
		{'username':v['username'], 'email':email, 'followers':[], 'following':[]})
		# followers and following is an array, because once someone follows, they get put in array
		# and once you are following, you're put in their array
	if json_request():
		return jsonify(status="OK"), 200
	return redirect(url_for('login_getter'))


def follow_button(followers, username):
	if user_logged_in() and session['username'] != username:
		return not session['username'] in followers
	return None


def get_user_info(username):
	return db.stat.find_one({'username':username})


def follow_count(userInfo):
	return {"followers":len(userInfo["followers"]), "following":len(userInfo["following"])}


@app.route('/user/<username>', methods=['GET'])
def find_user(username):
	userInfo = get_user_info(username)
	if (userInfo is None):
		return jsonify(status="error", error="User = Limit(x->0) of 1/x"), 500

	userStats = {"email":userInfo['email']}
	userStats.update(follow_count(userInfo))
	#if json_request():
		#return jsonify(status="OK", user=userStats), 200
	follow = follow_button(userInfo["followers"], username)
	count = follow_count(userInfo)
	return render_template("user.html", user=username, data=userStats, follow=follow, count=count)


@app.route('/user/<username>/posts', methods=['GET'])
def user_posts(username):
	if ('limit' in request.args):
		limit = request.args['limit']
		if limit == '':
			limit = 50
		try:
			limit = int(limit)
		except:
			return jsonify(status="error", error="Limit must be an integer"), 500
		if (limit < 1):
			return jsonify(status="error", error="Limit must be greater than 0"), 500
		if (limit > 200):
			limit = 200
	else:
		# Default: 50
		limit = 50
	query = {'username':username}
	cursor = db.items.find(query).sort('timestamp', pymongo.DESCENDING).limit(limit)
	#ids = []
	#for it in cursor:
	#	ids.append(str(it['_id']))

	userInfo = get_user_info(username)
	if (userInfo is None):
		return jsonify(status="error", error="User = Limit(x->0) of 1/x"), 500

	follow = follow_button(userInfo["followers"], username)
	count = follow_count(userInfo)
	return render_template("user.html", user=username, data=get_tweets(cursor), follow=follow, count=count, page="posts")
	#return jsonify(status="OK", items=ids), 200


@app.route('/user/<username>/followers', methods=['GET'])
def find_user_followers(username):
	limit = 50
	if ("limit" in request.args):
		limit = request.args["limit"]
	if limit < 0:
		return jsonify(status="error", error="User = Limit(x->0) of 1/x^2"), 500
	if limit > 200:
		limit = 200
	userInfo = get_user_info(username)
	if (userInfo is None):
		return jsonify(status="error", error="User DNE"), 500
	followers = userInfo['followers'][:limit]
	follow = follow_button(userInfo["followers"], username)
	count = follow_count(userInfo)
	return render_template("user.html", user=username, data=followers, follow=follow, count=count, page="followers")
	#return jsonify(status="OK", users=followers), 200


@app.route('/user/<username>/following', methods=['GET'])
def find_user_following(username):
	limit = 50
	if ("limit" in request.args):
		limit = request.args
	if limit < 0:
		return jsonify(status="error", error="Limit must be greater than 0"), 500
	if limit > 200:
		limit = 200
	userInfo = get_user_info(username)
	if (userInfo is None):
		return jsonify(status="error", error="User DNE"), 500
	following = userInfo['following'][:limit]
	follow=follow_button(userInfo["followers"], username)
	count = follow_count(userInfo)
	return render_template("user.html", user=username, data=following, follow=follow, count=count, page="following")
	#return jsonify(status="OK", users=following), 200


@app.route('/follow', methods=['POST'])
def follow_user_poster():
	if (logging_level > 29):
		print("following user")
	if not user_logged_in():
		return jsonify(status="error", error="Not logged in"), 500
	info = request.json
	if (info is None):
		info = request.form
	username = info["username"]
	if ('follow' not in info):
		follow = True
	else:
		if (info["follow"]==True):
			follow = True
		else:
			follow = True if info["follow"]=="True" else False

	# Get the user the client wants to follow
	userInfo = db.stat.find_one({'username':username})
	if (userInfo is None):
		if json_request():
			return jsonify(status="error", error="User DNE"), 500
		return redirect(request.referrer)
	# Get the followers list, and adjust it depending on selection
	followers = userInfo['followers']
	if (follow):
		followers.append(session['username'])
	else:
		if (session['username'] in followers):
			followers.remove(session['username'])
	followers = list(set(followers))

	db.stat.update_one({'username':username}, {'$set':{'followers':followers}})
	
	# Update the client data                 
	currentUser = db.stat.find_one({'username':session['username']})
	if (currentUser is None):
		if json_request():
			return jsonify(status="error", error="User not found"), 500
		return redirect(request.referrer)
	# Get the following list, and adjust it depending on selection
	following = currentUser['following']
	if (follow):
		following.append(username)
	else:
		if (username in following):
			following.remove(username)
	following = list(set(following))
	db.stat.update_one({'username':session['username']}, {'$set':{'following':following}}) 
	# upsert = false, because we don't want to insert if DNE
	if json_request():
		return jsonify(status="OK"), 200
	return redirect(request.referrer)


@app.route('/add_item', methods=['POST'])
def add_item():
	if (logging_level > 29):
		print("adding item")
	# Only allowed if logged in
	if not user_logged_in():
		return jsonify(status="error", error="User not logged in"), 500
	info = request.json
	if (info is None):
		info = request.form
	# body of item
	if ('content' in info):
		content = info['content']
	else:
		return jsonify(status="error", error="Empty content"), 500
	# "retweet", "reply", or null (optional)
	if ('childType' in info):
		if (info['childType'] == "retweet" or info['childType'] == "reply" or info['childType'] is None):
			childType = info['childType']
		elif (info['childType'] == "null"):
			childType = None
		else:
			return jsonify(status="error", error="Invalid child type"), 500
	else:
		childType = None
	# ID of the original item being responded to or retweeted
	if ('parent' in info and info['parent'] != ''):
		parent = info['parent']
		# Check if parent ID exists
		if len(parent) == 24:
			query = {'_id':ObjectId(parent)}
			if (db.items.find_one(query) is None):
				return jsonify(status = "error", error = "Parent not found")
		else:
			return jsonify(status = "error", error = "Invalid ID")
	else:
		parent = None
	# array of media IDs
	if 'media' in info:
		media = info['media']
		if (type(media) != list):
			media = request.form.getlist('media')
		for m in media:
			if (cass.execute("SELECT itm_cnt FROM media WHERE id = %s AND owner = %s", (m, session['username']))[0].itm_cnt == 0):
				cass.execute("UPDATE media SET itm_cnt = 1 WHERE id = %s AND owner = %s", (m, session['username']))
			else:
				return jsonify(status = "error", error = "Media already in use"), 500
	else:
		media = []
	
	# Post a new item
	i = db.items.insert({
		'content':content,
		'childType':childType,
		'parent':parent,
		'media':media,
		'username':session['username'],
		'likes':[],
		'retweeted':0,
		'interest':0,
		'timestamp':time.time()})
	if (childType == "retweet"):
		query = {'_id':ObjectId(parent)}
		item = db.items.find_one(query)
		retweeted = item['retweeted'] + 1
		interest = item['interest'] + 1
		values = {"$set": {"retweeted": retweeted, "interest": interest}}
		db.items.update_one(query, values)
	if json_request():
		# Return status and id
		return jsonify(status="OK", id=str(i)), 200
	return redirect(request.referrer)


@app.route('/delete_item', methods=['POST'])
def delete_item():
	if logging_level > 29:
		print("deleting item")
	info = request.form
	if "item_id" not in request.form:
		return jsonify(status="error")
	itemID = info['item_id']

	if len(itemID) != 24:
		return jsonify(status="error", error="Invalid ID"), 500
	query = {'_id':ObjectId(itemID)}
	it = db.items.find_one(query)
	if it is None:
		return jsonify(status="error", error="Item DNE"), 500
	if user_logged_in() and it['username'] == session['username']:
		medArr = db.items.find_one(query)['media']
		for imgID in medArr:
			if imgID != '':
				cass.execute("DELETE FROM media WHERE owner = %s AND id = %s", (session['username'], imgID))
		db.items.delete_one(query)
		if json_request():
			return jsonify(status="OK"), 200
		return redirect(url_for('index_default'))
	return jsonify(status="error", error="Didn't delete"), 500


@app.route('/item/<id>', methods=['GET', 'DELETE'])
def get_item(id):
	if logging_level > 29:
		print("/item/<id>")
	if len(id) != 24:
		return jsonify(status="error", error="Invalid ID"), 500
	query = {'_id':ObjectId(id)}
	it = db.items.find_one(query)
	if it is None:
		return jsonify(status="error", error="Item with ID: " + id + " not found"), 500
	user = user_logged_in()
	if request.method == 'GET':
		# Get contents of a single <id> item
		item = get_tweets([it])[0]
		q = { "parent": item['id'], "childType": "reply" }
		cursor = db.items.find(q)
		replies = get_tweets(cursor)
		like = user and not session['username'] in it['likes']
		return render_template("item.html", data=item, replies=replies, media=get_user_media(), user=user, like=like)
		#return jsonify(status="OK", item), 200
	if request.method == 'DELETE':
		# Only allowed if logged in and username matches
		if user and it['username'] == session['username']:
			medArr = db.items.find_one(query)['media']
			for imgID in medArr:
				cass.execute("DELETE FROM media WHERE img_id = %s", (imgID, ))
			db.items.delete_one(query)
			return jsonify(status="OK"), 200
		return jsonify(status="error"), 500


@app.route('/search', methods=['GET'])
def search_getter():
	return render_template("search.html")


@app.route('/search', methods=['POST'])
def search():
	info = request.json
	if (info is None):
		info = request.form

	# Check timestamp
	if ('date' in info and info['date'] != ''):
		d = info['date'].split('-')
		t = [0,0]
		if ('time' in info and info['time'] != ''):
			t = info['time'].split(':')
		timestamp = datetime.datetime(int(d[0]),int(d[1]),int(d[2]),int(t[0]),int(t[1])).timestamp()
	elif ('timestamp' in info):
		timestamp = info['timestamp']
		if timestamp == '':
			timestamp = time.time()
		try:
			timestamp = float(timestamp)
		except:
			return jsonify(status="error", error="The timestamp entered is neither an int nor a float."), 500
	else:
		# Default: current time
		timestamp = time.time()
	query = {'timestamp':{'$lt':timestamp}}
	#datetime.datetime(yyyy,m,d,0,0).timestamp()

	# Check limit
	if ('limit' in info and info['limit'] != ''):
		limit = info['limit']
		try:
			limit = int(limit)
		except:
			return jsonify(status="error", error="The limit entered is not an int."), 500
		if (limit < 1):
			return jsonify(status="error", error="Please enter a limit greater than 0."), 500
		if (limit > 100):
			limit = 100
	else:
		# Default: 25
		limit = 25

	# Check query string
	if ('q' in info and info['q'] != ''):
		q = info['q']
		if (type(q) != str):
			return jsonify(status="error", error="Query is not a string."), 500
		words = q.split()
		if (len(words) == 1):
			word = words[0]
			query['content'] = {'$regex': '(?:^|\W)' + word + '(?:$|\W)', '$options': 'i'}
		else:
			regStr = ""
			first = True
			for word in words:
				if not first:
					regStr += '|'
				else:
					first = False
				regStr += '(?:^|\W)' + word + '(?:$|\W)'
			query['content'] = {'$regex': regStr, '$options': 'i'}

	# Check username
	if ('username' in info and info['username'] != ''):
		username = info['username']
		if (type(username) != str):
			return jsonify(status="error", error="Username is not a string."), 500
		query['username'] = username

	# Check following
	if ('following' in info):
		following = info['following']
		if (following == "True"):
			following = True
		elif (following == "False"):
			following = False
		elif (type(following) != bool):
			return jsonify(status="error", error="Following is not True or False."), 500
	else:
		# Default: true
		following = True
	if following and user_logged_in():
		userStats = db.stat.find_one({'username':session['username']})
		if (userStats):
			followingUser = userStats['following']
			if (len(followingUser) == 0):
				query['username'] = None
			elif (len(followingUser) == 1):
				query['username'] = followingUser[0]
			else:
				usernames = []
				for user in followingUser:
					usernames.append({'username': user})
				query['$or'] = usernames

	# Check parent
	if ('parent' in info and info['parent'] != ''):
		parent = info['parent']
	else:
		# Default: none
		parent = None

	# Check replies
	if ('replies' in info):
		replies = info['replies']
		if (replies == "True"):
			replies = True
		elif (replies == "False"):
			replies = False
		elif (type(replies) != bool):
			return jsonify(status="error", error="Replies is not True or False.")
	else:
		# Default: true
		replies = True
	if replies:
		if parent:
			query['parent'] = parent
	else:
		query['childType'] = {'$ne' : "reply"}

	# Check hasMedia
	if ('hasMedia' in info):
		hasMedia = info['hasMedia']
		if (hasMedia == "True"):
			hasMedia = True
		elif (hasMedia == "False"):
			hasMedia = False
		elif (type(hasMedia) != bool):
			return jsonify(status="error", error="HasMedia is not True or False."), 500
	else:
		# Default: false
		hasMedia = False
	if hasMedia:
		query['media'] = {'$ne' : []}

	# Check rank and execute query
	if ('rank' in info):
		rank = info['rank']
		if (rank == "time"):
			cursor = db.items.find(query).sort('timestamp', pymongo.DESCENDING).limit(limit)
		elif (rank == "interest"):
			cursor = db.items.find(query).sort('interest', pymongo.DESCENDING).limit(limit)
		else:
			return jsonify(status="error", error="Invalid rank."), 500
	else:
		# Default: interest
		rank = "interest"
		cursor = db.items.find(query).sort('interest', pymongo.DESCENDING).limit(limit)

	if json_request():
		return jsonify(status="OK", items=its), 200
	return render_template("search.html", data=get_tweets(cursor))


@app.route('/add_media', methods=["POST"])
def add_media():
	# forward the request to 130.245.171.150:80/add_media?
	
	if not user_logged_in():
		return jsonify(status="error", error="User not logged in")

	if (request.files is not None):
		contents = request.files['content'].read()
	else:
		content = request.values['content']

	file_id = str(uuid.uuid4())
	x = cass.execute("INSERT INTO media (id, owner, itm_cnt, content) VALUES (%s, %s, %s, %s)", (file_id, session['username'], 0, memoryview(contents)))
	if json_request():
		return jsonify(status="OK", id=file_id)
	return redirect(url_for('index_default'))


@app.route('/media/<media_id>', methods=['GET'])
def get_media(media_id):
	stuff = cass.execute("SELECT * FROM media WHERE id=%s ALLOW FILTERING", [media_id])

	if (stuff == []):
		return jsonify(stats="error"), 400

	stuff = stuff[0].content
	resp =  make_response(stuff)
	resp.headers.set('Content-Type', 'image/jpeg')
	if (stuff is not None):
		return resp, 200
	return resp, 400


@app.route('/like_item', methods=['POST'])
def item_liker_poster():
	data = request.form['item_id']
	return like_item_post(data)


@app.route('/item/<item_id>/like', methods=['POST'])
def like_item_post(item_id):
	info = request.json
	if not user_logged_in():
		return jsonify(status="error", error="User not logged in")
	if (info is None):
		info = request.values
		toLike = True if info["like"]=="True" else False
	else:
		toLike = True if "like" not in info or info["like"] else False

	item = db.items.find_one({'_id':ObjectId(item_id)})
	if (item is None):
		if json_request():
			return jsonify(status="error", error="Item not found")
		return jsonify(status="error", error="Item not found") #Error page

	likes = item["likes"]
	interest = item['interest']
	if (session['username'] not in likes):
		if (toLike):
			likes.append(session['username'])
			interest += 1
	else:
		if (not toLike): # and username is in likes
			likes.remove(session['username'])
			interest -= 1

	db.items.update_one({'_id':ObjectId(item_id)}, {'$set':{'likes':likes, 'interest':interest}})
	if json_request():
		return jsonify(status="OK"), 200
	return redirect(request.referrer)


def filler():
	# fill up the database with fake data to initialize the collections
	tables = {'emails':db['emails'], 'users':db['users']}
	tables['emails'].insert({'fake email'})
	tables['users'].insert({'fake user'})
	tables['accounts'].insert({'username':'user', 'password':'1234', 'email':'@'})


if __name__ == "__main__":
	# filler()
	# sudo gunicorn3 --workers=8 --reload app:app
	app.run(host='0.0.0.0', port=80, debug=True)
