"""Agent 核心 — ReAct 循环的 Think → Act → Observe

包含 System Prompt、Agent Node、路由函数。
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from .config import get
from .prompts import load_system_prompt

# ── System Prompt ──────────────────────────────────────────

SYSTEM_PROMPT = """你是一个严谨的调研 Agent，名为 Conflux。你的任务是基于多种信息源回答用户的问题。

## 可用工具

你可以使用以下工具来获取信息：

1. **search_rag(query)** — 在本地知识库中搜索。使用它查找已存储的文档、报告、分析等。
2. **search_web(query)** — 在互联网上搜索最新信息。使用它查找实时新闻、最新研究、公共信息等。
3. **ask_model(query)** — 使用模型自身的世界知识回答。适用于常识推理、概念解释、理论分析等。
   注意：如果 search_web 不可用，可以用 ask_model 作为补充。

## 工作流程

遵循 ReAct 模式：思考 → 行动 → 观察 → 思考 → ...

1. **先检索，再回答**：在给出任何结论之前，至少使用一个工具检索相关信息。
2. **交叉验证**：如果时间允许，用两个工具搜索同一主题以交叉验证。
3. **诚实标注**：
   - 如果信息来自检索结果，标注来源。
   - 如果信息来自你自身的知识，明确标注为「基于模型知识」。
   - 如果信息不确定或存在争议，明确标注不确定性。
4. **引用格式**：每次使用检索结果时，注明是从哪个工具获得的。

## 回答结构

当你准备好给出最终回答时，按以下结构组织：

```final
## 回答
[你的回答]

## 信息来源
- [来源1]
- [来源2]

## 不确定性说明
[如有不确定或争议，在此说明]

## 置信度评估
整体置信度：[高/中/低] — [简要原因]
```
"""

FINAL_MARKER = "```final"


# ── Agent Node ─────────────────────────────────────────────

# 子 Agent 专用 System Prompt 模板
SUB_AGENT_PROMPTS = {
    "rag": """你是一个本地知识库检索专家。你的唯一工具是 search_rag(query)。
请用 search_rag 检索相关信息，然后基于检索结果回答问题。
回答中必须引用具体文档来源。""",

    "web": """你是一个互联网信息检索专家。你的唯一工具是 search_web(query)。
请用 search_web 搜索最新信息，然后基于搜索结果回答问题。
回答中必须引用具体 URL 来源。如果搜索失败，明确告知并建议用其他信息源。""",

    "model": """你是一个基于模型世界知识回答问题的专家。你的唯一工具是 ask_model(query)。
请用 ask_model 获取模型知识，然后组织回答。
回答中必须明确标注「基于模型世界知识」。""",
}

SUB_AGENT_PROMPT_FILES = {
    "rag": "agents/rag_agent.system.yaml",
    "web": "agents/web_agent.system.yaml",
    "model": "agents/model_agent.system.yaml",
}


class ResearchAgent:
    """ReAct Agent：管理 LLM + 工具之间的交互循环"""

    def __init__(self, model: BaseChatModel, tools: list[BaseTool], system_prompt: str | None = None):
        self.raw_model = model                       # 无工具绑定，用于合成
        self.model = model.bind_tools(tools)          # 带工具绑定，用于 ReAct
        self.tools_by_name = {t.name: t for t in tools}
        self.max_iterations = get("agent", "max_iterations", default=3)
        self.system_prompt = system_prompt or SYSTEM_PROMPT

    def build_messages(self, query: str, history: list | None = None) -> list:
        """构建初始消息列表"""
        msgs = [SystemMessage(content=self.system_prompt)]
        if history:
            msgs.extend(history)
        msgs.append(HumanMessage(content=query))
        return msgs

    def call_model(self, messages: list, use_tools: bool = True) -> AIMessage:
        """调用 LLM，返回 AIMessage

        Args:
            messages: 消息列表
            use_tools: True 用带工具绑定的模型，False 用纯文本模型
        """
        m = self.model if use_tools else self.raw_model
        return m.invoke(messages)

    def execute_tools(self, ai_message: AIMessage) -> list[ToolMessage]:
        """执行 AIMessage 中的所有 tool_calls，返回 ToolMessage 列表"""
        tool_messages = []
        for tc in ai_message.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc["id"]

            tool = self.tools_by_name.get(tool_name)
            if tool is None:
                result = f"错误：未找到工具 {tool_name}"
            else:
                try:
                    result = tool.invoke(tool_args)
                except Exception as e:
                    result = f"工具执行错误：{e}"

            tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))
        return tool_messages

    def has_final_answer(self, ai_message: AIMessage) -> bool:
        """判断 LLM 是否给出了最终答案"""
        content = ai_message.content
        if isinstance(content, str) and FINAL_MARKER in content:
            return True
        # 如果 LLM 没有 tool_calls 且内容非空，也视为最终回答
        if not ai_message.tool_calls and content and isinstance(content, str) and len(content) > 50:
            return True
        return False

    def should_continue(self, messages: list, iteration: int) -> bool:
        """判断是否应该继续循环"""
        if iteration >= self.max_iterations:
            return False
        # 看最后一条 AI 消息
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                return not self.has_final_answer(msg)
        return True


def create_sub_agent(
    name: str,
    model: BaseChatModel,
    tool: BaseTool,
) -> ResearchAgent:
    """工厂函数：创建单工具子 Agent

    Args:
        name: "rag" | "web" | "model"
        model: LLM 实例
        tool: 该 Agent 的专属工具
    """
    default_prompt = SUB_AGENT_PROMPTS.get(name, SYSTEM_PROMPT)
    prompt_file = SUB_AGENT_PROMPT_FILES.get(name)
    prompt = load_system_prompt(prompt_file, default_prompt) if prompt_file else default_prompt
    return ResearchAgent(model, [tool], system_prompt=prompt)
