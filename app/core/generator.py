import os

import anthropic


class Generator:
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        self.client = anthropic.Anthropic()
        self.model = model

    def generate(self, question: str, context_chunks: list[dict]) -> dict:
        context_text = "\n\n---\n\n".join(
            f"[Chunk {c['chunk_index'] + 1}] (similarity: {c['score']:.3f})\n{c['chunk_text']}"
            for c in context_chunks
        )

        system_prompt = (
            "You are a helpful assistant. Answer the user's question based ONLY on the "
            "provided context below. If the context does not contain enough information "
            "to answer the question, say so clearly. Cite which chunk(s) you used."
        )

        user_message = f"Context:\n{context_text}\n\nQuestion: {question}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        return {
            "system_prompt": system_prompt,
            "user_message": user_message,
            "llm_response": response.content[0].text,
            "llm_model": self.model,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }
