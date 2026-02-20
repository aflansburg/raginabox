import httpx
import numpy as np


class EmbeddingService:
    def __init__(self, base_url: str = "http://localhost:1234/v1", model: str = "nomic-embed-text-v1.5"):
        self.base_url = base_url
        self.model = model
        self.client = httpx.Client(timeout=60.0)

    def embed(self, texts: list[str]) -> np.ndarray:
        """Embed a list of texts. Returns shape (n, dim) numpy array."""
        response = self.client.post(
            f"{self.base_url}/embeddings",
            json={"input": texts, "model": self.model},
            headers={"Authorization": "Bearer lm-studio"},
        )
        response.raise_for_status()
        data = response.json()
        embeddings = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
        return np.array(embeddings, dtype=np.float32)

    def health_check(self) -> bool:
        try:
            resp = self.client.get(f"{self.base_url}/models", timeout=5.0)
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False
