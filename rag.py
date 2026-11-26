"""Module 2 - RAG pipeline: chunking, embeddings (ChromaDB + MiniLM, TF-IDF fallback) and retrieval."""
from __future__ import annotations
import tempfile
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .ingestion import read_file, _sentences

_EMBED = None  # embedding model loaded once, reused across rebuilds

class SemanticVectorStore:
    """ChromaDB vector store using all-MiniLM-L6-v2 sentence embeddings."""
    def __init__(self):
        self.client = None
        self.collection = None
        self.mode = "tfidf-fallback"
        self.error = None
        self._temp_dir = None
        try:
            import chromadb
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            self._temp_dir = tempfile.mkdtemp(prefix="projectiq_chroma_")
            self.client = chromadb.PersistentClient(path=self._temp_dir)
            global _EMBED
            if _EMBED is None:
                _EMBED = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            embedding_fn = _EMBED
            self.collection = self.client.get_or_create_collection(
                name="project_documents", embedding_function=embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
            self.mode = "semantic-chromadb"
        except Exception as exc:
            self.error = str(exc)
            self.client = self.collection = None

    def add_chunks(self, chunks):
        if not self.collection or not chunks:
            return
        # Chroma limits batch sizes; small batches are more memory-friendly.
        for start in range(0, len(chunks), 64):
            batch = chunks[start:start + 64]
            self.collection.add(
                ids=[f"chunk-{start+i}" for i in range(len(batch))],
                documents=[item[1] for item in batch],
                metadatas=[{"source": item[0]} for item in batch],
            )

    def search(self, question, k=4):
        if not self.collection or self.collection.count() == 0:
            return []
        result = self.collection.query(query_texts=[question], n_results=min(k, self.collection.count()))
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        # Chroma cosine distance: convert to a bounded similarity estimate.
        return [((meta.get("source", "Unknown"), doc), max(0.0, 1.0-float(dist)))
                for doc, meta, dist in zip(docs, metas, distances)]


class KB:
    def __init__(self):
        self.docs, self.lines, self.tasks, self.chunks = [], [], [], []
        self.vec = None
        self.matrix = None
        self.vector_store = SemanticVectorStore()
        self.retrieval_mode = self.vector_store.mode

    @property
    def text_lines(self):
        """Sentences from prose documents; CSV rows are analysed structurally via self.tasks instead."""
        return [(n, t) for n, t in self.lines if not n.lower().endswith('.csv')]

    def add(self, name, data):
        text, tasks = read_file(name, data)
        self.docs.append({"name": name, "chars": len(text), "type": name.rsplit(".", 1)[-1].upper()})
        self.tasks.extend(tasks)
        sentences = _sentences(text)
        self.lines.extend((name, sentence) for sentence in sentences)
        # Three-sentence windows with a two-sentence stride retain overlap/context.
        for index in range(0, len(sentences), 2):
            chunk = " ".join(sentences[index:index+3])
            if chunk:
                self.chunks.append((name, chunk))

    def build(self):
        if self.vector_store.collection:
            try:
                self.vector_store.add_chunks(self.chunks)
                self.retrieval_mode = "semantic-chromadb"
                return
            except Exception as exc:
                self.vector_store.error = str(exc)
                self.retrieval_mode = "tfidf-fallback"
        if self.chunks:
            self.vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
            try:
                self.matrix = self.vec.fit_transform([chunk for _, chunk in self.chunks])
            except ValueError:
                self.vec = self.matrix = None

    def search(self, question, k=4):
        if self.retrieval_mode == "semantic-chromadb":
            try:
                return self.vector_store.search(question, k)
            except Exception:
                self.retrieval_mode = "tfidf-fallback"
        if self.vec is None or self.matrix is None or not question.strip():
            return []
        query = self.vec.transform([question])
        scores = cosine_similarity(query, self.matrix)[0]
        ranked = scores.argsort()[::-1][:k]
        return [(self.chunks[i], float(scores[i])) for i in ranked]

