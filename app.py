from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from pymongo import MongoClient

import requests
import datetime
import utils


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
    e = db.emails.find_one({'email':email}) # first {} is for _id
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


@app.route('/additem', methods=['POST'])
# Post a new item
# Only allowed if logged in
# Return status and id/error
# return 

@app.route('/item/<id>', methods=['GET'])
def get_item(id):
    # Get contents of a single <id> item
    return

@app.route('/item/<id>', methods=['DELETE'])
def delete_item(id):
    # Delete item <id>

@app.route('/search', methods=['POST'])


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
    info = request.json
    username = info['username']
    password = info['password']
    acc = db.accounts.find_one({}, {username:username, password:password})
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
    if (key!='abracadabra' and v['key']!=key):
        print(v['key'])
        return jsonify(status="error"), 500        

@app.route('/checksession', methods=['POST', 'GET'])
def checkingSession():
    print(session)
    return jsonify(session="OK"), 200
        
    
def filler()
    # fill up the database with fake data to initialize the collections
    tables = {'emails':db['emails'], 'users':db['users']}
    tables['emails'].insert({'fake email'})
    tables['users'].insert({'fake user'})
    tables['accounts'].insert(
        {'username':'user', 'password':'1234', 'email':'@'})
    
    
if __name__ == "__main__":
    #filler()
    app.run(host='0.0.0.0', port=80, debug=True)
    
