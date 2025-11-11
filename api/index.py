"""Ultra-minimal FastAPI test for Vercel"""
from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="Minimal Test")

@app.get("/")
async def root():
    return {
        "status": "working",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Ultra-minimal FastAPI on Vercel"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

handler = app
