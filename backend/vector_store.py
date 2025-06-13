import chromadb
from chromadb.config import Settings
import os
import logging
from typing import List, Dict, Any, Optional
import uuid
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, persist_directory: str = "/app/backend/chroma_db"):
        """Initialize ChromaDB vector store"""
        self.persist_directory = persist_directory
        
        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="tds_knowledge_base",
            metadata={"description": "TDS course content and discourse posts"}
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        logger.info(f"Initialized VectorStore with {self.collection.count()} documents")
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
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
                embedding = self.embedding_model.encode(content).tolist()
                
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
                self.collection.add(
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
    
    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Search in ChromaDB
            results = self.collection.query(
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
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        try:
            count = self.collection.count()
            return {
                'total_documents': count,
                'collection_name': self.collection.name,
                'persist_directory': self.persist_directory
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}
    
    def clear_collection(self) -> None:
        """Clear all documents from the collection"""
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(name="tds_knowledge_base")
            self.collection = self.client.get_or_create_collection(
                name="tds_knowledge_base",
                metadata={"description": "TDS course content and discourse posts"}
            )
            logger.info("Cleared vector store collection")
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            raise

# Global instance
vector_store = VectorStore()
