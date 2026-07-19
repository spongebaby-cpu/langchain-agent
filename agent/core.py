"""Agent 核心 — 创建和运行 ReAct Agent"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from agent.tools import get_all_tools
from agent.prompts import SYSTEM_PROMPT


def create_agent(config: dict):
    """创建 Agent 实例。

    Args:
        config: 配置字典，需包含 DEEPSEEK_API_KEY

    Returns:
        (agent, tools) 元组 — agent 是编译好的 LangGraph 图，tools 是工具列表
    """
    llm = ChatOpenAI(
        model=config["DEEPSEEK_MODEL"],
        api_key=config["DEEPSEEK_API_KEY"],
        base_url=config["DEEPSEEK_BASE_URL"],
        temperature=0.3,
        max_tokens=4096,
    )

    tools = get_all_tools()

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )

    return agent, tools


def run_agent(agent, user_input: str, stream: bool = False):
    """运行 Agent，处理用户输入。

    Args:
        agent: 编译好的 LangGraph agent
        user_input: 用户输入文本
        stream: 是否流式输出

    Yields:
        dict: 流式模式下每次更新的状态片段
        或在非流式模式下，直接返回最终结果
    """
    messages = agent.invoke(
        {"messages": [HumanMessage(content=user_input)]}
    )
    return messages
