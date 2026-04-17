import io
import PyPDF2
from dotenv import load_dotenv
load_dotenv()  # loads ANTHROPIC_API_KEY from .env automatically
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from tools.metadata_store import init_db, list_documents, get_metadata, delete_metadata
from tools.document_tools import get_client as get_chroma_client

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()  # create SQLite table if it doesn't exist


from graph import build_graph

agent_graph = build_graph()


# ── Main analysis endpoint ─────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {".pdf", ".txt"}
ALLOWED_CONTENT_TYPES = {"application/pdf", "text/plain"}
MAX_FILE_SIZE_MB = 20
MAX_FILE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


@app.post("/analyze")
async def analyze(file: UploadFile = File(...), query: str = Form(...)):
    # ── File-level guardrails ──────────────────────────────────────────────
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Only PDF and TXT files are accepted.",
        )

    content = await file.read()

    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(content) / 1024 / 1024:.1f} MB). Maximum allowed size is {MAX_FILE_SIZE_MB} MB.",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if file.filename.endswith(".pdf"):
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            raise HTTPException(status_code=422, detail="Could not parse PDF. The file may be corrupted or encrypted.")
    else:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=422, detail="TXT file must be UTF-8 encoded.")

    result = agent_graph.invoke(
        {
            "user_query": query,
            "document_text": text,
            "file_name": file.filename,
            "collection_name": None,   # set by document_agent (Agent 1)
            "guardrail_blocked": None,
            "route": None,
            "routing_reason": None,
            "retrieval_result": None,
            "factcheck_result": None,
            "analysis_result": None,
            "final_response": None,
            "error": None,
        }
    )

    active_agent = result["route"]
    agent_result = result.get(f"{active_agent}_result")

    return {
        "route": active_agent,
        "routing_reason": result["routing_reason"],
        "result": agent_result,
        "file_name": file.filename,
        "collection_name": result.get("collection_name"),
        "error": result.get("error"),
    }


# ── Metadata registry endpoints ────────────────────────────────────────────

@app.get("/documents")
def get_documents():
    """List all documents stored in the metadata registry (SQLite), newest first."""
    return {"documents": list_documents()}


@app.get("/documents/{collection_name}")
def get_document(collection_name: str):
    """Fetch metadata for a single document by its ChromaDB collection name."""
    doc = get_metadata(collection_name)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.delete("/documents/{collection_name}")
def delete_document(collection_name: str):
    """Remove a document from both the SQLite registry and ChromaDB."""
    # Delete from SQLite
    removed = delete_metadata(collection_name)
    if not removed:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from ChromaDB
    try:
        get_chroma_client().delete_collection(collection_name)
    except Exception:
        pass  # already gone or never existed in chroma

    return {"deleted": collection_name}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
