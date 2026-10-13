from fastapi import APIRouter
from pydantic import BaseModel

from app.ai.agent import ask_database


router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(request: ChatRequest):

    answer = ask_database(request.message)

    return {
        "answer": answer
    }