"""AI Assistant using GPT-5.4 via Emergent LLM key (emergentintegrations)."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import UserDep
from app.core.module_registry import module_gate
from app.core.repository import new_id, utcnow_iso

router = APIRouter(prefix="/ai", tags=["AI Assistant"], dependencies=[Depends(module_gate("ai"))])

TASK_SYSTEMS = {
    "summarize_client": "You are a CRM assistant. Given the client context, produce a concise executive summary (bullet points): who they are, current status, opportunities, risks, and 3 recommended next actions.",
    "generate_quote": "You are a CRM assistant. Draft a professional quotation given the requirements. Include: scope, deliverables, line items with placeholders for prices, timeline, validity period. Never invent numbers.",
    "draft_email": "You are a CRM assistant. Draft a polite, concise professional email to a client. Match the requested tone. Do not invent facts.",
    "analyze_sales": "You are a CRM assistant. Analyze the sales/pipeline data provided. Identify trends, risks, and give 5 actionable recommendations.",
    "suggest_followup": "You are a CRM assistant. Given the client context, suggest 3 specific follow-up actions with rationale and suggested timing.",
    "chat": "You are the AI Assistant for a CRM/ERP called NED Tech. Be concise, business-focused, and actionable.",
}


class AIRequest(BaseModel):
    task: str
    context: str
    session_id: Optional[str] = None


@router.get("/tasks")
async def list_tasks(user: UserDep):
    return [{"code": k, "label": k.replace("_", " ").title()} for k in TASK_SYSTEMS.keys()]


@router.post("/run")
async def run_ai(body: AIRequest, user: UserDep):
    if body.task not in TASK_SYSTEMS:
        raise HTTPException(400, "Unsupported task")
    if not settings.EMERGENT_LLM_KEY:
        raise HTTPException(503, "AI is not configured (missing EMERGENT_LLM_KEY)")

    system = TASK_SYSTEMS[body.task]
    session_id = body.session_id or f"{user.tenant_id}:{new_id()}"

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = (
            LlmChat(api_key=settings.EMERGENT_LLM_KEY, session_id=session_id, system_message=system)
            .with_model("openai", settings.LLM_MODEL)
        )
        result = await chat.send_message(UserMessage(text=body.context))
    except Exception as e:
        raise HTTPException(502, f"AI provider error: {e}")

    text = result if isinstance(result, str) else str(result)

    await get_db().ai_conversations.insert_one({
        "_id": new_id(), "id": new_id(), "tenant_id": user.tenant_id,
        "session_id": session_id, "task": body.task,
        "user_id": user.user_id, "prompt": body.context, "response": text,
        "created_at": utcnow_iso(),
    })
    return {"text": text, "session_id": session_id}


@router.get("/history")
async def history(user: UserDep, limit: int = 50):
    cur = get_db().ai_conversations.find(
        {"tenant_id": user.tenant_id}, {"_id": 0}
    ).sort([("created_at", -1)]).limit(limit)
    return await cur.to_list(length=limit)
