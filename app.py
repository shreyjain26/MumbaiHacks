from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from groq_request import groq_req
from chat_pdf import RAGChatAssistant
from stochastic import SocraticRAGAssistant
from quiz import QuizAssistant
import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import markdown
import json
from typing import List, Dict, Optional

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

@app.route("/socratic")
def stochastic():
    """Render the chat interface."""
    return render_template("stochastic_chatbot.html")

@app.route("/quiz_prac")
def quiz_prac():
    """Render the chat interface."""
    return render_template("quiz.html")

@app.route('/course_gen')
def index():
    return render_template('course_gen.html')


@app.route('/generate_course', methods=['POST'])
def generate_course():
    data = request.json
    topic = data['topic']
    params = {
        "level": data['level'],
        "audience": data['audience'],
        "duration": data['duration'],
        "depth": data['depth']
    }
    api_key = "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"
    course_bot = CourseGeneratorBot(api_key)
    course_gen = course_bot.interactive_course_creation(topic, params)
    md = markdown.markdown(course_gen)
    return {"mark": md}

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
        return redirect(url_for('document_ai'))
    else:
        flash('Invalid file format. Only PDFs are allowed.')
        return redirect(url_for('home'))
    
@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"error": "No input provided!"}), 400
    api_key = "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"
    assistant = RAGChatAssistant(api_key)
    ans = assistant.chat(user_input)
    return {"response": ans}

@app.route("/stochastic_chat", methods=["POST"])
def stochastic_chat():
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"error": "No input provided!"}), 400
    api_key = "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"
    assistant = SocraticRAGAssistant(api_key)
    ans = assistant.chat(user_input)
    return {"response": ans}



@app.route("/quiz", methods=["POST"])
def gen_quiz():
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"error": "No input provided!"}), 400
    api_key = "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"
    assistant = QuizAssistant(api_key)
    ans = assistant.chat(user_input)
    return {"response": ans}
    
    
class CourseGeneratorBot(RAGChatAssistant):
    def _init_(self, api_key, docs_directory="./docs"):
        super().__init__(api_key, docs_directory)
        self.history = [
            {"role": "system", "content": """You are an expert course creator and educator. You can create comprehensive courses 
            on various topics, adapting the content's complexity, depth, and vocabulary to the specified requirements. 
            Your courses include clear learning objectives, structured lessons, practical examples, exercises, and assessments."""}
        ]
        
    def generate_course_prompt(self, topic: str, params: Dict) -> str:
        """Generate a detailed prompt for course creation"""
        return f"""Please create a comprehensive course on {topic} with the following specifications:

Level: {params.get('level', 'intermediate')}
Target Audience: {params.get('audience', 'general')}
Estimated Duration: {params.get('duration', '4 hours')}
Depth: {params.get('depth', 'moderate')}

The course should include:
1. Course Overview and Learning Objectives
2. Prerequisites (if any)
3. Detailed Lesson Plans with:
   - Theoretical concepts
   - Practical examples
   - Code snippets (if applicable)
   - Exercises
   - Knowledge checks
4. Final Assessment
5. Additional Resources

Please format the content with:
- Code snippets in backticks
- Important terms in bold
- Key points in italics
- Clear section headers using markdown
- Numbered lists for steps
- Bullet points for lists

Context from available documents will be incorporated where relevant."""

    def create_course(self, topic: str, params: Optional[Dict] = None):
        """Generate a full course on the specified topic"""
        if params is None:
            params = {}
            
        # Get relevant context if available
        context = self.get_relevant_context(topic)
        
        # Generate course prompt
        course_prompt = self.generate_course_prompt(topic, params)
        if context:
            course_prompt += f"\n\nRelevant Context:\n{context}"
            
        # Generate course content
        self.history.append({"role": "user", "content": course_prompt})
        
        print("Generating course content... This may take a while.\n")
        print("Course: ", end="")
        
        response_text = ""
        response_chunks = self.client.stream(self.history)
        
        for chunk in response_chunks:
            print(chunk.content, end="")
            response_text += chunk.content
            
        print("\n\nCourse generation complete!")
        
        return response_text
    
    
    def interactive_course_creation(self, topic, params):
        """Interactive interface for course creation"""
        print("Welcome to the Course Generator!")
        print("You can create custom courses with specific parameters.")
        
        while True:
            course = self.create_course(params)
            with open(f"{topic}.md", "w") as f:
                f.writelines(course)
            return course
        else:
            print("Invalid choice. Please try again.")


if __name__ == '__main__':
    app.run(debug=True)