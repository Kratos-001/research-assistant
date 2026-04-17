# Agentic Document Research Assistant

A powerful, multi-agent AI system designed to analyze, summarize, fact-check, and intelligently query complex academic and research documents. Built heavily on modern Agentic workflows using **LangGraph**, **FastAPI**, and **React**.

## 🧠 The Agentic Engine

Unlike standard RAG (Retrieval-Augmented Generation) applications that blindly vector-search text, this application features an autonomous **Multi-Agent Pipeline** driven by strict decision trees.

### Agent Breakdown:
1. **Guardrail Agent**: Acts as the system’s bouncer. Analyzes user queries to ensure they are strictly related to document research, gracefully rejecting irrelevant topics or malicious prompt injections.
2. **Orchestrator Agent**: The central router. Evaluates document context and your query, checking against a strict decision hierarchy to autonomously route the workload to the best specialist agent. If the context is ambiguous across multiple documents, it intelligently pauses execution to ask the user for clarification.
3. **Fact-Check Agent**: Verifies highly specific TRUE/FALSE claims. Evaluates hypotheses against the raw text and delivers a structured verdict (TRUE / FALSE / CONFLICTED / NOT MENTIONED), always explicitly quoting its sources.
4. **Analysis Agent**: Synthesizes broad information. Fetches extensive context and constructs dense, multi-layer JSON responses encompassing executive summaries, key achievements, methodological gaps, and hidden ("big picture") risks.
5. **Retrieval Agent**:
   - *Metadata Layer*: Directly pulls from a structured SQL database when you lookup authors, publishing dates, abstract, or journals.
   - *Content Layer*: Exclusively activates for specialized needle-in-the-haystack text excerpt extraction, equipped with strict vector distance thresholds to block hallucinated "garbage" chunks.

## ⚙️ Architecture Profile

- **Backend**: Python, FastAPI, LangGraph
- **Frontend**: React (Vite)
- **Vector Database**: ChromaDB (locally persisted)
- **Metadata Registry**: SQLite (for structured metadata identity mapping)
- **Embedding Model**: `all-MiniLM-L6-v2` via SentenceTransformers
- **LLM Engine**: OpenAI GPT-4o & GPT-4o-mini

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js (v18+)
- An active OpenAI API Key

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your environment variables by creating a `.env` file in the `/backend` directory containing your API key:
   ```env
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   ```
5. Start the FastAPI server (runs on `http://127.0.0.1:8080`):
   ```bash
   python -m uvicorn main:app --reload --port 8080
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Run the Vite development server:
   ```bash
   npm run dev
   ```
4. Open your browser and navigate to the localhost port provided (usually `http://localhost:5173`).

## 💬 How to Command the Agents
Because this system is powered by strict Orchestrator decision logic, you can summon specific agents just by how you phrase your question:
- **Summon Fact-Check**: Ask true/false or hypothesis questions like *"did the study find XYZ?"* or *"does this paper mention Epstein?"*.
- **Summon Analysis**: Ask broad extraction or synthesis questions like *"what are the risks?"*, *"give me the details"*, or *"what were the main achievements?"*.
- **Summon Metadata Retrieval**: Process paper identity lookups like *"who wrote this paper?"* or *"what year was this published?"*.
