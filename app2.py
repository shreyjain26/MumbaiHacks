from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import markdown
import os
import json
from typing import List, Dict, Optional
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from chat_pdf import RAGChatAssistant
import os

app = Flask(__name__)

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
            return course
        else:
            print("Invalid choice. Please try again.")

@app.route('/')
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

if __name__ == '__main__':
    app.run(debug=True)