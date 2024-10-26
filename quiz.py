from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_community.embeddings import HuggingFaceEmbeddings
import json

class QuizAssistant:
    def __init__(self, api_key):
        self.client = ChatNVIDIA(
            model="meta/llama-3.1-405b-instruct",
            api_key=api_key,
            temperature=0.7,
            top_p=0.9,
            max_tokens=1024,
        )
        
        self.history = self.initialize_history()
        
        # Initialize embedding model
        print("Loading embedding model...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )

    def initialize_history(self):
        return [
            {"role": "system", "content": """Task: Generate a string input format for a multiple-choice question (MCQ) quiz about a specified topic.

Instructions:
Generate 10 multiple-choice questions (MCQs) based on the specified topic. 
Each question should begin with a question phrase (e.g., "What", "Which", "In what year", etc.).
Follow each question with four options labeled A, B, C, and D.
Each option should be a plausible answer to the question.
Conclude with the correct answer, labeled as "Answer: [Correct Option]".

Please format the output as follows:
{
    "questions": [
        {
            "question": "What year was Elon Musk born?",
            "options": {
                "A": "1970",
                "B": "1971",
                "C": "1972",
                "D": "1973"
            },
            "answer": "B"
        },
        ...
    ]
}
"""}
        ]

    def generate_socratic_prompt(self, topic):
        return f"Generate 10 multiple-choice questions (MCQs) about the following topic:\n{topic}\n"

    def format_response_to_dict(self, response_text):
        # Split the response into lines
        lines = response_text.strip().split('\n')
        questions_list = []

        current_question = None

        for line in lines:
            line = line.strip()
            if line.startswith("What") or line.startswith("Which") or line.startswith("In what year"):
                if current_question:
                    questions_list.append(current_question)
                current_question = {"question": line, "options": {}, "answer": ""}
            elif line.startswith("A)") or line.startswith("B)") or line.startswith("C)") or line.startswith("D)"):
                if current_question is not None:
                    option_label = line[0]  # Get the option label (A, B, C, D)
                    option_text = line[3:]  # Get the option text (after "A) ")
                    current_question["options"][option_label] = option_text
            elif line.startswith("Answer:"):
                if current_question is not None:
                    current_question["answer"] = line.split(": ")[1]

        if current_question:  # Append the last question if exists
            questions_list.append(current_question)

        return {"questions": questions_list}

    def chat(self, user_input):
        if user_input.lower() == "exit":
            print("Ending chat session.")
            return

        # Generate the prompt for MCQs
        enhanced_prompt = self.generate_socratic_prompt(user_input)
        self.history.append({"role": "user", "content": enhanced_prompt})

        print(f"You: {user_input}")

        # Get the assistant's response
        print("Assistant: ", end="")
        response_chunks = self.client.stream(self.history)
        
        # Combine response chunks into a single string
        response_text = "".join(chunk.content for chunk in response_chunks)

        # Print the raw response text
        print(response_text)
            
        start_index = response_text.find('{')
        end_index = response_text.rfind('}') + 1  # Include the closing brace

        # Extract the JSON part
        json_string = response_text[start_index:end_index]
            
        response_dict = json.loads(json_string)
        
        print(response_dict)
        
        html_output = '<form>\n'

        for index, q in enumerate(response_dict['questions']):
            html_output += f'<fieldset>\n<legend>Question {index + 1}:</legend>\n'
            html_output += f'<p>{q["question"]}</p>\n'
            
            for option, answer in q['options'].items():
                html_output += f'<label><input type="radio" name="question{index}" value="{option}"> {option}. {answer}</label><br>\n'
            
            html_output += '</fieldset>\n'

        html_output += '<input type="submit" value="Submit">\n</form>'

        # Print or save the HTML output

        # Append the assistant's response to history
        self.history.append({"role": "assistant", "content": response_text})
        
        return html_output

if __name__ == "__main__":
    try:
        api_key = "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"
        assistant = QuizAssistant(api_key)
        while True:
            user_input = input("You: ")
            assistant.chat(user_input)
    except Exception as e:
        print(f"Fatal error: {str(e)}")
