"""
稀疏向量生成 - TfidfVectorizer（无需下载模型，离线可用）
输出 {int: float} 格式，兼容 Milvus SPARSE_FLOAT_VECTOR
"""
import jieba
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


def _tokenize(text: str) -> str:
    return " ".join(w.strip() for w in jieba.cut(text) if len(w.strip()) > 1)


_vectorizer: TfidfVectorizer = None


def build_vocab(texts: List[str]):
    """用文档集合构建 Tfidf 词汇表"""
    global _vectorizer
    tokenized = [_tokenize(t) for t in texts]
    _vectorizer = TfidfVectorizer(max_features=5000, token_pattern=r"(?u)\b\w+\b")
    _vectorizer.fit(tokenized)


def encode_sparse(texts: List[str]) -> List[Dict[int, float]]:
    """生成稀疏 Tfidf 向量 [{int_index: float_weight}, ...]"""
    global _vectorizer
    if _vectorizer is None:
        tokenized = [_tokenize(t) for t in texts]
        _vectorizer = TfidfVectorizer(max_features=5000, token_pattern=r"(?u)\b\w+\b")
        _vectorizer.fit(tokenized)

    tokenized = [_tokenize(t) for t in texts]
    result = _vectorizer.transform(tokenized)
    vectors = []
    for row in result:
        nonzero = row.nonzero()[1]
        if len(nonzero) > 0:
            vectors.append({int(idx): float(row[0, idx]) for idx in nonzero})
        else:
            vectors.append({0: 1e-6})
    return vectors
