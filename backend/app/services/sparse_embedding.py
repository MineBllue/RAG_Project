
"""
稀疏向量生成 - TfidfVectorizer（每个知识库独立词汇表）
输出 {int: float} 格式，兼容 Milvus SPARSE_FLOAT_VECTOR
"""
import jieba
import pickle
import os
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from app.core.config import get_settings

settings = get_settings()


def _tokenize(text: str) -> str:
    return " ".join(w.strip() for w in jieba.cut(text) if len(w.strip()) > 1)


# 每个知识库独立的 vectorizer 缓存
_vectorizers: Dict[int, TfidfVectorizer] = {}


def _get_cache_path(kb_id: int) -> str:
    return os.path.join(settings.data_dir, f"tfidf_kb_{kb_id}.pkl")


def build_vocab(texts: List[str], kb_id: int = 0):
    """用文档集合构建 Tfidf 词汇表（按知识库隔离）"""
    tokenized = [_tokenize(t) for t in texts]
    vec = TfidfVectorizer(max_features=5000, token_pattern=r"(?u)\b\w+\b")
    vec.fit(tokenized)
    _vectorizers[kb_id] = vec
    # 持久化到磁盘
    os.makedirs(settings.data_dir, exist_ok=True)
    with open(_get_cache_path(kb_id), "wb") as f:
        pickle.dump(vec, f)


def load_vocab(kb_id: int):
    """从磁盘加载词汇表"""
    if kb_id in _vectorizers:
        return
    path = _get_cache_path(kb_id)
    if os.path.exists(path):
        with open(path, "rb") as f:
            _vectorizers[kb_id] = pickle.load(f)


def encode_sparse(texts: List[str], kb_id: int = 0) -> List[Dict[int, float]]:
    """生成稀疏 Tfidf 向量 [{int_index: float_weight}, ...]"""
    load_vocab(kb_id)
    if kb_id not in _vectorizers:
        build_vocab(texts, kb_id)

    vec = _vectorizers[kb_id]
    tokenized = [_tokenize(t) for t in texts]
    result = vec.transform(tokenized)
    vectors = []
    for row in result:
        nonzero = row.nonzero()[1]
        if len(nonzero) > 0:
            vectors.append({int(idx): float(row[0, idx]) for idx in nonzero})
        else:
            vectors.append({0: 1e-6})
    return vectors
