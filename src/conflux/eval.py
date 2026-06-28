"""评估管线 — 对 Golden Dataset 跑 LLM-as-Judge 评估（§7.2）

使用独立模型评估系统回答的忠实度、完整性、权威性、平衡性、诚实性。
"""

import sys
import yaml
from pathlib import Path

# 确保 conflux 可导入
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models import BaseChatModel

from conflux.config import load as load_config
from conflux.model_factory import create_chat_model

JUDGE_PROMPT = """你是一个严格的评估者。根据以下标准对系统回答评分（1-5分）：

1. 忠实度 (1-5)：回答中的每个声明是否有检索到的证据支持？
2. 完整性 (1-5)：是否回答了用户问题的所有方面？
3. 权威性 (1-5)：引用的来源是否具有高权威性？
4. 平衡性 (1-5)：对于有争议的话题，是否呈现了多视角？
5. 诚实性 (1-5)：是否明确标注了不确定性和信息缺失？

用户问题：{query}
系统回答：{answer}

请仅输出以下 JSON 格式（不要其他文字）：
{{"faithfulness": N, "completeness": N, "authority": N, "balance": N, "honesty": N, "overall": N, "comments": "简短评语"}}
"""


def judge_answer(query: str, answer: str, judge_model: BaseChatModel) -> dict:
    """LLM-as-Judge 评分"""
    prompt = JUDGE_PROMPT.format(query=query, answer=answer[:3000])
    messages = [
        SystemMessage(content="你是一个严格且公平的评估者。只输出 JSON。"),
        HumanMessage(content=prompt),
    ]
    response = judge_model.invoke(messages)
    content = str(response.content)

    # 尝试解析 JSON
    import json
    # 提取 JSON 块
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        return {"error": "JSON parse failed", "raw": content[:200]}


def load_golden_dataset(path: str = "data/golden_dataset.yaml") -> list[dict]:
    """加载 Golden Dataset"""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, list) else []


def run_evaluation(
    golden_path: str = "data/golden_dataset.yaml",
    answer_func=None,  # (query: str) -> str
) -> dict:
    """对 Golden Dataset 逐条运行评估

    Args:
        golden_path: Golden Dataset 文件路径
        answer_func: 接受 query 返回 answer 的函数

    Returns:
        {"results": [...], "avg_scores": {...}}
    """
    items = load_golden_dataset(golden_path)
    judge_model = create_chat_model("cheap")  # 用廉价模型做评估

    results = []
    scores = {"faithfulness": [], "completeness": [], "authority": [], "balance": [], "honesty": [], "overall": []}

    for item in items:
        query = item["query"]
        answer = answer_func(query) if answer_func else "(no answer function provided)"

        judgement = judge_answer(query, answer, judge_model)
        item_result = {
            "id": item["id"],
            "query": query,
            "expected_sources": item.get("expected_sources", []),
            "judgement": judgement,
        }
        results.append(item_result)

        for key in scores:
            if key in judgement:
                scores[key].append(judgement[key])

    avg_scores = {k: round(sum(v) / len(v), 2) if v else 0 for k, v in scores.items()}

    return {"results": results, "avg_scores": avg_scores}


if __name__ == "__main__":
    # 独立运行时：仅加载 Golden Dataset 并做基本验证
    load_config()
    items = load_golden_dataset()
    print(f"Loaded {len(items)} items from Golden Dataset")
    for item in items:
        print(f"  [{item['id']}] {item['query'][:50]}...")
    print("\nGolden Dataset OK — run via conflux.eval.run_evaluation() with an answer_func")
