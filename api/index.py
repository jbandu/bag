"""
Vercel Serverless Function Entry Point
This wraps the FastAPI app for Vercel deployment
"""
import sys
import os

# Add parent directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app
from api_server import app

# Vercel handler
handler = app
