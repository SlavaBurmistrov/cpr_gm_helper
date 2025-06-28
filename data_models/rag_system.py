from langchain.vectorstores import FAISS
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader
from langchain.llms import Ollama  # Or another LLM provider
from langchain.chains import RetrievalQA
import os


class RAGSystem:
    """Handles knowledge base creation and querying."""

    def __init__(self, knowledge_base_path: str, vector_store_path: str):
        self.knowledge_base_path = knowledge_base_path
        self.vector_store_path = vector_store_path
        self.embedding_model = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
        self.llm = Ollama(model="llama3")  # Example using a local Llama3 model
        self.vector_store = None
        self.qa_chain = None
        self._initialize_vector_store()

    def _initialize_vector_store(self):
        """Loads or creates the vector store from documents."""
        if os.path.exists(self.vector_store_path):
            print("Loading existing vector store...")
            self.vector_store = FAISS.load_local(self.vector_store_path, self.embedding_model,
                                                 allow_dangerous_deserialization=True)
        else:
            print("Creating new vector store...")
            docs = []
            for root, _, files in os.walk(self.knowledge_base_path):
                for file in files:
                    if file.endswith(".pdf"):
                        loader = PyPDFLoader(os.path.join(root, file))
                        docs.extend(loader.load())

            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
            splits = text_splitter.split_documents(docs)
            self.vector_store = FAISS.from_documents(documents=splits, embedding=self.embedding_model)
            self.vector_store.save_local(self.vector_store_path)

        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vector_store.as_retriever()
        )
        print("RAG system is ready.")

    def query(self, question: str) -> str:
        """Asks a question to the knowledge base."""
        if not self.qa_chain:
            return "QA chain is not initialized."

        prompt = f"""
        You are an expert Game Master for the Cyberpunk Red TTRPG.
        Answer the following question based only on the provided context.
        If the context does not contain the answer, say 'The rules do not specify this'.
        Question: {question}
        """
        response = self.qa_chain.run(prompt)
        return response