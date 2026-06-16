import os
import io
import edge_tts
import io
from typing import Optional
from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from dotenv import load_dotenv
import edge_tts

from db.database import init_db, create_conversation, get_conversations, get_conversation, get_messages, save_message, update_conversation_title, delete_conversation
from agent.providers import AIProvider
from agent.core import run_agent
from agent.prompts import ORCHESTRATOR_SYSTEM

load_dotenv()

app = FastAPI(title="Trillion Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

_instances = {}

def get_provider(provider_name: str) -> AIProvider:
    key = f"provider_{provider_name}"
    if key not in _instances:
        api_key = GROQ_API_KEY if provider_name == "groq" else OPENROUTER_API_KEY
        if not api_key:
            raise HTTPException(400, f"{provider_name} API key not configured. Set {provider_name.upper()}_API_KEY in .env")
        _instances[key] = AIProvider(provider_name, api_key)
    return _instances[key]


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    provider: str = "openrouter"
    model: str = "openrouter/free"


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str


class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-GuyNeural"


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/api/conversations")
async def list_conversations():
    return get_conversations()


@app.get("/api/conversations/{cid}")
async def get_convo(cid: str):
    convo = get_conversation(cid)
    if not convo:
        raise HTTPException(404, "Conversation not found")
    msgs = get_messages(cid)
    return {"conversation": convo, "messages": msgs}


@app.delete("/api/conversations/{cid}")
async def delete_convo(cid: str):
    delete_conversation(cid)
    return {"ok": True}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    cid = req.conversation_id

    if not cid:
        cid = create_conversation(provider=req.provider, model=req.model)
    else:
        convo = get_conversation(cid)
        if not convo:
            raise HTTPException(404, "Conversation not found")

    save_message(cid, "user", req.message)

    provider = get_provider(req.provider)
    msgs = get_messages(cid)
    history = [{"role": m["role"], "content": m["content"]} for m in msgs]

    try:
        reply, usage, _ = await run_agent(
            provider=provider,
            model=req.model,
            messages=history,
            system_prompt=ORCHESTRATOR_SYSTEM,
        )
    except Exception as e:
        reply = f"Error: {str(e)}"

    save_message(cid, "assistant", reply)

    if len(get_messages(cid)) <= 2:
        title = req.message[:50].strip()
        if len(req.message) > 50:
            title += "..."
        update_conversation_title(cid, title)

    return ChatResponse(reply=reply, conversation_id=cid)


class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-JennyNeural"


@app.post("/api/tts")
async def text_to_speech(req: TTSRequest):
    communicate = edge_tts.Communicate(req.text, req.voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return Response(content=audio_data, media_type="audio/mpeg")


@app.post("/api/tts-form")
async def text_to_speech_form(text: str = Form(...), voice: str = Form("en-US-JennyNeural")):
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return Response(content=audio_data, media_type="audio/mpeg")


@app.post("/api/tts")
async def text_to_speech(req: TTSRequest):
    try:
        communicate = edge_tts.Communicate(req.text, req.voice)
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])
        audio_data.seek(0)
        return StreamingResponse(
            audio_data,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"},
        )
    except Exception as e:
        raise HTTPException(500, f"TTS error: {str(e)}")
