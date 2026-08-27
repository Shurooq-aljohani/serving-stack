from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os

app = FastAPI()
API_KEY = os.getenv("API_KEY", "")

@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if request.url.path.startswith("/health"):
        return await call_next(request)
    
    if request.url.path.startswith("/v1/"):
        auth_header = request.headers.get("Authorization")
        
        # إذا لم يتم إرسال المفتاح أبداً -> 401
        if not auth_header:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        
        # التحقق من أن المفتاح المطابق صحيح
        expected_token = f"Bearer {API_KEY}"
        if API_KEY and auth_header != expected_token:
            return JSONResponse(status_code=401, content={"detail": "Invalid API Key"})
            
    response = await call_next(request)
    return response

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/v1/chat/completions")
def chat_completions():
    return {"choices": [{"message": {"content": "Hello!"}}]}
