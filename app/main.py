from fastapi import FastAPI
from pydantic import BaseModel
from app.chatbot import ask


app = FastAPI(title="ERP Zapier-Style Chatbot")

class ChatRequest(BaseModel):
    question: str

@app.post("/chat")
def chat(req: ChatRequest):
    return {"answer": ask(req.question)}
