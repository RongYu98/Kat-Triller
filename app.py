from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient

# One database
client = MongoClient("mongodb://localhost:27017/")
db = client["kt_db"]
# tablename = client['table_name'] 
# https://www.w3schools.com/python/python_mongodb_create_collection.asp

app = Flask(__name__)

@app.route('/', methods=['GET'])
def adduser_getter():
    return render_template("index.html")

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



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)
    
