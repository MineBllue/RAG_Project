#!/usr/bin/env python3
"""Ragas 离线评估 — ragas 0.4.x + 线程隔离"""
import os, sys, json, time, types, math, logging, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)-5s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("eval_ragas")
if "langchain_community.chat_models.vertexai" not in sys.modules:
    s = types.ModuleType("langchain_community.chat_models.vertexai"); s.ChatVertexAI = type("ChatVertexAI", (), {})
    sys.modules["langchain_community.chat_models.vertexai"] = s
TEST_FILE = "/Users/wangjie/RAGData/05_评估集/检索评估测试集.jsonl"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "logs"

def load_cases(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]

def _eval_one(case, api_key):
    from ragas import evaluate, EvaluationDataset, SingleTurnSample
    from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall
    from ragas.llms import LangchainLLMWrapper
    from langchain_openai import ChatOpenAI
    llm = LangchainLLMWrapper(ChatOpenAI(model="qwen-max", api_key=api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", temperature=0.0, max_tokens=200))
    sample = SingleTurnSample(user_input=case["question"], response=case["answer"], retrieved_contexts=[case["source"]], reference=case["answer"])
    ds = EvaluationDataset(samples=[sample])
    r = evaluate(dataset=ds, metrics=[ContextPrecision(), ContextRecall(), Faithfulness(), AnswerRelevancy()], llm=llm)
    def _v(k):
        val = r[k]; v = float(val[0] if isinstance(val, list) else val)
        return None if (isinstance(val, list) and math.isnan(v)) else round(v, 4)
    return {"qid": case["qid"], "type": case["type"], "question": case["question"][:55],
        "context_precision": _v("context_precision"), "context_recall": _v("context_recall"),
        "faithfulness": _v("faithfulness"), "answer_relevancy": _v("answer_relevancy")}

def main():
    logger.info("=" * 55); logger.info("Ragas 离线评估")
    cases = load_cases(TEST_FILE); total = len(cases)
    logger.info("%d 条测试用例", total)
    from app.core.config import get_settings
    api_key = get_settings().dashscope_api_key or os.environ.get("DASHSCOPE_API_KEY","")
    # 兜底硬编码（conda run 环境下 .env 可能不生效）
    api_key = api_key or "sk-f8acbc094bd54275b739a842d2273038"
    if not api_key: logger.error("DASHSCOPE_API_KEY 未配置！"); return 1
    os.environ["DASHSCOPE_API_KEY"] = api_key
    os.environ["OPENAI_API_KEY"] = api_key
    results = []; start = time.time()
    with ThreadPoolExecutor(max_workers=1) as pool:
        for i, case in enumerate(cases):
            qid, qt = case["qid"], case["type"]
            logger.info("[%2d/%2d] %s (%s) %s", i+1, total, qid, qt, case["question"][:50])
            try:
                r = pool.submit(_eval_one, case, api_key).result(timeout=120)
                results.append(r)
                ar = f"relev={r['answer_relevancy']}" if r['answer_relevancy'] is not None else "relev=N/A"
                logger.info("       prec=%.3f recall=%.3f faith=%.3f %s", r["context_precision"], r["context_recall"], r["faithfulness"], ar)
            except Exception as e:
                logger.error("       FAILED: %s", str(e)[:120])
                results.append({"qid": qid, "type": qt, "question": case["question"][:50], "error": str(e)[:200]})
    elapsed = time.time() - start
    valid = [r for r in results if "error" not in r]
    bt = {}
    for r in valid:
        t = r["type"]
        if t not in bt: bt[t] = {"n":0,"p":0,"r":0,"f":0,"a":0,"ac":0}
        b = bt[t]; b["n"] += 1; b["p"] += r["context_precision"]; b["r"] += r["context_recall"]; b["f"] += r["faithfulness"]
        if r["answer_relevancy"] is not None: b["a"] += r["answer_relevancy"]; b["ac"] += 1
    logger.info("=" * 55); logger.info("完成: %d/%d, %.0f秒", len(valid), total, elapsed)
    for t in sorted(bt):
        b = bt[t]; n = b["n"]
        ar = f"relev={b['a']/b['ac']:.3f}" if b["ac"] > 0 else "relev=N/A"
        logger.info("  %-12s(n=%2d): prec=%.3f recall=%.3f faith=%.3f %s", t, n, b["p"]/n, b["r"]/n, b["f"]/n, ar)
    avg = {}
    if valid:
        for k in ["context_precision","context_recall","faithfulness","answer_relevancy"]:
            vals = [r[k] for r in valid if r.get(k) is not None]
            avg[k] = round(sum(vals)/len(vals),4) if vals else None
        ar = f"relev={avg['answer_relevancy']:.3f}" if avg.get("answer_relevancy") else "relev=N/A"
        logger.info("总体(n=%d): prec=%.3f recall=%.3f faith=%.3f %s", len(valid), avg["context_precision"], avg["context_recall"], avg["faithfulness"], ar)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / "ragas_eval_report.json"
    st = {"total": total, "valid": len(valid), "elapsed_seconds": round(elapsed,1), "note": "answer_relevancy 在 DashScope 下不可用", "by_type": {}, "avg": avg}
    for t, b in bt.items():
        st["by_type"][t] = {"count": b["n"], "precision": round(b["p"]/b["n"],4), "recall": round(b["r"]/b["n"],4), "faithfulness": round(b["f"]/b["n"],4)}
        if b["ac"] > 0: st["by_type"][t]["relevancy"] = round(b["a"]/b["ac"],4)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"summary": st, "results": results}, f, ensure_ascii=False, indent=2)
    logger.info("结果: %s", out)
    return 0

if __name__ == "__main__":
    sys.exit(main())
