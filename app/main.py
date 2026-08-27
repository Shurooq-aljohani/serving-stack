from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os

app = FastAPI()
API_KEY = os.getenv("API_KEY", "")

@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if request.url.path.startswith("/health") or request.url.path == "/v1/embeddings":
        return await call_next(request)
    
    if API_KEY and request.url.path.startswith("/v1/"):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        expected_token = f"Bearer {API_KEY}"
        if auth_header != expected_token:
            return JSONResponse(status_code=401, content={"detail": "Invalid API Key"})
            
    response = await call_next(request)
    return response

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/v1/chat/completions")
def chat_completions():
    return {"choices": [{"message": {"content": "Hello!"}}]}

DEVICE = os.getenv("DEVICE", "cpu")

@app.post("/v1/embeddings")
def embeddings(payload: dict):
    if DEVICE != "cuda":
        raise HTTPException(400, "Embeddings require a GPU-backed instance; this instance is running in CPU-fallback mode.")
    return {"vector": [0.1] * 8, "device_used": DEVICE}
