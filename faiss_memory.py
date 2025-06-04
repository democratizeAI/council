# faiss_memory.py – 60‑line helper that plugs Agent‑Zero "Memory" mixin into our Prom/Router stack
# ------------------------------------------------------------------------------
# Usage:
#   memory = FaissMemory(db_path="memory")
#   uid = memory.add("hello world", {"role": "user"})
#   hits = memory.query("world", k=3)
# ------------------------------------------------------------------------------

from __future__ import annotations
import os, json, time, hashlib, sqlite3, threading, pathlib
from typing import List, Dict, Any

import numpy as np
import faiss                    # pip install faiss-cpu
from sentence_transformers import SentenceTransformer  # tiny all‑MiniLM by default

from prometheus_client import Counter, Summary

MEM_ADD = Counter("swarm_memory_add_total", "Items added to FAISS memory")
MEM_QRY = Summary("swarm_memory_query_latency_seconds", "Latency of memory queries")

_EMB = SentenceTransformer(os.getenv("MEM_EMB_MODEL", "all-MiniLM-L6-v2"))
_LOCK = threading.Lock()

class FaissMemory:  # minimal implementation of Agent‑Zero Memory API
    def __init__(self, db_path: str = "memory"):
        self.db_dir = pathlib.Path(db_path)
        self.db_dir.mkdir(exist_ok=True, parents=True)
        self.meta_path = self.db_dir / "meta.jsonl"
        self.index_path = str(self.db_dir / "index.faiss")

        d = _EMB.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatIP(d)  # cosine via normalised vectors

        if self.meta_path.exists() and pathlib.Path(self.index_path).exists():
            self._load()
        else:
            self.meta: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    def _persist(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "w") as f:
            for m in self.meta:
                f.write(json.dumps(m) + "\n")

    def _load(self):
        self.index = faiss.read_index(self.index_path)
        with open(self.meta_path) as f:
            self.meta = [json.loads(l) for l in f]

    # ------------------------------------------------------------------
    def _embed(self, txt: str) -> np.ndarray:
        v = _EMB.encode([txt])[0]
        return v / np.linalg.norm(v)

    def add(self, text: str, meta: Dict[str, Any] | None = None) -> str:
        meta = meta or {}
        uid = hashlib.sha1(f"{time.time_ns()}-{text}".encode()).hexdigest()[:12]
        vec = self._embed(text).astype("float32")
        with _LOCK:
            self.index.add(vec.reshape(1, -1))
            self.meta.append({"id": uid, "text": text, **meta})
            if len(self.meta) % 100 == 0:  # light persistence
                self._persist()
        MEM_ADD.inc()
        return uid

    @MEM_QRY.time()
    def query(self, text: str, k: int = 5, thresh: float = 0.35) -> List[Dict[str, Any]]:
        if len(self.meta) == 0:
            return []
        qv = self._embed(text).astype("float32").reshape(1, -1)
        D, I = self.index.search(qv, k)
        hits = []
        for score, idx in zip(D[0], I[0]):
            if idx == -1 or score < thresh:
                continue
            rec = self.meta[idx].copy()
            rec["score"] = float(score)
            hits.append(rec)
        return hits

    # optional convenience
    def flush(self):
        with _LOCK:
            self._persist()

# ------------------------------------------------------------------
# Quick sanity check when run directly
if __name__ == "__main__":
    mem = FaissMemory()
    mem.add("Paris is the capital of France", {"tag": "fact"})
    print(mem.query("capital of france")) 