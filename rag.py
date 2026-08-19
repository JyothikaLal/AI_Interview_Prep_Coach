import json
import re
from pathlib import Path
from collections import Counter

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[1]
KB_DIR = ROOT_DIR / "data" / "kb"
INDEX_DIR = ROOT_DIR / "data" / "faiss_index"
INDEX_FILE = INDEX_DIR / "index.json"


class SimpleDocument:
    def __init__(self, page_content: str):
        self.page_content = page_content


class SimpleRetriever:
    def __init__(self, documents, vocabulary, vectors, k=3):
        self.documents = documents
        self.vocabulary = vocabulary
        self.vectors = vectors
        self.k = k

    def _tokenize(self, text: str):
        return re.findall(r"[a-zA-Z0-9]+", text.lower())

    def _vectorize(self, text: str):
        counts = Counter(self._tokenize(text))
        vector = np.zeros(len(self.vocabulary), dtype=float)
        for token, count in counts.items():
            if token in self.vocabulary:
                vector[self.vocabulary[token]] = count
        return vector

    def _cosine_similarity(self, a, b):
        dot = float(np.dot(a, b))
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        return 0.0 if norm == 0 else dot / norm

    def invoke(self, query: str, k=None):
        k = self.k if k is None else k
        query_vector = self._vectorize(query)
        scored = []
        for document, vector in zip(self.documents, self.vectors):
            scored.append((self._cosine_similarity(query_vector, vector), document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [SimpleDocument(doc["page_content"]) for _, doc in scored[:k]]


def build_index():
    docs = []
    for path in sorted(KB_DIR.glob("**/*.md")):
        docs.append({"source": str(path), "page_content": path.read_text(encoding="utf-8")})

    if not docs:
        raise FileNotFoundError(f"No markdown knowledge base files found in {KB_DIR}")

    vocabulary = {}
    for doc in docs:
        for token in re.findall(r"[a-zA-Z0-9]+", doc["page_content"].lower()):
            if token not in vocabulary:
                vocabulary[token] = len(vocabulary)

    vectors = []
    for doc in docs:
        counts = Counter(re.findall(r"[a-zA-Z0-9]+", doc["page_content"].lower()))
        vector = np.zeros(len(vocabulary), dtype=float)
        for token, count in counts.items():
            if token in vocabulary:
                vector[vocabulary[token]] = count
        vectors.append(vector)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "documents": docs,
        "vocabulary": vocabulary,
        "vectors": [vector.tolist() for vector in vectors],
    }
    INDEX_FILE.write_text(json.dumps(payload), encoding="utf-8")
    print(f"Indexed {len(docs)} document chunks.")


def load_retriever(k=3):
    if not INDEX_FILE.exists():
        build_index()

    payload = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    documents = payload["documents"]
    vocabulary = payload["vocabulary"]
    vectors = [np.array(vector, dtype=float) for vector in payload["vectors"]]
    return SimpleRetriever(documents, vocabulary, vectors, k=k)


if __name__ == "__main__":
    build_index()
