"""
FastAPI Application for LangGraph Multi-Agent Educational Generator & PDF Studio
================================================================================
Exposes REST endpoints to generate zero-knowledge educational content,
stream/serve generated PDFs and Markdown, and provide an interactive Chat & PDF Viewer UI.
"""

import os
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Import the modular education system
import education_system

# Initialize FastAPI app
app = FastAPI(
    title="Zero-Knowledge Educational AI Studio",
    description="Multi-agent educational content generation pipeline with interactive PDF viewer",
    version="1.0.0"
)

# Enable CORS for development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = "Output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ==========================================
# Request & Response Models
# ==========================================
class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=300, description="The educational topic to generate.")
    recursion_limit: Optional[int] = Field(default=15, ge=5, le=30, description="Maximum graph recursion limit.")


class GenerateResponse(BaseModel):
    topic: str
    final_content: str
    revision_count: int
    markdown_filename: Optional[str]
    pdf_filename: Optional[str]
    pdf_url: Optional[str]
    markdown_url: Optional[str]
    concepts: list[str] = []
    is_satisfactory: bool = True


# ==========================================
# API Endpoints
# ==========================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    has_keys = bool(os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
    return {
        "status": "healthy",
        "api_key_configured": has_keys,
        "output_directory": os.path.abspath(OUTPUT_DIR)
    }


@app.get("/api/documents")
async def list_documents():
    """Returns all available generated educational PDF and Markdown documents."""
    try:
        docs = await asyncio.to_thread(education_system.get_available_documents, output_folder=OUTPUT_DIR)
        for doc in docs:
            if doc.get("pdf_filename"):
                doc["pdf_url"] = f"/api/pdf/{doc['pdf_filename']}"
            if doc.get("markdown_filename"):
                doc["markdown_url"] = f"/api/markdown/{doc['markdown_filename']}"
        return {"documents": docs, "total": len(docs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_lesson(req: GenerateRequest):
    """
    Triggers the LangGraph multi-agent pipeline to generate educational content and PDF.
    Runs asynchronously in a threadpool so the server event loop is not blocked.
    """
    topic = req.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic must not be empty.")

    try:
        # Run graph in threadpool
        result = await asyncio.to_thread(
            education_system.generate_educational_content,
            topic=topic,
            output_folder=OUTPUT_DIR,
            recursion_limit=req.recursion_limit
        )

        pdf_filename = result.get("pdf_filename")
        md_filename = result.get("markdown_filename")

        return GenerateResponse(
            topic=result["topic"],
            final_content=result["final_content"],
            revision_count=result["revision_count"],
            markdown_filename=md_filename,
            pdf_filename=pdf_filename,
            pdf_url=f"/api/pdf/{pdf_filename}" if pdf_filename else None,
            markdown_url=f"/api/markdown/{md_filename}" if md_filename else None,
            concepts=result.get("concepts", []),
            is_satisfactory=result.get("is_satisfactory", True)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.get("/api/pdf/{filename}")
async def get_pdf(filename: str, download: bool = Query(False, description="Force file download")):
    """
    Serves the generated PDF file.
    Supports inline browser rendering (for <iframe> / built-in viewers) or attachment download.
    """
    # Sanitize filename
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(OUTPUT_DIR, safe_filename)

    if not os.path.exists(file_path):
        # Fallback check in root directory
        if os.path.exists(safe_filename):
            file_path = safe_filename
        else:
            raise HTTPException(status_code=404, detail=f"PDF '{safe_filename}' not found.")

    disposition = "attachment" if download else "inline"
    headers = {
        "Content-Disposition": f'{disposition}; filename="{safe_filename}"',
        "Cache-Control": "public, max-age=3600"
    }

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        headers=headers,
        filename=safe_filename
    )


@app.get("/api/markdown/{filename}")
async def get_markdown(filename: str):
    """Fetches raw markdown content for a given filename."""
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(OUTPUT_DIR, safe_filename)
    if not os.path.exists(file_path):
        file_path = safe_filename
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Markdown file '{safe_filename}' not found.")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {"filename": safe_filename, "content": content}


# ==========================================
# Frontend Single-Page Chat & PDF Studio UI
# ==========================================
HTML_TEMPLATE_PATH = os.path.join("templates", "index.html")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the interactive Chat & PDF Studio frontend."""
    if os.path.exists(HTML_TEMPLATE_PATH):
        with open(HTML_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        # Fallback inline response
        return HTMLResponse(content="<h1>Educational AI Studio</h1><p>Template loading...</p>")


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting FastAPI Server on http://127.0.0.1:8000 ...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
