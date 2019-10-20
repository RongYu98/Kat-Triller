from flask import Flask, render_template, request, jsonify, session
from pymongo import MongoClient

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
    print(session.items())
    info = request.json
    username = info['username'] # unique
    password = info['password']
    email = info['email'] # unique

    # check for uniqueness of username and email in db
    e = db.emails.find_one({}, {'email':email}) # first {} is for _id
    u = db.users.find_one({}, {'username':username})

    #if (e!=None or u!=None): ## one or both are not unique
    #    return jsonify(status="error"), 500

    # do this only after verifying
    # db.accounts.insert(
    #     {username:username, email:email, password:password})
    key = utils.generateKey()
    db.verification.insert(
        {username:username, email:email, password:password, key:key})
    
    # send email verfication
    # sendEmail(email, key)
    
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
    return render_template("login.html")
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
    
    
>>>>>>> 1875ffe23f1d9c81ec6a8b3170e5e97a461315fd

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
    
