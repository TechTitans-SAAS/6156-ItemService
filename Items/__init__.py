from flask import Flask
from flask_pymongo import PyMongo
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
# app.config["SECRET_KEY"] = "somekey"
app.config["MONGO_URI"] = "mongodb+srv://thriftUStore:dbUserPassword@cluster0.xzhgoim.mongodb.net/ThriftUStore?retryWrites=true&w=majority"

# mongodb database
mongodb_client = PyMongo(app)
db = mongodb_client.db

from Items import routes
