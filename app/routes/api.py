import os
import uuid

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse

from app.core.chunker import chunk_text
from app.core.generator import Generator
from app.core.pdf_extractor import extract_text_from_pdf
from app.models.schemas import (
    EmbeddingPreview,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    SampleDetail,
    SampleInfo,
    SimilarityResult,
)
from app.samples.content import DEMO_QUESTIONS, SAMPLES

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/api/health", response_model=HealthResponse)
async def health(request: Request):
    embedding_service = request.app.state.embedding_service
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        lm_studio_available=embedding_service.health_check(),
        embedding_model=settings.embedding_model,
        anthropic_key_set=bool(os.environ.get("ANTHROPIC_API_KEY")),
    )


@router.get("/api/samples", response_model=list[SampleInfo])
async def list_samples():
    return [
        SampleInfo(id=s["id"], title=s["title"], preview=s["text"][:200] + "...")
        for s in SAMPLES.values()
    ]


@router.get("/api/samples/{sample_id}", response_model=SampleDetail)
async def get_sample(sample_id: str):
    sample = SAMPLES.get(sample_id)
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    return SampleDetail(
        id=sample["id"],
        title=sample["title"],
        text=sample["text"],
        suggested_questions=DEMO_QUESTIONS.get(sample_id, []),
    )


@router.post("/api/ingest", response_model=IngestResponse)
async def ingest(request: Request, body: IngestRequest):
    settings = request.app.state.settings
    embedding_service = request.app.state.embedding_service
    vector_store = request.app.state.vector_store

    text = body.text.strip()
    if len(text) > 100_000:
        raise HTTPException(status_code=400, detail="Text too large (max 100KB)")
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty")

    chunks = chunk_text(text, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    chunk_texts = [c["text"] for c in chunks]

    embeddings = embedding_service.embed(chunk_texts)
    doc_id = str(uuid.uuid4())[:8]
    vector_store.store(doc_id, chunks, embeddings)

    embedding_previews = [
        EmbeddingPreview(
            chunk_index=i,
            preview=embeddings[i][:10].tolist(),
            dimensions=embeddings.shape[1],
        )
        for i in range(len(chunks))
    ]

    return IngestResponse(
        doc_id=doc_id,
        chunks=[
            {"index": c["index"], "text": c["text"], "start_char": c["start_char"], "end_char": c["end_char"]}
            for c in chunks
        ],
        chunk_count=len(chunks),
        embeddings=embedding_previews,
        total_characters=len(text),
    )


@router.post("/api/ingest-file", response_model=IngestResponse)
async def ingest_file(request: Request, file: UploadFile):
    settings = request.app.state.settings
    embedding_service = request.app.state.embedding_service
    vector_store = request.app.state.vector_store

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    suffix = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if suffix not in ("pdf", "txt", "md"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload a .pdf, .txt, or .md file.")

    contents = await file.read()
    if len(contents) > 10_000_000:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    if suffix == "pdf":
        try:
            text = extract_text_from_pdf(contents)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        text = contents.decode("utf-8").strip()

    if not text:
        raise HTTPException(status_code=400, detail="File contains no text")
    if len(text) > 100_000:
        raise HTTPException(status_code=400, detail="Extracted text too large (max 100KB)")

    chunks = chunk_text(text, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    chunk_texts = [c["text"] for c in chunks]

    embeddings = embedding_service.embed(chunk_texts)
    doc_id = str(uuid.uuid4())[:8]
    vector_store.store(doc_id, chunks, embeddings)

    embedding_previews = [
        EmbeddingPreview(
            chunk_index=i,
            preview=embeddings[i][:10].tolist(),
            dimensions=embeddings.shape[1],
        )
        for i in range(len(chunks))
    ]

    return IngestResponse(
        doc_id=doc_id,
        chunks=[
            {"index": c["index"], "text": c["text"], "start_char": c["start_char"], "end_char": c["end_char"]}
            for c in chunks
        ],
        chunk_count=len(chunks),
        embeddings=embedding_previews,
        total_characters=len(text),
    )


@router.post("/api/query", response_model=QueryResponse)
async def query(request: Request, body: QueryRequest):
    settings = request.app.state.settings
    embedding_service = request.app.state.embedding_service
    vector_store = request.app.state.vector_store

    doc = vector_store.get(body.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found. Ingest a document first.")

    query_embedding = embedding_service.embed([body.question])
    query_vec = query_embedding[0]

    results = vector_store.search(body.doc_id, query_vec, top_k=settings.top_k)

    try:
        generator = Generator(model=settings.llm_model)
        gen_result = generator.generate(body.question, results)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")

    similarity_results = [
        SimilarityResult(
            chunk_index=r["chunk_index"],
            chunk_text=r["chunk_text"],
            score=r["score"],
            embedding_preview=r["embedding_preview"],
        )
        for r in results
    ]

    return QueryResponse(
        question=body.question,
        question_embedding_preview=query_vec[:10].tolist(),
        similarity_results=similarity_results,
        context_assembled=gen_result["user_message"],
        prompt_sent_to_llm=f"System: {gen_result['system_prompt']}\n\nUser: {gen_result['user_message']}",
        llm_response=gen_result["llm_response"],
        llm_model=gen_result["llm_model"],
        total_chunks_searched=len(doc.chunks),
        top_k=settings.top_k,
    )


@router.delete("/api/documents/{doc_id}")
async def delete_document(request: Request, doc_id: str):
    vector_store = request.app.state.vector_store
    deleted = vector_store.delete(doc_id)
    return {"success": deleted}
