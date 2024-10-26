from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import os
import random

class SocraticRAGAssistant:
    def __init__(self, api_key, docs_directory="./docs"):
        self.client = ChatNVIDIA(
            model="meta/llama-3.1-405b-instruct",
            api_key=api_key,
            temperature=0.7,  # Slightly lower temperature for more focused responses
            top_p=0.9,
            max_tokens=1024,
        )
        
        self.docs_directory = docs_directory
        self.vector_store = None
        
        # Modified system prompt to encourage Socratic dialogue
        self.history = [
            {"role": "system", "content": """You are a Socratic tutor who guides users to discover answers through questioning and critical thinking. 
            Your goal is to help users reach understanding through self-reflection and logical reasoning. If the user is referring to a specific subject matter, please ask questions regarding the subject only
            
            Follow these principles:
            1. Ask probing questions instead of giving direct answers
            2. Help users examine their assumptions
            3. Guide them to break down complex problems into simpler parts
            4. Encourage users to find connections between ideas
            5. Use analogies to relate abstract concepts to familiar ones
            
            When you have access to relevant information from the knowledge base, use it to formulate better questions rather than simply stating facts."""}
        ]
        
        # Socratic question templates
        self.question_templates = [
            "What do you think are the key aspects of {topic}?",
            "How would you compare {topic} to something you're familiar with?",
            "What assumptions are we making about {topic}?",
            "Can you break down {topic} into its fundamental components?",
            "What evidence would support or challenge your view on {topic}?",
            "How might someone with a different perspective view {topic}?",
            "What are the implications if your understanding of {topic} is correct?",
            "How does {topic} relate to what you already know?",
        ]
        
        # Initialize embedding model
        print("Loading embedding model...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        if os.path.exists(docs_directory):
            self.create_vector_store()
        else:
            print(f"Warning: Documents directory '{docs_directory}' does not exist.")
            os.makedirs(docs_directory, exist_ok=True)
            print(f"Created empty documents directory at '{docs_directory}'")

    def load_document(self, file_path):
        """Load a single document based on its file type"""
        try:
            if file_path.lower().endswith('.pdf'):
                loader = PyPDFLoader(file_path)
                return loader.load()
            else:
                print(f"Unsupported file type for {file_path}")
                return []
        except Exception as e:
            print(f"Error loading {file_path}: {str(e)}")
            return []

    def create_vector_store(self):
        """Create a vector store from documents in the specified directory"""
        try:
            print("Loading documents...")
            documents = []
            pdf_files = [f for f in os.listdir(self.docs_directory) if f.lower().endswith('.pdf')]
            
            if not pdf_files:
                print(f"No PDF files found in {self.docs_directory}")
                return
            
            for pdf_file in pdf_files:
                file_path = os.path.join(self.docs_directory, pdf_file)
                print(f"Loading {pdf_file}...")
                docs = self.load_document(file_path)
                documents.extend(docs)
                
            if not documents:
                print("No documents were loaded successfully.")
                return
                
            print(f"Loaded {len(documents)} documents")
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            splits = text_splitter.split_documents(documents)
            
            if not splits:
                print("No text splits were created.")
                return
                
            print(f"Created {len(splits)} text splits")
            
            print("Creating FAISS index...")
            self.vector_store = FAISS.from_documents(splits, self.embeddings)
            print(f"Created vector store from {len(splits)} document chunks")
            
            if not os.path.exists("faiss_index"):
                os.makedirs("faiss_index", exist_ok=True)
            self.vector_store.save_local("faiss_index")
            print("Saved vector store to disk")
            
        except Exception as e:
            print(f"Error creating vector store: {str(e)}")
            print("Continuing without document search capability...")

    def get_relevant_context(self, query, k=3):
        """Retrieve relevant document chunks for the query"""
        try:
            if not self.vector_store:
                return ""
            docs = self.vector_store.similarity_search(query, k=k)
            context = "\n\n".join([doc.page_content for doc in docs])
            return context
        except Exception as e:
            print(f"Error retrieving context: {str(e)}")
            return ""

    def generate_socratic_prompt(self, query, context):
        """Generate a Socratic-style prompt that encourages questioning and discovery"""
        # Extract key terms from the query for focused questioning
        key_terms = [term.strip() for term in query.lower().split() if len(term) > 3]
        
        if context:
            return f"""Based on the following context and the conversation history, guide the user through understanding their question using Socratic questioning.

Context:
{context}

User Question: {query}

Remember to:
1. Ask thought-provoking questions that lead to deeper understanding
2. Use the context to inform your questions, but don't directly state the information
3. Help the user discover connections and insights on their own
4. Guide them to examine their assumptions and reasoning

Choose or adapt relevant questions from:
{random.choice(self.question_templates).format(topic=random.choice(key_terms) if key_terms else "this topic")}"""
        
        return f"""Guide the user through understanding their question using Socratic questioning:

User Question: {query}

Remember to ask thought-provoking questions that lead to deeper understanding."""

    def chat(self, user_input):
        """Start an interactive Socratic chat session"""
        print("Chat with the Socratic assistant! Type 'exit' to end the conversation.\n")
        print("Note: Place your PDF documents in the 'docs' directory to enable document search.\n")
        
        try:
            if user_input.lower() == "exit":
                print("Ending chat session.")
            
            context = self.get_relevant_context(user_input)
            enhanced_prompt = self.generate_socratic_prompt(user_input, context)
            self.history.append({"role": "user", "content": enhanced_prompt})
            
            print("Assistant: ", end="")
            response_chunks = self.client.stream(self.history)
            
            response_text = ""
            for chunk in response_chunks:
                print(chunk.content, end="")
                response_text += chunk.content
            
            print()
            self.history.append({"role": "assistant", "content": response_text})
            return response_text.replace("\n", "<br>")
            
        except Exception as e:
            print(f"\nError during chat: {str(e)}")
            print("Please try again or type 'exit' to end the session.")
            return "ERROR"

if __name__ == "__main__":
    try:
        api_key = "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"
        assistant = SocraticRAGAssistant(api_key)
        assistant.chat()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        print("Please ensure all requirements are installed and the configuration is correct.")