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

# Import our custom modules
from .scraper import scrape_all_data
from .vector_store import vector_store
from .qa_system import qa_system

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

# Background task to initialize data
async def initialize_data():
    """Initialize vector store with scraped data"""
    global data_loaded
    try:
        logger.info("Starting data initialization...")
        
        # Check if data already exists
        collection_info = vector_store.get_collection_info()
        if collection_info.get('total_documents', 0) > 0:
            logger.info(f"Data already exists: {collection_info['total_documents']} documents")
            data_loaded = True
            return
        
        # Scrape data
        all_data = await scrape_all_data()
        
        if all_data:
            # Add to vector store
            vector_store.add_documents(all_data)
            data_loaded = True
            logger.info(f"Successfully initialized with {len(all_data)} documents")
        else:
            logger.warning("No data was scraped")
            
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
        result = qa_system.generate_answer(request.question, request.image)
        
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
        vector_store.clear_collection()
        
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
        collection_info = vector_store.get_collection_info()
        return {
            "status": "running",
            "data_loaded": data_loaded,
            "total_documents": collection_info.get('total_documents', 0),
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
