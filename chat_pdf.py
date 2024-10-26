from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import os

class RAGChatAssistant:
    def __init__(self, api_key, docs_directory="./docs"):
        self.client = ChatNVIDIA(
            model="meta/llama-3.1-405b-instruct",
            api_key=api_key,
            temperature=1,
            top_p=1,
            max_tokens=1024,
        )
        
        self.docs_directory = docs_directory
        self.vector_store = None
        self.history = [
            {"role": "system", "content": "You are an assistant knowledgeable about AI and GPUs. You have access to a knowledge base of documents that you can reference to provide accurate information."},
        ]
        
        # Initialize embedding model
        print("Loading embedding model...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # Create vector store if documents directory exists
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
            
            # Get all PDF files in the directory
            pdf_files = [f for f in os.listdir(self.docs_directory) if f.lower().endswith('.pdf')]
            
            if not pdf_files:
                print(f"No PDF files found in {self.docs_directory}")
                return
            
            # Load each PDF file
            for pdf_file in pdf_files:
                file_path = os.path.join(self.docs_directory, pdf_file)
                print(f"Loading {pdf_file}...")
                docs = self.load_document(file_path)
                documents.extend(docs)
                
            if not documents:
                print("No documents were loaded successfully.")
                return
                
            print(f"Loaded {len(documents)} documents")
            
            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            splits = text_splitter.split_documents(documents)
            
            if not splits:
                print("No text splits were created.")
                return
                
            print(f"Created {len(splits)} text splits")
            
            # Create vector store
            print("Creating FAISS index...")
            self.vector_store = FAISS.from_documents(splits, self.embeddings)
            print(f"Created vector store from {len(splits)} document chunks")
            
            # Save the index
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

    def generate_prompt(self, query, context):
        """Generate a prompt that includes relevant context"""
        if context:
            return f"""Based on the following context and the conversation history, please answer the user's question.

Context:
{context}

User Question: {query}

Please provide a detailed response, citing specific information from the context when relevant."""
        return query

    def chat(self, user_input: str):
        """Start an interactive chat session"""
        print("Chat with the assistant! Type 'exit' to end the conversation.\n")
        print("Note: Place your PDF documents in the 'docs' directory to enable document search.\n")
        
        try:
            # Get user input
            if user_input.lower() == "exit":
                print("Ending chat session.")
            
            # Get relevant context
            context = self.get_relevant_context(user_input)
            
            # Generate enhanced prompt
            enhanced_prompt = self.generate_prompt(user_input, context)
            
            # Add the user's message to history
            self.history.append({"role": "user", "content": enhanced_prompt})
            
            # Get and print the assistant's response
            print("Assistant: ", end="")
            response_chunks = self.client.stream(self.history)
            
            response_text = ""
            for chunk in response_chunks:
                print(chunk.content, end="")
                response_text += chunk.content
            
            print()  # Newline after the assistant's response
            
            # Add assistant's response to history
            self.history.append({"role": "assistant", "content": response_text})
            return response_text.replace("\n", "<br>")
            
        except Exception as e:
            print(f"\nError during chat: {str(e)}")
            print("Please try again or type 'exit' to end the session.")
            return "ERROR"

if __name__ == "__main__":
    try:
        api_key = "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"
        assistant = RAGChatAssistant(api_key)
        assistant.chat("Hello")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        print("Please ensure all requirements are installed and the configuration is correct.")