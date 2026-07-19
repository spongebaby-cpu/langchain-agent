#!/usr/bin/env python3
"""启动脚本 — 设置代理后启动 Web 服务器"""
import os, sys

# 设置代理（Clash Verge 默认端口）
proxy = os.environ.get("HTTP_PROXY", "http://127.0.0.1:7890")
os.environ["http_proxy"] = os.environ["https_proxy"] = proxy
os.environ["HTTP_PROXY"] = os.environ["HTTPS_PROXY"] = proxy
print(f"Proxy: {proxy}")

# 启动 app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py"), encoding="utf-8").read())
