from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import base64
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, urlparse
import json
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from openai import OpenAI

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="TDS Virtual Teaching Assistant", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# Initialize ChromaDB
persist_directory = "/app/backend/chroma_db"
os.makedirs(persist_directory, exist_ok=True)
chroma_client = chromadb.PersistentClient(path=persist_directory)
collection = chroma_client.get_or_create_collection(
    name="tds_knowledge_base",
    metadata={"description": "TDS course content and discourse posts"}
)

# Initialize embedding model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class QuestionRequest(BaseModel):
    question: str
    image: Optional[str] = None  # base64 encoded image

class Link(BaseModel):
    url: str
    text: str

class QuestionResponse(BaseModel):
    answer: str
    links: List[Link]

class DataScrapeResponse(BaseModel):
    status: str
    message: str
    total_documents: int

# Global flag to track if data has been loaded
data_loaded = False

def get_sample_data():
    """Get sample data for testing"""
    return [
        {
            'id': 'sample_course_1',
            'type': 'course_content',
            'title': 'Introduction to Tools in Data Science',
            'content': 'Tools in Data Science covers various computational tools and libraries used in data analysis, machine learning, and statistical computing. Key topics include Python libraries like pandas, numpy, scikit-learn, and matplotlib. The course covers data preprocessing, visualization, machine learning algorithms, model evaluation, and deployment strategies.',
            'url': 'https://tds.s-anand.net/#/2025-01/',
            'section_type': 'h2',
            'scraped_at': datetime.utcnow().isoformat()
        },
        {
            'id': 'sample_discourse_1',
            'type': 'discourse_post',
            'title': 'Question about GPT models in assignments',
            'content': 'Should I use gpt-4o-mini which AI proxy supports, or gpt3.5 turbo? For the assignment, I need to know which model to use for token counting and pricing calculations. The assignment mentions specific model requirements.',
            'raw_content': 'Should I use gpt-4o-mini which AI proxy supports, or gpt3.5 turbo?',
            'url': 'https://discourse.onlinedegree.iitm.ac.in/t/ga5-question-8-clarification/155939/4',
            'author': 'student123',
            'created_at': '2025-03-15T10:30:00Z',
            'topic_id': 155939,
            'post_number': 4,
            'scraped_at': datetime.utcnow().isoformat()
        },
        {
            'id': 'sample_discourse_2',
            'type': 'discourse_post',
            'title': 'GA5 Question 8 Clarification',
            'content': 'You must use gpt-3.5-turbo-0125, even if the AI Proxy only supports gpt-4o-mini. Use the OpenAI API directly for this question. My understanding is that you just have to use a tokenizer, similar to what Prof. Anand used, to get the number of tokens and multiply that by the given rate.',
            'raw_content': 'You must use gpt-3.5-turbo-0125, even if the AI Proxy only supports gpt-4o-mini.',
            'url': 'https://discourse.onlinedegree.iitm.ac.in/t/ga5-question-8-clarification/155939/3',
            'author': 'ta_helper',
            'created_at': '2025-03-15T11:00:00Z',
            'topic_id': 155939,
            'post_number': 3,
            'scraped_at': datetime.utcnow().isoformat()
        },
        {
            'id': 'sample_course_2',
            'type': 'course_content',
            'title': 'Python Programming Fundamentals',
            'content': 'Python is the primary programming language used in this course. Students should be familiar with basic Python syntax, data structures (lists, dictionaries, tuples), control flow (loops, conditionals), functions, and object-oriented programming concepts. Libraries covered include NumPy for numerical computing, Pandas for data manipulation, Matplotlib and Seaborn for visualization.',
            'url': 'https://tds.s-anand.net/#/2025-01/',
            'section_type': 'h3',
            'scraped_at': datetime.utcnow().isoformat()
        },
        {
            'id': 'sample_course_3',
            'type': 'course_content',
            'title': 'Machine Learning with Scikit-Learn',
            'content': 'The course covers supervised learning algorithms including linear regression, logistic regression, decision trees, random forests, and support vector machines. Unsupervised learning topics include clustering (K-means, hierarchical) and dimensionality reduction (PCA). Model evaluation techniques such as cross-validation, precision, recall, F1-score, and ROC curves are discussed.',
            'url': 'https://tds.s-anand.net/#/2025-01/',
            'section_type': 'h3',
            'scraped_at': datetime.utcnow().isoformat()
        }
    ]

def add_documents_to_vectorstore(documents):
    """Add documents to the vector store"""
    try:
        if not documents:
            logger.warning("No documents to add")
            return
        
        # Prepare data for ChromaDB
        ids = []
        embeddings = []
        metadatas = []
        documents_text = []
        
        for doc in documents:
            doc_id = doc.get('id', str(uuid.uuid4()))
            content = doc.get('content', '')
            
            # Skip if no content
            if not content.strip():
                continue
            
            # Generate embedding
            embedding = embedding_model.encode(content).tolist()
            
            # Prepare metadata (ChromaDB requires all values to be strings, ints, or floats)
            metadata = {
                'type': str(doc.get('type', 'unknown')),
                'title': str(doc.get('title', ''))[:500],  # Limit length
                'url': str(doc.get('url', '')),
                'scraped_at': str(doc.get('scraped_at', '')),
            }
            
            # Add specific fields based on document type
            if doc.get('type') == 'discourse_post':
                metadata.update({
                    'author': str(doc.get('author', '')),
                    'topic_id': str(doc.get('topic_id', '')),
                    'post_number': str(doc.get('post_number', ''))
                })
            elif doc.get('type') == 'course_content':
                metadata.update({
                    'section_type': str(doc.get('section_type', ''))
                })
            
            ids.append(doc_id)
            embeddings.append(embedding)
            metadatas.append(metadata)
            documents_text.append(content)
        
        if ids:
            # Add to ChromaDB
            collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_text
            )
            
            logger.info(f"Added {len(ids)} documents to vector store")
        else:
            logger.warning("No valid documents to add")
            
    except Exception as e:
        logger.error(f"Error adding documents to vector store: {e}")
        raise

def search_vectorstore(query: str, n_results: int = 5):
    """Search for similar documents"""
    try:
        # Generate query embedding
        query_embedding = embedding_model.encode(query).tolist()
        
        # Search in ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Format results
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                result = {
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results['distances'] else None
                }
                formatted_results.append(result)
        
        logger.info(f"Found {len(formatted_results)} results for query: {query[:100]}...")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error searching vector store: {e}")
        return []

def generate_answer(question: str, image_base64: Optional[str] = None):
    """Generate answer for a student question"""
    try:
        # Step 1: Search for relevant context
        relevant_docs = search_vectorstore(question, n_results=5)
        
        # Step 2: Prepare context for LLM
        context_parts = []
        for doc in relevant_docs:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            # Format context with metadata
            context_part = f"Source: {metadata.get('type', 'unknown')}\n"
            if metadata.get('title'):
                context_part += f"Title: {metadata.get('title')}\n"
            if metadata.get('url'):
                context_part += f"URL: {metadata.get('url')}\n"
            context_part += f"Content: {content}\n"
            context_part += "-" * 50 + "\n"
            
            context_parts.append(context_part)
        
        context = "\n".join(context_parts)
        
        # Step 3: Create system prompt
        system_prompt = """You are a helpful Teaching Assistant for the Tools in Data Science (TDS) course at IIT Madras. 
Your role is to answer student questions based on the course content and discussion forum posts provided.

Instructions:
1. Answer questions clearly and directly based on the provided context
2. If the context doesn't contain enough information, say so honestly
3. For technical questions, provide specific guidance when possible
4. Reference the course materials or forum discussions when relevant
5. Be helpful and encouraging, as you would be as a real TA
6. If asked about specific models or tools, refer to the exact requirements mentioned in the course
7. Keep your answers concise but comprehensive

Remember: You are representing the TDS course, so maintain academic standards and provide accurate information based on the course content."""
        
        # Step 4: Create user prompt with context
        user_prompt = f"""Based on the following course materials and forum discussions, please answer this student question:

QUESTION: {question}

RELEVANT COURSE MATERIALS AND DISCUSSIONS:
{context}

Please provide a helpful and accurate answer based on the above information."""
        
        # Handle image if provided
        if image_base64:
            user_prompt += f"\n\nNote: An image was provided with this question (base64 encoded). Please consider this in your response if relevant."
        
        # Step 5: Generate response using OpenAI
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )
            
            answer_text = response.choices[0].message.content.strip()
        except Exception as openai_error:
            logger.warning(f"OpenAI API error: {openai_error}")
            # Fallback response based on retrieved context
            if relevant_docs:
                # Use the most relevant document as fallback
                best_doc = relevant_docs[0]
                answer_text = f"Based on the course materials, here's what I found: {best_doc['content'][:500]}..."
            else:
                answer_text = "I found some relevant information but couldn't generate a complete response. Please check the course materials linked below."
        
        # Step 6: Extract links from relevant documents
        links = []
        seen_urls = set()
        
        for doc in relevant_docs:
            metadata = doc.get('metadata', {})
            url = metadata.get('url', '')
            
            if url and url not in seen_urls:
                # Create meaningful link text
                title = metadata.get('title', '')
                if not title:
                    title = doc.get('content', '')[:100] + "..." if len(doc.get('content', '')) > 100 else doc.get('content', '')
                
                links.append({
                    "url": url,
                    "text": title
                })
                seen_urls.add(url)
                
                # Limit to maximum 5 links
                if len(links) >= 5:
                    break
        
        # Step 7: Format response
        result = {
            "answer": answer_text,
            "links": links
        }
        
        logger.info(f"Generated answer for question: {question[:100]}...")
        return result
        
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        return {
            "answer": "I apologize, but I encountered an error while processing your question. Please try again later.",
            "links": []
        }

# Background task to initialize data
async def initialize_data():
    """Initialize vector store with scraped data"""
    global data_loaded
    try:
        logger.info("Starting data initialization...")
        
        # Check if data already exists
        count = collection.count()
        if count > 0:
            logger.info(f"Data already exists: {count} documents")
            data_loaded = True
            return
        
        # Use sample data for now
        all_data = get_sample_data()
        
        if all_data:
            # Add to vector store
            add_documents_to_vectorstore(all_data)
            data_loaded = True
            logger.info(f"Successfully initialized with {len(all_data)} documents")
        else:
            logger.warning("No data was loaded")
            
    except Exception as e:
        logger.error(f"Error initializing data: {e}")

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "TDS Virtual Teaching Assistant API", "status": "running"}

@api_router.post("/", response_model=QuestionResponse)
async def answer_question(request: QuestionRequest):
    """Main endpoint to answer student questions"""
    try:
        # Ensure data is loaded
        if not data_loaded:
            await initialize_data()
        
        if not data_loaded:
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")
        
        # Generate answer
        result = generate_answer(request.question, request.image)
        
        # Format response
        links = [Link(url=link["url"], text=link["text"]) for link in result.get("links", [])]
        
        return QuestionResponse(
            answer=result.get("answer", "I couldn't generate an answer at this time."),
            links=links
        )
        
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.post("/scrape-data", response_model=DataScrapeResponse)
async def scrape_data_endpoint(background_tasks: BackgroundTasks):
    """Endpoint to trigger data scraping (useful for testing)"""
    try:
        # Clear existing data
        chroma_client.delete_collection(name="tds_knowledge_base")
        global collection
        collection = chroma_client.get_or_create_collection(
            name="tds_knowledge_base",
            metadata={"description": "TDS course content and discourse posts"}
        )
        
        # Trigger background scraping
        background_tasks.add_task(initialize_data)
        
        return DataScrapeResponse(
            status="started",
            message="Data scraping started in background",
            total_documents=0
        )
        
    except Exception as e:
        logger.error(f"Error starting data scrape: {e}")
        raise HTTPException(status_code=500, detail="Failed to start data scraping")

@api_router.get("/status")
async def get_status():
    """Get system status"""
    try:
        count = collection.count()
        return {
            "status": "running",
            "data_loaded": data_loaded,
            "total_documents": count,
            "openai_configured": bool(os.environ.get('OPENAI_API_KEY'))
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {"status": "error", "message": str(e)}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status-checks", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize data on startup
@app.on_event("startup")
async def startup_event():
    """Initialize data on startup"""
    logger.info("Starting TDS Virtual Teaching Assistant API")
    # Initialize data in background
    try:
        await initialize_data()
    except Exception as e:
        logger.error(f"Error during startup initialization: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
