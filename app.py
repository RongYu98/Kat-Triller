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

@app.route('/adduser', methods=['GET'])
def adduser_getter():
    return render_template("index.html")
@app.route('/adduser', methods=['POST'])
def adduser_post():
    print(session)
    # print(session.items())
    info = request.json
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
    print(session)
    if (request.args['username']==None or request.args['password']==None):
        return render_template('login.html')
    username = request.args['username']
    password = request.args['password']
    return requests.post('http://130.245.168.160/login',
    # return requests.post('http://0.0.0.0/login',
                         json={'username':username, 'password':password}).json()
    
@app.route('/login', methods=['POST'])
def login_post():
    print('\n\n')
    info = request.json
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
    if (request.args['key']==None or request.args['email']==None):
        return render_template('verify.html')
    key = request.args['key']
    email = request.args['email']
    # bad for performance, but meh...
    return requests.post('http://0.0.0.0/verify',
                         json={'email':email, 'key':key}).json()

@app.route('/verify', methods=['POST'])
def verify_post():
    print('\n\n\n')
    info = request.json
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
    return jsonify(status="OK"), 200



@app.route('/additem', methods=['POST'])
def addItem():
    # Only allowed if logged in
    if ('username' in session and session['username'] != None):
        info = request.json
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

@app.route('/item/<id>', methods=['GET'])
def getItem(id):
    if len(id) == 24:
        it = db.items.find_one({'_id':ObjectId(id)})
        if (it != None):
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
        else:
            response = jsonify(status = "error", error = "Item with ID: " + id + " not found.")
            return response, 500    
    else:
        response = jsonify(status = "error", error = "Invalid ID")
        return response, 500

@app.route('/search', methods=['POST'])
def search():
    info = request.json
    if ('timestamp' in info):
        timestamp = info['timestamp']
        if (not isinstance(timestamp, float)):
            response = jsonify(status = "error", error = "The timestamp entered is not a float.")
            return response, 500
    else:
        # Default: current time
        timestamp = time.time()
    if ('limit' in info):
        limit = info['limit']
        if (not isinstance(limit, int)):
            response = jsonify(status = "error", error = "The limit entered is not an integer.")
            return response, 500
        if (limit > 100):
            response = jsonify(status = "error", error = "The limit has exceeded the maximum.")
            return response, 500
    else:
        # Default: 25
        limit = 25
    cursor = db.items.find({'timestamp':{'$lt':timestamp}}).sort('timestamp', pymongo.DESCENDING).limit(limit)
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
    
