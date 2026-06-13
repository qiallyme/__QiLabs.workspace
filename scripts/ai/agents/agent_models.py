"""
Pydantic models for QiOS Local Core API requests/responses.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime


class IngestRequest(BaseModel):
    """Request model for POST /ingest."""
    file_path: str
    slug: str
    mime_type: Optional[str] = None
    file_ext: Optional[str] = None
    content: str
    realm: Optional[str] = None
    qid: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class IngestResponse(BaseModel):
    """Response model for POST /ingest."""
    ok: bool
    id: str


class IngestStatusResponse(BaseModel):
    """Response model for GET /ingest/{id}."""
    id: str
    file_path: str
    status: str
    slug: Optional[str] = None
    realm: Optional[str] = None
    created_at: str
    updated_at: str
    error: Optional[str] = None


class QueryRequest(BaseModel):
    """Request model for POST /query."""
    query: str
    limit: int = 10


class QueryResult(BaseModel):
    """Single result in query response."""
    source_id: str
    score: float
    content: str
    file_path: Optional[str] = None
    slug: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for POST /query."""
    results: List[QueryResult]


class ChatMessage(BaseModel):
    """Single message in chat conversation."""
    role: str  # "system" | "user" | "assistant"
    content: str


class GinaChatRequest(BaseModel):
    """Request model for POST /gina/chat.
    
    Follows OpenAI Chat Completions format.
    GINA automatically injects its system prompt, so user-provided system messages
    are preserved but GINA's prompt takes precedence.
    """
    messages: List[ChatMessage]
    with_voice: Optional[bool] = False  # If true, indicates frontend will call /gina/tts separately
    mode: Optional[str] = "chat"  # "chat" or "voice" - hint for response length


class QueueContext(BaseModel):
    """Ingestion queue state."""
    total: int
    by_status: Dict[str, int]


class WorkerContext(BaseModel):
    """Worker status information."""
    name: str
    status: str
    last_heartbeat: Optional[str]
    meta: Dict[str, Any]


class HealthContext(BaseModel):
    """System health information."""
    status: str
    runtime: str
    last_tick: Optional[str]
    layers: Optional[Dict[str, Any]] = None


class GinaChatContext(BaseModel):
    """Optional structured context about system state."""
    queue: Optional[QueueContext] = None
    workers: Optional[List[WorkerContext]] = None
    health: Optional[HealthContext] = None


class ToolSuggestion(BaseModel):
    """A tool that GINA suggests using."""
    tool: str
    label: str
    args: Dict[str, Any]


class SourceReference(BaseModel):
    """A source reference from RAG retrieval."""
    id: str  # e.g., "S1", "S2"
    file_path: str
    score: float


class GinaChatResponse(BaseModel):
    """Response model for POST /gina/chat.
    
    Always includes `reply` (GINA's text response).
    Optionally includes `context` with live system telemetry (queue, workers, health).
    Optionally includes `tool_suggestions` for actions GINA recommends.
    Optionally includes `retrieval_used` and `sources` if RAG was used.
    """
    reply: str
    context: Optional[GinaChatContext] = None
    tool_suggestions: Optional[List[ToolSuggestion]] = None
    retrieval_used: Optional[bool] = False
    sources: Optional[List[SourceReference]] = None


class ToolInvokeRequest(BaseModel):
    """Request model for POST /tools/invoke."""
    tool: str
    args: Dict[str, Any]


class ToolInvokeResponse(BaseModel):
    """Response model for POST /tools/invoke."""
    ok: bool
    tool: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class GinaTTSRequest(BaseModel):
    """Request model for POST /gina/tts."""
    text: str
    voice_id: Optional[str] = None  # Optional ElevenLabs voice ID
    model_id: Optional[str] = None  # Optional ElevenLabs model ID


class JobCreateRequest(BaseModel):
    """Request model for POST /jobs."""
    job_type: str
    params: Optional[Dict[str, Any]] = None


class JobResponse(BaseModel):
    """Response model for job operations."""
    id: int
    job_type: str
    status: str
    params: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class DevCodeAssistRequest(BaseModel):
    """Request model for POST /dev/code_assist.
    
    Dev-specific endpoint that always queries dev_error_log before generating suggestions.
    """
    file_path: str
    snippet: str
    symbol: Optional[str] = None
    question: Optional[str] = None


class DevCodeAssistResponse(BaseModel):
    """Response model for POST /dev/code_assist."""
    answer: str
    used_errors: List[Dict[str, Any]] = []


# Notes API models (QiNote v2.0)
class NoteBase(BaseModel):
    """Base note model with common fields."""
    title: str
    slug: str
    realm: str
    content_md: str
    content_html: Optional[str] = None
    tags: Optional[List[str]] = None
    backlinks: Optional[List[str]] = None
    sensitivity: Optional[str] = "internal"
    metadata: Optional[Dict[str, Any]] = None


class NoteCreate(NoteBase):
    """Request model for POST /notes."""
    pass


class NoteUpdate(BaseModel):
    """Request model for PUT /notes/{id}."""
    title: Optional[str] = None
    slug: Optional[str] = None
    realm: Optional[str] = None
    content_md: Optional[str] = None
    content_html: Optional[str] = None
    tags: Optional[List[str]] = None
    backlinks: Optional[List[str]] = None
    sensitivity: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Note(NoteBase):
    """Response model for note operations."""
    id: str
    created_at: str
    updated_at: str


# Note Assist API models
class NoteAssistRequest(BaseModel):
    """Request model for POST /gina/note_assist."""
    intent: str  # "summarize" | "rewrite" | "outline" | "tag" | "qa"
    note: Dict[str, Any]  # Note object with id, title, realm, content_md, tags
    selection: Optional[Dict[str, Any]] = None
    user_instruction: Optional[str] = None


class NoteAssistResponse(BaseModel):
    """Response model for POST /gina/note_assist."""
    intent: str
    summary_md: Optional[str] = None
    rewritten_md: Optional[str] = None
    outline_md: Optional[str] = None
    suggested_tags: Optional[List[str]] = None
    answer_md: Optional[str] = None