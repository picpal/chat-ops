import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.v1 import chat, documents

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="AI Orchestrator",
    description="ChatOps AI Orchestrator - Step 8: RAG Document Management API",
    version="0.8.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development: Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])


@app.get("/")
async def root():
    return {
        "service": "ai-orchestrator",
        "status": "UP",
        "step": "8-rag-document-management",
        "features": [
            "Natural Language to QueryPlan",
            "LangChain + OpenAI Integration",
            "RenderSpec Composition",
            "RAG Document Search (pgvector)",
            "Document Management REST API"
        ]
    }


@app.get("/health")
async def health():
    return {
        "service": "ai-orchestrator",
        "status": "UP",
        "step": "8",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "rag_enabled": os.getenv("RAG_ENABLED", "true").lower() == "true",
        "database_configured": bool(os.getenv("DATABASE_URL"))
    }
