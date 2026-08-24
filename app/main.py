
from __future__ import annotations


"""serving-stack: the FastAPI service (week 2, CPU, tiny model).

This is the starter. GET /health is done for you and works as soon as the model
loads: treat it as the worked example. Your job is the two routes marked TODO.
Correctness before speed. The model runs on CPU this week; do not add a GPU.

Run it:
    uvicorn main:app --host 0.0.0.0 --port 8000

Model: Qwen/Qwen2.5-0.5B-Instruct (about 0.5B params; loads on CPU in seconds
once cached). The first ever load downloads weights; the prep-week verify-env
pass pre-seeded the Hugging Face cache, so a cached load is fast.
"""

import time
import torch
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from transformers import AutoModelForCausalLM, AutoTokenizer
import json


app = FastAPI()

# 1. تحميل النموذج والمزود (Tokenizer & Model Initialization)
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME, 
    torch_dtype=torch.float16, 
    device_map="auto"
)

# 2. نماذج الطلب والاستجابة (Pydantic Models)
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 256
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

class ResponseMessage(BaseModel):
    role: str
    content: str

class Choice(BaseModel):
    index: int
    message: ResponseMessage
    finish_reason: str

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: Usage


# 3. مسار التحقق من الصحة (Health Check)
@app.get("/health")
def health_check():
    return {"status": "ok"}


# 4. مسار عرض النماذج (Models List)
@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_NAME,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "organization-owner"
            }
        ]
    }

#--
# 5. مسار إكمال المحادثة الرئيسي
@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest):
    # تطبيق قالب المحادثة
    text = tokenizer.apply_chat_template(
        request.messages, 
        tokenize=False, 
        add_generation_prompt=True
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    prompt_tokens = inputs.input_ids.shape[1]
    
    temp = request.temperature if request.temperature is not None else 0.7
    do_samp = False if temp == 0.0 else True

    # إذا كان طلب الـ streaming مفعلاً (stream=True)
    if request.stream:
        from transformers import TextIteratorStreamer
        from threading import Thread

        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
        
        generation_kwargs = dict(
            **inputs,
            max_new_tokens=request.max_tokens or 256,
            temperature=temp if do_samp else None,
            do_sample=do_samp,
            streamer=streamer
        )
        
        # تشغيل التوليد في خيط منفصل (Background Thread) لكي يعمل الـ Streaming بسلاسة
        thread = Thread(target=model.generate, kwargs=generation_kwargs)
        thread.start()

        def generate():
            for new_text in streamer:
                if not new_text:
                    continue
                chunk_data = {
                    "id": "chatcmpl-123456",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": new_text},
                            "finish_reason": None
                        }
                    ]
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
            
            # الرسالة الأخيرة للإعلان عن انتهاء البث
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    # --- الحالة العادية (إذا كان stream=false) ---
    outputs = model.generate(
        **inputs,
        max_new_tokens=request.max_tokens or 256,
        temperature=temp if do_samp else None,
        do_sample=do_samp
    )
    
    generated_tokens = outputs[0][prompt_tokens:]
    content = tokenizer.decode(generated_tokens, skip_special_tokens=True)
    
    completion_tokens = len(generated_tokens)
    total_tokens = prompt_tokens + completion_tokens
    
    return ChatCompletionResponse(
        id="chatcmpl-123456",
        object="chat.completion",
        created=int(time.time()),
        model=request.model,
        choices=[
            Choice(
                index=0,
                message=ResponseMessage(role="assistant", content=content),
                finish_reason="stop"
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens
        )
    )
# ---------------------------------------------------------------------------
# Streaming is a DELTA STEP, not required for the green check. See the README.
# When you add it: same route, if req.stream is True return a
# StreamingResponse of Server-Sent Events. Each event is
#   data: {chat.completion.chunk with choices[0].delta.content}\n\n
# and the stream ends with the literal line
#   data: [DONE]\n\n
# ---------------------------------------------------------------------------
