"""
Vercel Serverless Function Entry Point
This wraps the FastAPI app for Vercel deployment
"""
import sys
import os

# Add parent directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import the FastAPI app
    from api_server import app
    handler = app
except Exception as e:
    # Fallback minimal app if imports fail
    from fastapi import FastAPI

    handler = FastAPI()

    @handler.get("/")
    def root():
        return {
            "status": "error",
            "message": f"Failed to load full application: {str(e)}",
            "hint": "Check environment variables and dependencies"
        }

    @handler.get("/health")
    def health():
        return {
            "status": "degraded",
            "error": str(e)
        }
