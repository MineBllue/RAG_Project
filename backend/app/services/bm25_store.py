import os
import pickle
import jieba
from typing import List, Dict, Tuple
from collections import defaultdict
from rank_bm25 import BM25Okapi
from app.core.config import get_settings

settings = get_settings()

class BM25Store:
    """BM25 稀疏检索索引"""

    def __init__(self):
        self._indices: Dict[int, Tuple[BM25Okapi, list, list]] = {}

    def _tokenize(self, text: str) -> List[str]:
        return [w.strip() for w in jieba.cut(text) if w.strip() and len(w.strip()) > 1]

    def _get_path(self, kb_id: int) -> str:
        return os.path.join(settings.data_dir, f"bm25_kb_{kb_id}.pkl")

    def build(self, kb_id: int, chunks: List[dict]):
        """构建 BM25 索引"""
        tokenized = [self._tokenize(c["text"] if isinstance(c, dict) else c) for c in chunks]
        docs = [c["text"] if isinstance(c, dict) else c for c in chunks]
        bm25 = BM25Okapi(tokenized)
        self._indices[kb_id] = (bm25, tokenized, docs)
        with open(self._get_path(kb_id), "wb") as f:
            pickle.dump((tokenized, docs), f)

    def load(self, kb_id: int):
        """加载索引"""
        if kb_id in self._indices:
            return
        path = self._get_path(kb_id)
        if os.path.exists(path):
            with open(path, "rb") as f:
                tokenized, docs = pickle.load(f)
            bm25 = BM25Okapi(tokenized)
            self._indices[kb_id] = (bm25, tokenized, docs)

    def search(self, kb_id: int, query: str, top_k: int = 5) -> List[dict]:
        """BM25 检索"""
        self.load(kb_id)
        if kb_id not in self._indices:
            return []
        bm25, tokenized, docs = self._indices[kb_id]
        tokens = self._tokenize(query)
        scores = bm25.get_scores(tokens)
        idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        results = []
        for i in idxs:
            if scores[i] > 0:
                results.append({"text": docs[i], "score": float(scores[i]), "type": "bm25"})
        return results

bm25_store = BM25Store()
