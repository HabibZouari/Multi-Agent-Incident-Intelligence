import os
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from backend.models.db import SessionLocal, DocumentModel
import numpy as np

class HybridRetriever:
    def __init__(self):
        pass

    def get_embedding(self, text_content: str) -> List[float]:
        np.random.seed(abs(hash(text_content.lower())) % (2**32))
        vec = np.random.randn(1536)
        vec = vec / np.linalg.norm(vec)
        return vec.tolist()

    def search(self, query: str, top_k: int = 5, service_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        session = SessionLocal()
        try:
            # Check if using SQLite or Postgres
            is_sqlite = "sqlite" in str(session.bind.url)

            query_embedding = self.get_embedding(query)

            if is_sqlite:
                # Fallback retrieval for SQLite
                docs = session.query(DocumentModel).all()
                scored = []
                for doc in docs:
                    doc_vec = np.array(doc.embedding) if doc.embedding else np.zeros(1536)
                    q_vec = np.array(query_embedding)
                    sim = float(np.dot(q_vec, doc_vec) / (np.linalg.norm(q_vec) * np.linalg.norm(doc_vec) + 1e-8))
                    scored.append({
                        "document_id": doc.document_id,
                        "filename": doc.filename,
                        "document_type": doc.document_type,
                        "service_name": doc.service_name,
                        "chunk_id": doc.chunk_id,
                        "content": doc.content,
                        "score": max(0.0, sim),
                        "source": f"{doc.filename} (Chunk {doc.chunk_id})"
                    })
                scored.sort(key=lambda x: x["score"], reverse=True)
                return scored[:top_k]
            else:
                vec_str = "[" + ",".join(map(str, query_embedding)) + "]"
                sql = """
                    SELECT document_id, filename, document_type, service_name, chunk_id, content,
                           (embedding <=> CAST(:query_vec AS vector)) as distance
                    FROM documents
                """
                params = {"query_vec": vec_str}

                if service_filter:
                    sql += " WHERE service_name = :service_name"
                    params["service_name"] = service_filter

                sql += " ORDER BY distance ASC LIMIT :top_k;"
                params["top_k"] = top_k

                result = session.execute(text(sql), params).fetchall()

                retrieved_chunks = []
                for row in result:
                    similarity = 1.0 - float(row.distance)
                    retrieved_chunks.append({
                        "document_id": row.document_id,
                        "filename": row.filename,
                        "document_type": row.document_type,
                        "service_name": row.service_name,
                        "chunk_id": row.chunk_id,
                        "content": row.content,
                        "score": max(0.0, similarity),
                        "source": f"{row.filename} (Chunk {row.chunk_id})"
                    })

                return retrieved_chunks
        finally:
            session.close()

if __name__ == "__main__":
    retriever = HybridRetriever()
    results = retriever.search("authentication timeout error", top_k=3)
    print(f"Retrieved {len(results)} chunks for test query.")
    for r in results:
        print(f"- [{r['score']:.4f}] {r['source']}: {r['content'][:100]}...")
