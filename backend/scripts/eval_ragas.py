#!/usr/bin/env python3
"""Ragas 离线评估 — ragas 0.4.x + 线程隔离 + 中文标签"""
import os, sys, json, time, types, math, logging, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "logs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)-5s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("eval_ragas")
_fh = logging.FileHandler(str(OUTPUT_DIR / "eval_ragas.log"), encoding="utf-8")
_fh.setLevel(logging.INFO); _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-5s] %(message)s", datefmt="%H:%M:%S"))
logging.getLogger().addHandler(_fh)
if "langchain_community.chat_models.vertexai" not in sys.modules:
    s = types.ModuleType("langchain_community.chat_models.vertexai"); s.ChatVertexAI = type("ChatVertexAI", (), {})
    sys.modules["langchain_community.chat_models.vertexai"] = s
TEST_FILE = "/Users/wangjie/RAGData/05_评估集/检索评估测试集.jsonl"
METRIC_LABELS = {
    "context_precision": "检索精度",
    "context_recall":    "检索召回",
    "faithfulness":      "忠实度",
}

def load_cases(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]

def _eval_one(case, api_key):
    from ragas import evaluate, EvaluationDataset, SingleTurnSample
    from ragas.metrics import Faithfulness, ContextPrecision, ContextRecall
    from ragas.llms import LangchainLLMWrapper
    from langchain_openai import ChatOpenAI
    llm = LangchainLLMWrapper(ChatOpenAI(model="qwen-max", api_key=api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", temperature=0.0, max_tokens=200))
    sample = SingleTurnSample(user_input=case["question"], response=case["answer"], retrieved_contexts=[case["source"]], reference=case["answer"])
    ds = EvaluationDataset(samples=[sample])
    r = evaluate(dataset=ds, metrics=[ContextPrecision(), ContextRecall(), Faithfulness()], llm=llm)
    def _v(k):
        val = r[k]; v = float(val[0] if isinstance(val, list) else val)
        return None if (isinstance(val, list) and math.isnan(v)) else round(v, 4)
    return {"qid": case["qid"], "type": case["type"], "question": case["question"][:55],
        "检索精度": _v("context_precision"), "检索召回": _v("context_recall"),
        "忠实度": _v("faithfulness")}

def score_str(r):
    parts = []
    for k_cn in ["检索精度","检索召回","忠实度"]:
        v = r.get(k_cn)
        if v is None: parts.append(f"{k_cn}=N/A")
        else: parts.append(f"{k_cn}={v:.3f}")
    return "  ".join(parts)

def avg_from(valid, key_cn):
    vals = [r[key_cn] for r in valid if r.get(key_cn) is not None]
    return round(sum(vals)/len(vals), 4) if vals else None

def main():
    logger.info("=" * 55)
    logger.info("Ragas 离线评估 — 指标: 检索精度 | 检索召回 | 忠实度 | 回答相关性")
    cases = load_cases(TEST_FILE); total = len(cases)
    logger.info("测试用例: %d 条", total)
    from app.core.config import get_settings
    api_key = get_settings().dashscope_api_key or os.environ.get("DASHSCOPE_API_KEY","")
    api_key = api_key or "sk-f8acbc094bd54275b739a842d2273038"
    if not api_key: logger.error("DASHSCOPE_API_KEY 未配置！"); return 1
    os.environ["DASHSCOPE_API_KEY"] = api_key; os.environ["OPENAI_API_KEY"] = api_key
    results = []; start = time.time()
    with ThreadPoolExecutor(max_workers=1) as pool:
        for i, case in enumerate(cases):
            qid, qt = case["qid"], case["type"]
            logger.info("[%2d/%2d] %s (%s) %s", i+1, total, qid, qt, case["question"][:50])
            try:
                r = pool.submit(_eval_one, case, api_key).result(timeout=120)
                results.append(r)
                logger.info("       %s", score_str(r))
            except Exception as e:
                logger.error("       ❌ 失败: %s", str(e)[:120])
                results.append({"qid": qid, "type": qt, "question": case["question"][:50], "error": str(e)[:200]})
    elapsed = time.time() - start
    valid = [r for r in results if "error" not in r]
    bt = {}
    for r in valid:
        t = r["type"]
        if t not in bt: bt[t] = {"n":0,"prec":[],"recall":[],"faith":[]}
        b = bt[t]; b["n"] += 1
        for k_cn, k_list in [("检索精度","prec"),("检索召回","recall"),("忠实度","faith")]:
            v = r.get(k_cn)
            if v is not None: b[k_list].append(v)
    logger.info("=" * 55)
    logger.info("完成: %d/%d 条, 耗时 %.0f 秒", len(valid), total, elapsed)
    logger.info("")
    logger.info("按类型汇总:")
    for t in sorted(bt):
        b = bt[t]; n = b["n"]
        parts = [f"{t}(n={n})"]
        for k_cn, k_list in [("检索精度","prec"),("检索召回","recall"),("忠实度","faith")]:
            if b[k_list]: parts.append(f"{k_cn}={sum(b[k_list])/len(b[k_list]):.3f}")
            else: parts.append(f"{k_cn}=N/A")
        logger.info("  %s", "  ".join(parts))
    logger.info("")
    logger.info("总体平均:")
    parts = [f"n={len(valid)}"]
    for k_cn in ["检索精度","检索召回","忠实度"]:
        a = avg_from(valid, k_cn)
        parts.append(f"{k_cn}={a:.3f}" if a is not None else f"{k_cn}=N/A")
    logger.info("  %s", "  ".join(parts))
    out = OUTPUT_DIR / "ragas_eval_report.json"
    summary = {"total": total, "valid": len(valid), "elapsed_seconds": round(elapsed,1),
        "note": "回答相关性(AnswerRelevancy)在 DashScope 下不可用(Ragas 内部硬编码调用 OpenAI Embedding API)"}
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, ensure_ascii=False, indent=2)
    logger.info("")
    logger.info("JSON 报告: %s", out)
    logger.info("文本日志: %s", OUTPUT_DIR / "eval_ragas.log")
    return 0

if __name__ == "__main__":
    sys.exit(main())
