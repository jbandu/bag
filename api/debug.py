"""
Minimal debug endpoint for Vercel
"""
from fastapi import FastAPI
import sys
import os

app = FastAPI()

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Minimal FastAPI is working!",
        "python_version": sys.version,
        "working_directory": os.getcwd(),
        "sys_path": sys.path[:3]
    }

@app.get("/test-imports")
def test_imports():
    results = {}

    # Test each import
    try:
        import fastapi
        results["fastapi"] = "✓"
    except Exception as e:
        results["fastapi"] = f"✗ {str(e)}"

    try:
        import pydantic
        results["pydantic"] = "✓"
    except Exception as e:
        results["pydantic"] = f"✗ {str(e)}"

    try:
        import langchain
        results["langchain"] = "✓"
    except Exception as e:
        results["langchain"] = f"✗ {str(e)}"

    try:
        import anthropic
        results["anthropic"] = "✓"
    except Exception as e:
        results["anthropic"] = f"✗ {str(e)}"

    try:
        from config.settings import settings
        results["config"] = "✓"
        results["anthropic_key_set"] = "✓" if settings.anthropic_api_key else "✗ Not set"
    except Exception as e:
        results["config"] = f"✗ {str(e)}"

    return {
        "status": "test_complete",
        "imports": results
    }

handler = app
