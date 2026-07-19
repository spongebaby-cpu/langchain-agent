#!/usr/bin/env python3
"""LangChain Agent — 交互式命令行入口"""

import sys
import argparse
from utils.config import get_config
from agent.core import create_agent, run_agent
from agent.tools import get_all_tools


def print_banner(config: dict):
    """打印启动信息"""
    tools = get_all_tools()
    tool_names = [t.name for t in tools]
    print(f"""
╔══════════════════════════════════════════╗
║       LangChain Agent (Claude)          ║
╠══════════════════════════════════════════╣
║  模型: {config['ANTHROPIC_MODEL']:<31s} ║
║  工具: {', '.join(tool_names):<31s} ║
╠══════════════════════════════════════════╣
║  输入问题开始对话，输入 exit 退出      ║
╚══════════════════════════════════════════╝
""")


def main():
    parser = argparse.ArgumentParser(description="LangChain Agent 智能体")
    parser.add_argument("--stream", action="store_true", help="流式输出")
    parser.add_argument("--query", "-q", type=str, help="单次查询（非交互模式）")
    args = parser.parse_args()

    # 加载配置
    try:
        config = get_config()
    except ValueError as e:
        print(f"❌ 配置错误：{e}")
        print("请复制 .env.example 为 .env 并填入你的 API Key")
        sys.exit(1)

    # 创建 Agent
    print("⏳ 正在初始化 Agent...")
    agent, tools = create_agent(config)
    print("✅ Agent 就绪")

    # 单次查询模式
    if args.query:
        print(f"\n🔍 查询: {args.query}\n")
        result = run_agent(agent, args.query, stream=args.stream)
        # 提取最后一条 AI 消息
        for msg in reversed(result["messages"]):
            if hasattr(msg, "content") and msg.type == "ai" and msg.content:
                print(msg.content)
                break
        return

    # 交互模式
    print_banner(config)

    while True:
        try:
            user_input = input("\n👤 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "退出"):
            print("👋 再见！")
            break

        print("\n🤖 Agent 思考中...\n")
        try:
            result = run_agent(agent, user_input, stream=args.stream)
            # 提取最后一条 AI 消息的内容
            for msg in reversed(result["messages"]):
                if hasattr(msg, "content") and msg.type == "ai" and msg.content:
                    print(f"🤖 {msg.content}")
                    break
            else:
                # 如果没找到 AI 消息，打印最后的工具调用信息
                print("🤖 Agent 已执行完成，请查看上方的工具调用日志。")
        except Exception as e:
            print(f"❌ 出错：{e}")


if __name__ == "__main__":
    main()
