
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility, AnnSearchRequest, WeightedRanker
import logging
from typing import List, Optional, Dict, Any, Set
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

FIELD_ID = "id"
FIELD_TEXT = "text"
FIELD_VECTOR = "vector"
FIELD_SPARSE = "sparse_vector"
FIELD_DOC_ID = "doc_id"
FIELD_KB_ID = "kb_id"
FIELD_CHUNK_ID = "chunk_id"
FIELD_TYPE = "content_type"
FIELD_CHUNK_TYPE = "chunk_type"
FIELD_PARENT_ID = "parent_chunk_id"

DENSE_DIM = 1024
INDEX_PARAMS = {"metric_type": "IP", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
SPARSE_INDEX_PARAMS = {"metric_type": "IP", "index_type": "SPARSE_INVERTED_INDEX"}

_connected = False


def _connect():
    """连接 Milvus（幂等，已连接则跳过）"""
    global _connected
    if _connected:
        return
    try:
        connections.connect(alias="default", host=settings.milvus_host, port=settings.milvus_port)
        _connected = True
        logger.info("Milvus connected: %s:%s", settings.milvus_host, settings.milvus_port)
    except Exception:
        logger.exception("Milvus connection failed")
        raise


def disconnect_milvus():
    """断开 Milvus 连接（在 shutdown 时调用）"""
    global _connected
    if _connected:
        try:
            connections.disconnect("default")
        except Exception:
            pass
        _connected = False


def get_collection_name(kb_id: int) -> str:
    return f"{settings.milvus_collection_name}_kb{kb_id}"


def create_collection(kb_id: int):
    _connect()
    col_name = get_collection_name(kb_id)
    if utility.has_collection(col_name):
        col = Collection(col_name)
        # 验证所有必需字段都存在，缺失任一字段则重建
        required_fields = {FIELD_SPARSE, FIELD_PARENT_ID, FIELD_DOC_ID, FIELD_KB_ID, FIELD_CHUNK_ID, FIELD_TYPE, FIELD_CHUNK_TYPE}
        existing_fields = {f.name for f in col.schema.fields}
        missing = required_fields - existing_fields
        if missing:
            print(f"[vector_store] Collection {col_name} 缺少字段 {missing}，自动重建")
            utility.drop_collection(col_name)
        else:
            col.load()
            return

    fields = [
        FieldSchema(name=FIELD_ID, dtype=DataType.VARCHAR, max_length=100, is_primary=True),
        FieldSchema(name=FIELD_TEXT, dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name=FIELD_VECTOR, dtype=DataType.FLOAT_VECTOR, dim=DENSE_DIM),
        FieldSchema(name=FIELD_SPARSE, dtype=DataType.SPARSE_FLOAT_VECTOR),
        FieldSchema(name=FIELD_DOC_ID, dtype=DataType.INT64),
        FieldSchema(name=FIELD_KB_ID, dtype=DataType.INT64),
        FieldSchema(name=FIELD_CHUNK_ID, dtype=DataType.INT64),
        FieldSchema(name=FIELD_TYPE, dtype=DataType.VARCHAR, max_length=20),
        FieldSchema(name=FIELD_CHUNK_TYPE, dtype=DataType.VARCHAR, max_length=20),
        FieldSchema(name=FIELD_PARENT_ID, dtype=DataType.INT64),
    ]
    schema = CollectionSchema(fields, description=f"KB {kb_id}")
    col = Collection(col_name, schema)
    col.create_index(FIELD_VECTOR, INDEX_PARAMS)
    col.create_index(FIELD_SPARSE, SPARSE_INDEX_PARAMS)
    col.load()


def insert_vectors(kb_id: int, records: List[dict]):
    _connect()
    ensure_collection(kb_id)
    col_name = get_collection_name(kb_id)
    col = Collection(col_name)
    BATCH = 100
    for i in range(0, len(records), BATCH):
        batch = records[i:i + BATCH]
        # 确保所有字段存在默认值
        for r in batch:
            r.setdefault(FIELD_CHUNK_TYPE, "child")
            r.setdefault(FIELD_PARENT_ID, 0)
        col.insert(batch)
    col.flush()


_COLLECTION_FIELD_CACHE: Dict[str, Set[str]] = {}


def _get_existing_fields(kb_id: int) -> Set[str]:
    """获取 Collection 中实际存在的字段名集合（带缓存）"""
    col_name = get_collection_name(kb_id)
    if col_name in _COLLECTION_FIELD_CACHE:
        return _COLLECTION_FIELD_CACHE[col_name]
    _connect()
    if not utility.has_collection(col_name):
        return set()
    col = Collection(col_name)
    fields = {f.name for f in col.schema.fields}
    _COLLECTION_FIELD_CACHE[col_name] = fields
    return fields


def _safe_output_fields(kb_id: int, wanted: List[str]) -> List[str]:
    """过滤出 Collection 中实际存在的 output_fields"""
    existing = _get_existing_fields(kb_id)
    if not existing:
        return wanted  # collection 不存在时原样返回
    return [f for f in wanted if f in existing]


def search_vectors(kb_id: int, query_vector: List[float], top_k: int = 5,
                   filter_expr: Optional[str] = None) -> List[dict]:
    """稠密向量检索（支持过滤表达式）"""
    _connect()
    col_name = get_collection_name(kb_id)
    if not utility.has_collection(col_name):
        return []

    col = Collection(col_name)
    col.load()
    search_params = {"metric_type": "IP", "params": {"nprobe": 16}}
    output_fields = _safe_output_fields(kb_id, [FIELD_TEXT, FIELD_DOC_ID, FIELD_KB_ID, FIELD_TYPE,
                                                FIELD_CHUNK_ID, FIELD_CHUNK_TYPE, FIELD_PARENT_ID])
    # 检查 filter 字段是否存在
    if filter_expr and FIELD_CHUNK_TYPE not in _get_existing_fields(kb_id):
        filter_expr = None
    results = col.search(
        data=[query_vector],
        anns_field=FIELD_VECTOR,
        param=search_params,
        limit=top_k,
        output_fields=output_fields,

        expr=filter_expr,
    )

    return [
        {"text": hit.entity.get(FIELD_TEXT), "score": hit.distance,
         "doc_id": hit.entity.get(FIELD_DOC_ID), "kb_id": hit.entity.get(FIELD_KB_ID),
         "chunk_id": hit.entity.get(FIELD_CHUNK_ID), "content_type": hit.entity.get(FIELD_TYPE, "text"),
         "chunk_type": hit.entity.get(FIELD_CHUNK_TYPE, "child"),
         "parent_chunk_id": hit.entity.get(FIELD_PARENT_ID, 0)}
        for hits in results for hit in hits
    ]


def search_sparse(kb_id: int, sparse_vector: dict, top_k: int = 5) -> List[dict]:
    """稀疏向量检索"""
    _connect()
    col_name = get_collection_name(kb_id)
    if not utility.has_collection(col_name):
        return []
    col = Collection(col_name)
    col.load()
    output_fields = _safe_output_fields(kb_id, [FIELD_TEXT, FIELD_DOC_ID, FIELD_KB_ID, FIELD_TYPE,
                                                FIELD_CHUNK_ID, FIELD_CHUNK_TYPE, FIELD_PARENT_ID])
    results = col.search(
        data=[sparse_vector],
        anns_field=FIELD_SPARSE,
        param={"metric_type": "IP"},
        limit=top_k,
        output_fields=output_fields,
    )
    return [
        {"text": hit.entity.get(FIELD_TEXT), "score": hit.distance,
         "doc_id": hit.entity.get(FIELD_DOC_ID), "kb_id": hit.entity.get(FIELD_KB_ID),
         "type": "sparse", "chunk_id": hit.entity.get(FIELD_CHUNK_ID),
         "chunk_type": hit.entity.get(FIELD_CHUNK_TYPE, "child"),
         "parent_chunk_id": hit.entity.get(FIELD_PARENT_ID, 0)}
        for hits in results for hit in hits
    ]


def hybrid_search_vectors(kb_id: int, dense_vector: List[float], sparse_vector: dict,
                          top_k: int = 10, dense_weight: float = 0.6,
                          filter_fn=None) -> List[dict]:
    """稠密+稀疏混合检索（Milvus 原生 Hybrid Search，PyMilvus 3.x 不支持 expr，用 filter_fn 过滤）"""
    _connect()
    col_name = get_collection_name(kb_id)
    if not utility.has_collection(col_name):
        return []
    col = Collection(col_name)
    col.load()

    output_fields = _safe_output_fields(kb_id, [FIELD_TEXT, FIELD_DOC_ID, FIELD_KB_ID, FIELD_TYPE,
                                                FIELD_CHUNK_ID, FIELD_CHUNK_TYPE, FIELD_PARENT_ID])

    dense_req = AnnSearchRequest(
        data=[dense_vector],
        anns_field=FIELD_VECTOR,
        param={"metric_type": "IP", "params": {"nprobe": 16}},
        limit=top_k
    )
    sparse_req = AnnSearchRequest(
        data=[sparse_vector],
        anns_field=FIELD_SPARSE,
        param={"metric_type": "IP"},
        limit=top_k
    )
    rerank = WeightedRanker(dense_weight, 1 - dense_weight)

    results = col.hybrid_search(
        reqs=[dense_req, sparse_req],
        rerank=rerank,
        limit=top_k,
        output_fields=output_fields,
    )
    items = [
        {"text": hit.entity.get(FIELD_TEXT), "final_score": hit.distance,
         "doc_id": hit.entity.get(FIELD_DOC_ID), "kb_id": hit.entity.get(FIELD_KB_ID),
         "chunk_id": hit.entity.get(FIELD_CHUNK_ID),
         "chunk_type": hit.entity.get(FIELD_CHUNK_TYPE, "child"),
         "parent_chunk_id": hit.entity.get(FIELD_PARENT_ID, 0)}
        for hits in results for hit in hits
    ]
    # PyMilvus 3.x hybrid_search 不支持 expr → Python 侧过滤
    if filter_fn:
        items = [it for it in items if filter_fn(it)]
    return items


def fetch_by_ids(kb_id: int, ids: List[int], id_field: str = FIELD_CHUNK_ID) -> List[dict]:
    """根据 ID 列表批量取回向量记录"""
    _connect()
    col_name = get_collection_name(kb_id)
    if not utility.has_collection(col_name):
        return []
    col = Collection(col_name)
    col.load()
    if not ids:
        return []
    id_strs = ", ".join(str(i) for i in ids)
    expr = f"{id_field} in [{id_strs}]"
    output_fields = [FIELD_TEXT, FIELD_DOC_ID, FIELD_KB_ID, FIELD_TYPE,
                     FIELD_CHUNK_ID, FIELD_CHUNK_TYPE, FIELD_PARENT_ID]
    try:
        results = col.query(expr=expr, output_fields=output_fields, limit=len(ids) * 2)
        return results
    except Exception:
        return []


def search_with_parent_context(kb_id: int, dense_vector: List[float],
                               sparse_vector: dict, top_k: int = 5,
                               dense_weight: float = 0.6) -> List[dict]:
    """
    父子检索：先匹配子块，再取父块上下文

    策略:
    1. 先搜索子块 (chunk_type == "child")，取 top_k 个最相关的
    2. 提取这些子块的 parent_chunk_id
    3. 从 Milvus 取回对应的父块
    4. 将父块作为最终上下文返回（去重）
    """
    # 检查 Collection 是否支持父子检索
    existing_fields = _get_existing_fields(kb_id)
    if FIELD_CHUNK_TYPE not in existing_fields or FIELD_PARENT_ID not in existing_fields:
        # 降级为普通混合检索
        return hybrid_search_vectors(kb_id, dense_vector, sparse_vector,
                                     top_k=top_k, dense_weight=dense_weight)

    # 第一步：仅搜索子块
    child_results = hybrid_search_vectors(
        kb_id, dense_vector, sparse_vector,
        top_k=top_k, dense_weight=dense_weight,
        filter_fn=lambda it: it.get("chunk_type") == "child"
    )

    if not child_results:
        return []

    # 第二步：收集父块 ID
    parent_ids = set()
    for cr in child_results:
        pid = cr.get("parent_chunk_id", 0)
        if pid and pid > 0:
            parent_ids.add(pid)

    if not parent_ids:
        # 没有父子结构，直接返回子块结果
        return child_results

    # 第三步：取回父块
    parent_records = fetch_by_ids(kb_id, list(parent_ids), FIELD_CHUNK_ID)
    parent_map = {pr[FIELD_CHUNK_ID]: pr for pr in parent_records}

    # 第四步：为每个匹配子块附上父块上下文，去重返回
    seen_parents = set()
    final_results = []
    for cr in child_results:
        pid = cr.get("parent_chunk_id", 0)
        if pid in parent_map and pid not in seen_parents:
            parent = parent_map[pid]
            final_results.append({
                "text": parent.get(FIELD_TEXT, ""),
                "final_score": cr["final_score"],
                "doc_id": cr["doc_id"],
                "kb_id": cr["kb_id"],
                "chunk_id": parent.get(FIELD_CHUNK_ID),
                "chunk_type": "parent",
                "child_matches": [{"score": cr["final_score"],
                                   "text": cr["text"][:200]}],
            })
            seen_parents.add(pid)
        elif pid not in seen_parents:
            final_results.append(cr)

    return final_results


def delete_collection(kb_id: int):
    _connect()
    col_name = get_collection_name(kb_id)
    if utility.has_collection(col_name):
        utility.drop_collection(col_name)


def ensure_collection(kb_id: int):
    _connect()
    col_name = get_collection_name(kb_id)
    if utility.has_collection(col_name):
        col = Collection(col_name)
        has_sparse = any(f.name == FIELD_SPARSE for f in col.schema.fields)
        has_parent = any(f.name == FIELD_PARENT_ID for f in col.schema.fields)
        if not has_sparse or not has_parent:
            utility.drop_collection(col_name)
        else:
            col.load()
            return
    create_collection(kb_id)
