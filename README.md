# TDS Virtual Teaching Assistant

A virtual Teaching Assistant for the Tools in Data Science (TDS) course at IIT Madras. This application uses RAG (Retrieval Augmented Generation) to answer student questions based on course content and Discourse forum discussions.

## Project Overview

This project creates an API that can automatically answer student questions based on:
- TDS course content from https://tds.s-anand.net/#/2025-01/
- TDS Discourse posts from https://discourse.onlinedegree.iitm.ac.in/c/courses/tds-kb/34
- Date range: January 1, 2025 - April 14, 2025

## Live Demo

- **API Endpoint**: https://0611d488-7360-4f0e-9013-4cdc03adf146.preview.emergentagent.com/api/
- **Frontend Interface**: https://0611d488-7360-4f0e-9013-4cdc03adf146.preview.emergentagent.com/

## API Usage

### Main Endpoint
```
POST https://0611d488-7360-4f0e-9013-4cdc03adf146.preview.emergentagent.com/api/
```

**Request Format:**
```json
{
  "question": "Should I use gpt-4o-mini which AI proxy supports, or gpt3.5 turbo?",
  "image": "base64_encoded_image_optional"
}
```

**Response Format:**
```json
{
  "answer": "You must use gpt-3.5-turbo-0125, even if the AI Proxy only supports gpt-4o-mini...",
  "links": [
    {
      "url": "https://discourse.onlinedegree.iitm.ac.in/t/ga5-question-8-clarification/155939/4",
      "text": "Use the model that's mentioned in the question."
    }
  ]
}
```

## Testing Instructions

### For Local Testing (Promptfoo)

1. Copy the configuration content below and save it as `project-tds-virtual-ta-promptfoo.yaml`:

```yaml
description: 'TDS Virtual Teaching Assistant Evaluation'

providers:
  - id: tds-api
    type: http
    config:
      url: 'https://0611d488-7360-4f0e-9013-4cdc03adf146.preview.emergentagent.com/api/'
      method: POST
      headers:
        Content-Type: application/json
      body:
        question: '{{prompt}}'

prompts:
  - 'Should I use gpt-4o-mini which AI proxy supports, or gpt3.5 turbo?'
  - 'What Python libraries are covered in the TDS course?'
  - 'How do I handle machine learning models in assignments?'
  - 'What are the key topics in Tools in Data Science?'
  - 'Can you explain the difference between supervised and unsupervised learning?'

tests:
  - vars:
      prompt: 'Should I use gpt-4o-mini which AI proxy supports, or gpt3.5 turbo?'
    assert:
      - type: contains
        value: 'gpt'
      - type: javascript
        value: 'typeof output.answer === "string" && output.answer.length > 10'
      - type: javascript
        value: 'Array.isArray(output.links)'
```

2. Run the evaluation:
```bash
npx -y promptfoo eval --config project-tds-virtual-ta-promptfoo.yaml
```

### For Manual Testing (cURL)

```bash
curl "https://0611d488-7360-4f0e-9013-4cdc03adf146.preview.emergentagent.com/api/" \
  -H "Content-Type: application/json" \
  -d '{"question": "Should I use gpt-4o-mini which AI proxy supports, or gpt3.5 turbo?"}'
```

## Technical Architecture

- **Backend**: FastAPI with Python
- **Frontend**: React with Tailwind CSS
- **Vector Database**: ChromaDB for semantic search
- **Embeddings**: SentenceTransformer (all-MiniLM-L6-v2)
- **LLM**: OpenAI GPT-3.5-turbo with fallback mechanism
- **Database**: MongoDB for metadata storage

## Bonus Features

1. **Discourse Scraping Script**: Located at `scripts/scrape_discourse.py` for scraping forum posts
2. **Semantic Search**: ChromaDB-based vector search for relevant content retrieval
3. **Fallback Mechanism**: Graceful handling of OpenAI API quota limits
4. **Comprehensive Frontend**: React interface for easy testing and interaction

## How to Run Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB
- OpenAI API key

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key-here"
uvicorn server:app --host 0.0.0.0 --port 8001
```

### Frontend Setup
```bash
cd frontend
yarn install
yarn start
```

## GitHub Repository Information

This project should be committed to a public GitHub repository with:
- MIT License file in the root directory
- All source code for backend and frontend
- Documentation and setup instructions
- Discourse scraping script for bonus points
