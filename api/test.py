"""Ultra-minimal FastAPI test for Vercel"""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "working", "message": "FastAPI on Vercel is operational!"}

@app.get("/health")
def health():
    return {"status": "healthy"}

handler = app
