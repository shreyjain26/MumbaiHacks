from flask import Flask
from flask_cors import CORS
app = Flask(__name__)

CORS(app, resources={r"./*": {"origins": "*"}})

@app.route("/")
def hello():
    return "Mumbai Hacks"