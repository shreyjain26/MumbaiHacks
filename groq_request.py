import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def groq_req(user_prompt: str):
    client = Groq()
    if user_prompt:
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": user_prompt}  # This was missing 'role' and 'content'
        ]

        
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages
    )
    
    assistant_response = response.choices[0].message.content
    return assistant_response
