from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from groq_request import groq_req
from chat_pdf import RAGChatAssistant
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './docs'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.secret_key = 'your_secure_random_secret_key'

CORS(app, resources={r"./*": {"origins": "*"}})

def allowed_file(filename):
    """Check if the file is an allowed type."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route("/")
def home():
    """Render the chat interface."""
    return render_template("index.html")

@app.route("/document_ai")
def document_ai():
    """Render the chat interface."""
    return render_template("chatbot2.html")

@app.route("/groq_api/<prompt>")
def groq_api(prompt):
    if not prompt:
        return "No Prompt Given"
    
    resp = groq_req(prompt)
    return resp

@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle file uploads and save them to the 'docs' folder."""
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    
    # If no file is selected or the file is invalid
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # Save the file to the docs folder
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        flash('File uploaded successfully')
        return redirect(url_for('home'))
    else:
        flash('Invalid file format. Only PDFs are allowed.')
        return redirect(url_for('home'))
    
@app.route("/chat", methods=["POST"])
def chat():
    print("TEST1234567890")
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"error": "No input provided!"}), 400
    api_key = "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"
    assistant = RAGChatAssistant(api_key)
    ans = assistant.chat(user_input)
    return {"response": ans}
    