from flask import Flask
from flask_cors import CORS
from groq_request import groq_req
app = Flask(__name__)

CORS(app, resources={r"./*": {"origins": "*"}})

@app.route("/")
def hello():
    return "Mumbai Hacks"

@app.route("/groq_api/<prompt>")
def groq_api(prompt):
    if not prompt:
        return "No Prompt Given"
    
    resp = groq_req(prompt)
    return resp