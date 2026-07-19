# AI Assistant - LangChain Agent

基于 LangChain + LangGraph 的智能 Agent 应用，支持 DeepSeek（云端）和 Ollama（本地）双模式。

## 技术栈

- **框架**: LangChain + LangGraph (ReAct Agent)
- **大模型**: DeepSeek V3 / 本地 Ollama
- **后端**: Python HTTP Server
- **前端**: 原生 HTML/CSS/JS（暗色主题 + 响应式）

## 功能

- 多工具 Agent（计算器、时间查询、文件读写、联网搜索）
- Web 对话界面，多轮对话
- 云端/本地模型一键切换
- 零额外依赖，纯 Python 标准库即可运行

## 快速开始

```bash
pip install -r requirements.txt
py app.py
# 浏览器打开 http://localhost:7860
```

## 配置 .env

```env
LLM_MODE=cloud
DEEPSEEK_API_KEY=sk-your-key
DEEPSEEK_MODEL=deepseek-chat
```

## 项目结构

```
├── app.py          # Web 界面入口
├── main.py         # 命令行入口
├── agent/
│   ├── core.py     # Agent 核心（ReAct）
│   ├── tools.py    # 工具定义
│   └── prompts.py  # System Prompt
└── utils/
    └── config.py   # 配置管理
```
