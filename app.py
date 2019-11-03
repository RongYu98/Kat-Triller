from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId

import pymongo
import requests
import datetime
import utils
import time

# One database
client = MongoClient("mongodb://localhost:27017/")
db = client["kt_db"]
# tablename = client['table_name'] 
# https://www.w3schools.com/python/python_mongodb_create_collection.asp

app = Flask(__name__)
app.permanent_session_lifetime = datetime.timedelta(days=365)
app.secret_key = 'Kats Trilling is AWESOME!'

@app.route('/', methods=['GET'])
def index_default():
    return redirect(url_for('adduser_getter'))

@app.route('/adduser', methods=['GET'])
def adduser_getter():
    if 'username' not in request.args or 'password' not in request.args or 'email' not in request.args:
        return render_template("adduser.html")
    return adduser_post()
    
@app.route('/adduser', methods=['POST'])
def adduser_post():
    print(session)
    # print(session.items())
    info = request.json
    if (info==None):
        info = request.args
    username = info['username'] # unique
    password = info['password']
    email = info['email'] # unique

    # check for uniqueness of username and email in db
    e = db.emails.find_one({'email':email}) 
    u = db.users.find_one({'username':username})

    if (e!=None or u!=None): ## one or both are not unique
        return jsonify(status="error"), 500

    # record the email and username
    db.emails.insert({'email':email})
    db.users.insert({'username':username})

    # add account info to verification tables
    key = utils.generateKey()
    i = db.verification.insert(
        {'username':username, 'email':email, 'password':password, 'key':key})

    # send email verfication
    utils.sendEmail(key, email)
    
    resp = jsonify(status="OK", key=key)
    return resp, 200

@app.route('/login', methods=['GET'])
def login_getter():
    if ('username' not in request.args or 'password' not in request.args):
    # if (request.args['username']==None or request.args['password']==None):
        return render_template('login.html')
    return login_post()
    
    #request.json = {'username':request.args['username'],
    #                'password':request.args['password']}
    #request.json['username'] = request.args['username']
    #request.json['password'] = request.args['password']
    
@app.route('/login', methods=['POST'])
def login_post():
    print('\n\n')
    info = request.json
    if (info==None):
        # info = request.args
        info = request.form
    username = info['username']
    password = info['password']
    print(info)
    acc = db.accounts.find_one( {'username':username, 'password':password})
    print(acc)
    if (acc==None):
        return jsonify(status="error"), 500
    session['username'] = username

    resp = jsonify(status="OK")
    return resp, 200

@app.route('/logout', methods=['GET', 'POST'])
def logout_getter():
    print(session)
    print("AWESOME\n")
    if ('username' in session and session['username']!=None):
        session['username']=None
        resp = jsonify(status="OK")
        return resp, 200
    return jsonify(status="error"), 500
    # return redirect(url_for('/login'))

@app.route('/verify', methods=['GET'])
def verify_get():
    if ('key' not in request.args or 'email' not in request.args):
        return render_template('verify.html')
    return verify_post()
    
@app.route('/verify', methods=['POST'])
def verify_post():
    print('\n\n\n')
    info = request.json
    if (info==None):
        info = request.args
    print(info)
    email = info['email']
    key = info['key']
    print(email, key)
    # verify that it exists and is correct
    v = db.verification.find_one({'email':email})
    print(v)
    if (v==None):
        return jsonify(status="error"), 500
    if (key!='abracadabra' and v['key'][1:-1]!=key):
        print(v['key'])
        print(key)
        return jsonify(status="error"), 500        
    db.accounts.insert(
        {'username':v['username'], 'email':email, 'password':v['password']})
    db.verification.remove(v)
    db.stats.insert(
        {'username':v['username'], 'email':email, 'followers':[], 'following':[]})
        # followers and following is an array, because once someone follows, they get put in array
        # and once you are following, you're put in their array
    return jsonify(status="OK"), 200

@app.route('/user/<username>', methods=['GET'])
def find_user(username):
    userInfo = db.stats.find_one({'username':username})
    if (userInfo==None):
        return (jsonify(status="error"), 500)
    
    userStats = {"email":userInfo['email'], "followers":len(userInfo["followers"]),
                 "following":len(userInfo["following"])}
    resp = jsonify(status="OK", user=userStats)
    return resp, 200
@app.route('/user/<username>/followers', methods=['GET'])
def find_user_followers(username):
    limit = 50
    if ("limit" in request.args):
        limit = request.args["limit"]
    if limit < 0 or limit > 200:
        return (jsonify(status="error"), 500)
    
    userInfo = db.stats.find_one({'username':username})
    if (userInfo==None):
        return (jsonify(status="error"), 500)
    followers = userInfo['followers'][:limit]
    return jsonify(status="OK", users=followers), 200
@app.route('/user/<username>/following', methods=['GET'])
def find_user_following(username):
    limit = 50
    if ("limit" in request.args):
        limit = request.args
    if limit < 0 or limit > 200:
        return (jsonify(status="error"), 500)
    userInfo = db.stats.find_one({'username':username})
    if (userInfo==None):
        return (jsonify(status="error"), 500)
    following = userInfo['following'][:limit]
    return jsonify(status="OK", users=following), 200


@app.route('/follow', methods=['GET'])
def follow_user_getter():
    return render_template('follow_user.html')
@app.route('/follow', methods=['POST'])
def follow_user_poster():
    if ('username' not in session or session['username']==None):
        return jsonify(status="error"), 500
    info = request.json
    if (info==None):
        info = request.form
    username = info["username"]
    if ('follow' not in info):
        follow=True
    else:
        follow = True if info["follow"]=="True" else False
    print(follow)
    print(info["follow"])

    # get the user the client wants to follow
    userInfo = db.stats.find_one({'username':username})
    if (userInfo==None):
        return (jsonify(status="error"), 500)
    # get the followers list, and adjust it depending on selection
    followers = userInfo['followers']
    if (follow):
        followers.append(session['username'])
    else:
        if (username in followers):
            followers.remove(username)

    db.stats.update_one({
        'username':username
    }, {'$set':
        {'followers':followers}
    })
    
    # update the client data                 
    currentUser = db.stats.find_one({'username':session['username']})
    if (currentUser==None):
        return (jsonify(status="error"), 500)
    # get the following list, and adjust it depending on selection
    following = currentUser['following']
    if (follow):
        following.append(username)
    else:
        if (username in following):
            following.remove(username)
    db.stats.update_one({
        'username':session['username']
    }, {'$set':
        {'following':following}
    }) # upsert = false, because we don't want to insert if DNE
                
    return jsonify(status="OK"), 200



@app.route('/additem', methods=['GET'])
def additem_getter():
    return render_template("additem.html")

@app.route('/additem', methods=['POST'])
def addItem():
    # Only allowed if logged in
    if ('username' in session and session['username'] != None):
        info = request.json
        if (info==None):
            info = request.form
        # body of item
        if ('content' in info):
            content = info['content']
        else:
            response = jsonify(status = "error", error = "Empty content.")
            return response, 500
        # "retweet", "reply", or null (optional)
        if ('childType' in info):
            if (info['childType'] == "retweet" or info['childType'] == "reply" or info['childType'] == None):
                childType = info['childType']
            elif (info['childType'] == "null"):
                childType = None
            else:
                response = jsonify(status = "error", error = "Invalid child type.")
                return response, 500
        else:
            childType = None
        # ID of the original item being responded to
        # parent = info['parent']
        # array of media IDs
        # media = info['media']
        # Post a new item
        i = db.items.insert({'content':content, 'childType':childType, 'username':session['username'], 'likes':0, 'retweeted':0, 'timestamp':time.time()})
        # Return status and id
        response = jsonify(status = "OK", id = str(i))
        return response, 200
    else:
        # Return status and error
        response = jsonify(status = "error", error = "User not logged in.")
        return response, 500

@app.route('/item/<id>', methods=['GET', 'DELETE'])
def getItem(id):
    if len(id) == 24:
        query = {'_id':ObjectId(id)}
        it = db.items.find_one(query)
        if (it != None):
            if request.method == 'GET':
                # Get contents of a single <id> item
                response = jsonify(status = "OK", item = {
                    'id':id,
                    'username':it['username'],
                    'property':{'likes':it['likes']},
                    'retweeted':it['retweeted'],
                    'content':it['content'],
                    'timestamp':it['timestamp'],
                    'childType':it['childType']})
                return response, 200
            if request.method == 'DELETE':
                # Only allowed if logged in and username matches
                if ('username' in session and session['username'] != None and it['username'] == session['username']):
                    db.items.delete_one(query)
                    response = jsonify(status = "OK")
                    return response, 200
                else:
                    response = jsonify(status = "error")
                    return response, 500
        else:
            response = jsonify(status = "error", error = "Item with ID: " + id + " not found.")
            return response, 500    
    else:
        response = jsonify(status = "error", error = "Invalid ID")
        return response, 500

@app.route('/search', methods=['GET'])
def search_getter():
    return render_template("search.html")

@app.route('/search', methods=['POST'])
def search():
    info = request.json
    if (info == None):
        info = request.form
    # Check timestamp
    if ('timestamp' in info):
        timestamp = info['timestamp']
        if timestamp == '':
            timestamp = time.time()
        try:
            timestamp = float(timestamp)
        except:
            response = jsonify(status = "error", error = "The timestamp entered is neither an int nor a float.")
            return response, 500
    else:
        # Default: current time
        timestamp = time.time()
    query = {'timestamp':{'$lt':timestamp}}
    # Check limit
    if ('limit' in info and info['limit'] != ''):
        limit = info['limit']
        try:
            limit = int(limit)
        except:
            response = jsonify(status = "error", error = "The limit entered is not an int.")
            return response, 500
        if (limit < 1):
            response = jsonify(status = "error", error = "Please enter a limit greater than 0.")
            return response, 500
        if (limit > 100):
            response = jsonify(status = "error", error = "The limit has exceeded the maximum.")
            return response, 500
    else:
        # Default: 25
        limit = 25
    # Check query string
    if ('q' in info and info['q'] != ''):
        q = info['q']
        if (type(q) != str):
            response = jsonify(status = "error", error = "Query is not a string.")
            return response, 500
        words = q.split()
        if (len(words) == 1):
            word = words[0]
            query['content'] = {'$regex': '(?:^|\W)' + word + '(?:$|\W)'}
        else:
            regStr = ""
            first = True
            for word in words:
                if not first:
                    regStr += '|'
                else:
                    first = False
                regStr += '(?:^|\W)' + word + '(?:$|\W)'
            query['content'] = {'$regex': regStr}
    # Check username
    if ('username' in info and info['username'] != ''):
        username = info['username']
        if (type(username) != str):
            response = jsonify(status = "error", error = "Username is not a string.")
            return response, 500
        query['username'] = username
    # Check following
    if ('following' in info):
        following = info['following']
        if (following == "True"):
            following = True
        elif (following == "False"):
            following = False
        elif (type(following) != bool):
            response = jsonify(status = "error", error = "Following is not True or False.")
            return response, 500
    else:
        # Default: true
        following = True
    if (following and 'username' in session and session['username'] != None):
        userStats = db.stats.find_one({'username':session['username']})
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
    cursor = db.items.find(query).sort('timestamp', pymongo.DESCENDING).limit(limit)
    its = []
    for it in cursor:
        item = {
            'id':str(it['_id']),
            'username':it['username'],
            'property':{'likes':it['likes']},
            'retweeted':it['retweeted'],
            'content':it['content'],
            'timestamp':it['timestamp'],
            'childType':it['childType']
            }
        its.append(item)
    response = jsonify(status = "OK", items = its)
    return response, 200

@app.route('/user/<username>/posts', methods=['GET'])
def userPosts(username):
    if ('limit' in request.args):
        limit = request.args['limit']
        if limit == '':
            limit = 50
        try:
            limit = int(limit)
        except:
            response = jsonify(status = "error")
            return response, 500
        if (limit < 1):
            response = jsonify(status = "error")
            return response, 500
        if (limit > 200):
            response = jsonify(status = "error")
            return response, 500
    else:
        # Default: 50
        limit = 50
    query = {'username':username}
    cursor = db.items.find(query).limit(limit)
    ids = []
    for it in cursor:
        ids.append(str(it['_id']))
    response = jsonify(status = "OK", items = ids)
    return response, 200

@app.route('/checksession', methods=['POST', 'GET'])
def checkingSession():
    print(session)
    return jsonify(session="OK"), 200
    
def filler():
    # fill up the database with fake data to initialize the collections
    tables = {'emails':db['emails'], 'users':db['users']}
    tables['emails'].insert({'fake email'})
    tables['users'].insert({'fake user'})
    tables['accounts'].insert(
        {'username':'user', 'password':'1234', 'email':'@'})
    
    
if __name__ == "__main__":
    #filler()
    app.run(host='0.0.0.0', port=80, debug=True)
    
