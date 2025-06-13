from openai import OpenAI
import os
from typing import List, Dict, Any, Optional
import logging
from .vector_store import vector_store
import json
import re

logger = logging.getLogger(__name__)

class QASystem:
    def __init__(self):
        """Initialize QA System with OpenAI client"""
        self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        self.model = "gpt-3.5-turbo"
    
    def generate_answer(self, question: str, image_base64: Optional[str] = None) -> Dict[str, Any]:
        """Generate answer for a student question"""
        try:
            # Import vector_store dynamically to avoid circular imports
            from vector_store import vector_store
            
            # Step 1: Search for relevant context
            relevant_docs = vector_store.search(question, n_results=5)
            
            # Step 2: Prepare context for LLM
            context = self._prepare_context(relevant_docs)
            
            # Step 3: Create system prompt
            system_prompt = self._create_system_prompt()
            
            # Step 4: Create user prompt with context
            user_prompt = self._create_user_prompt(question, context)
            
            # Step 5: Generate response using OpenAI
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Handle image if provided
            if image_base64:
                # For GPT-4 Vision (if available), otherwise describe that image was provided
                user_prompt += f"\n\nNote: An image was provided with this question (base64 encoded). Please consider this in your response if relevant."
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )
            
            answer_text = response.choices[0].message.content.strip()
            
            # Step 6: Extract links from relevant documents
            links = self._extract_links(relevant_docs)
            
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
    
    def _prepare_context(self, relevant_docs: List[Dict[str, Any]]) -> str:
        """Prepare context from relevant documents"""
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
        
        return "\n".join(context_parts)
    
    def _create_system_prompt(self) -> str:
        """Create system prompt for the LLM"""
        return """You are a helpful Teaching Assistant for the Tools in Data Science (TDS) course at IIT Madras. 
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
    
    def _create_user_prompt(self, question: str, context: str) -> str:
        """Create user prompt with question and context"""
        return f"""Based on the following course materials and forum discussions, please answer this student question:

QUESTION: {question}

RELEVANT COURSE MATERIALS AND DISCUSSIONS:
{context}

Please provide a helpful and accurate answer based on the above information."""
    
    def _extract_links(self, relevant_docs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract relevant links from documents"""
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
        
        return links

# Global instance
qa_system = QASystem()
