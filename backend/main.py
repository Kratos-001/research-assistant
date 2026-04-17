import io
import json
import PyPDF2
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Union
import uvicorn

from tools.metadata_store import init_db, list_documents, get_metadata, delete_metadata, get_paper_metadata
from tools.document_tools import get_client as get_chroma_client, store_document
from agents.document_agent import _extract_paper_metadata
from tools.metadata_store import save_metadata

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


from graph import build_graph
agent_graph = build_graph()


ALLOWED_EXTENSIONS = {".pdf", ".txt"}
MAX_FILE_SIZE_MB = 20
MAX_FILE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def _extract_text(content: bytes, filename: str) -> str:
    if filename.endswith(".pdf"):
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            raise HTTPException(status_code=422, detail="Could not parse PDF. The file may be corrupted or encrypted.")
    else:
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=422, detail="TXT file must be UTF-8 encoded.")


def _validate_file(content: bytes, filename: str):
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Only PDF and TXT files are accepted.")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum is {MAX_FILE_SIZE_MB} MB.")


# ── Upload endpoint — extracts metadata immediately on file drop ───────────

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Called as soon as the user drops a file.

    1. Validates the file
    2. Chunks + embeds → ChromaDB
    3. Extracts paper metadata (title, authors, abstract, etc.) → SQLite
    4. Returns the metadata immediately so the UI can display it
    """
    content = await file.read()
    _validate_file(content, file.filename)

    text = _extract_text(content, file.filename)

    if len(text.strip()) < 200:
        raise HTTPException(status_code=422, detail="Document has too little extractable text.")

    # Chunk + embed → ChromaDB
    collection_name, total_chunks = store_document(file.filename, text)

    # Extract structured metadata → SQLite
    paper_metadata = _extract_paper_metadata(text)
    save_metadata(
        file_name=file.filename,
        collection_name=collection_name,
        total_chunks=total_chunks,
        char_count=len(text),
        paper_metadata=paper_metadata,
    )

    return {
        "collection_name": collection_name,
        "file_name": file.filename,
        "total_chunks": total_chunks,
        "paper_metadata": paper_metadata,
    }


# ── Analyze endpoint — runs agent pipeline across one or more collections ─────

class AnalyzeRequest(BaseModel):
    collection_names: Union[list, str]   # list of collection names or "all"
    file_names: Union[list, str]         # parallel list of file names or "all"
    query: str
    skip_clarification: bool = False     # True when user explicitly chose "both papers"


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """Runs the LangGraph pipeline across one or more pre-uploaded documents."""

    if req.collection_names == "all":
        docs = list_documents()
        if not docs:
            raise HTTPException(status_code=400, detail="No documents uploaded yet.")
        collection_names = [d["collection_name"] for d in docs]
        file_names = [d["file_name"] for d in docs]
    else:
        collection_names = req.collection_names
        file_names = req.file_names if isinstance(req.file_names, list) else []
        if not collection_names:
            raise HTTPException(status_code=400, detail="No papers selected.")

    # Pad file_names if shorter
    while len(file_names) < len(collection_names):
        file_names.append("unknown")

    result = agent_graph.invoke(
        {
            "user_query": req.query,
            "document_text": "",
            "file_name": file_names[0],
            "collection_name": collection_names[0],
            "collection_names": collection_names,
            "file_names": file_names,
            "guardrail_blocked": None,
            "route": None,
            "routing_reason": None,
            "clarification_question": None,
            "skip_clarification": req.skip_clarification,
            "retrieval_result": None,
            "factcheck_result": None,
            "analysis_result": None,
            "final_response": None,
            "error": None,
        }
    )

    if result.get("guardrail_blocked"):
        return {"error": result.get("error"), "route": None, "result": None}

    active_agent = result.get("route")

    # Clarification requested — no agent ran
    if active_agent == "clarification":
        return {
            "route": "clarification",
            "routing_reason": result.get("routing_reason"),
            "clarification_question": result.get("clarification_question"),
            "result": None,
            "collection_names": collection_names,
            "file_names": file_names,
            "error": None,
        }

    agent_result = result.get(f"{active_agent}_result") if active_agent else None

    return {
        "route": active_agent,
        "routing_reason": result.get("routing_reason"),
        "clarification_question": None,
        "result": agent_result,
        "collection_names": collection_names,
        "file_names": file_names,
        "error": result.get("error"),
    }


# ── Metadata registry endpoints ────────────────────────────────────────────

@app.get("/documents")
def get_documents():
    return {"documents": list_documents()}


@app.get("/documents/{collection_name}")
def get_document(collection_name: str):
    doc = get_metadata(collection_name)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.delete("/documents/{collection_name}")
def delete_document(collection_name: str):
    removed = delete_metadata(collection_name)
    if not removed:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        get_chroma_client().delete_collection(collection_name)
    except Exception:
        pass
    return {"deleted": collection_name}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
