from pydantic import BaseModel


class IngestRequest(BaseModel):
    text: str


class QueryRequest(BaseModel):
    doc_id: str
    question: str


class ChunkInfo(BaseModel):
    index: int
    text: str
    start_char: int
    end_char: int


class EmbeddingPreview(BaseModel):
    chunk_index: int
    preview: list[float]
    dimensions: int


class IngestResponse(BaseModel):
    doc_id: str
    chunks: list[ChunkInfo]
    chunk_count: int
    embeddings: list[EmbeddingPreview]
    total_characters: int


class SimilarityResult(BaseModel):
    chunk_index: int
    chunk_text: str
    score: float
    embedding_preview: list[float]


class QueryResponse(BaseModel):
    question: str
    question_embedding_preview: list[float]
    similarity_results: list[SimilarityResult]
    context_assembled: str
    prompt_sent_to_llm: str
    llm_response: str
    llm_model: str
    total_chunks_searched: int
    top_k: int


class HealthResponse(BaseModel):
    status: str
    lm_studio_available: bool
    embedding_model: str
    anthropic_key_set: bool


class SampleInfo(BaseModel):
    id: str
    title: str
    preview: str


class SampleDetail(BaseModel):
    id: str
    title: str
    text: str
    suggested_questions: list[str] = []
