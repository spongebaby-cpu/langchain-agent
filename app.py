#!/usr/bin/env python3
"""AI 智能助手 — Web 版（纯 Python 标准库，零额外依赖）"""

import json
import sys
import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

# ---- 代理（Clash Verge，解决 DeepSeek 连接问题）----
_proxy = os.environ.get("HTTP_PROXY", "http://127.0.0.1:7890")
os.environ["http_proxy"] = os.environ["https_proxy"] = _proxy
os.environ["HTTP_PROXY"] = os.environ["HTTPS_PROXY"] = _proxy

# ---- 加载 Agent ----
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.config import get_config
from agent.core import create_agent

HOST = "0.0.0.0"
PORT = 7860

print("Loading Agent...")
config = get_config()
agent, tools = create_agent(config)
tool_names = [t.name for t in tools]
print(f"Agent ready | Model: {config['DEEPSEEK_MODEL']} | Tools: {', '.join(tool_names)}")

# ---- HTML 页面 ----
HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🤖 AI 智能助手</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#1a1a2e;color:#eee;height:100vh;display:flex;flex-direction:column}
.header{background:#16213e;padding:16px 24px;text-align:center;border-bottom:1px solid #0f3460}
.header h1{font-size:22px;color:#e94560}
.header p{font-size:12px;color:#888;margin-top:4px}
.chat{flex:1;overflow-y:auto;padding:20px 24px;display:flex;flex-direction:column;gap:16px}
.msg{max-width:80%;padding:12px 16px;border-radius:12px;line-height:1.6;white-space:pre-wrap;word-break:break-word;font-size:14px}
.msg.user{align-self:flex-end;background:#e94560;color:#fff}
.msg.assistant{align-self:flex-start;background:#0f3460;color:#eee}
.msg .label{font-size:11px;opacity:0.6;margin-bottom:4px}
.tools{display:flex;gap:6px;flex-wrap:wrap;padding:8px 24px}
.tool-tag{font-size:11px;padding:3px 10px;border-radius:10px;background:#0f3460;color:#a0c4ff}
.input-area{display:flex;gap:10px;padding:16px 24px;border-top:1px solid #0f3460;background:#16213e}
.input-area textarea{flex:1;padding:12px;border-radius:8px;border:1px solid #0f3460;background:#1a1a2e;color:#eee;font-size:14px;resize:none;height:48px;font-family:inherit}
.input-area button{padding:12px 24px;border:none;border-radius:8px;background:#e94560;color:#fff;font-size:14px;cursor:pointer;font-weight:bold}
.input-area button:hover{background:#ff6b81}
.input-area button:disabled{opacity:0.5;cursor:not-allowed}
.thinking{color:#e94560;font-size:13px;padding:8px 0}
.tool-call{font-size:12px;color:#a0c4ff;padding:4px 12px;margin:4px 0;border-left:2px solid #e94560}
@media(max-width:600px){.msg{max-width:90%}.input-area{flex-direction:column}}
</style>
</head>
<body>

<div class="header">
  <h1>🤖 AI 智能助手</h1>
  <p>支持对话、计算、文件处理、联网搜索</p>
</div>

<div class="tools" id="tools"></div>

<div class="chat" id="chat">
  <div class="msg assistant">
    <div class="label">🤖 助手</div>
    你好！我是 AI 智能助手，有什么可以帮你的？
  </div>
</div>

<div class="input-area">
  <textarea id="input" placeholder="输入问题，按 Enter 发送（Shift+Enter 换行）..." rows="1"></textarea>
  <button id="sendBtn" onclick="send()">发送</button>
</div>

<script>
const tools = TOOL_LIST;
document.getElementById('tools').innerHTML = tools.map(t => '<span class="tool-tag">🔧 ' + t + '</span>').join('');

const chat = document.getElementById('chat');
const input = document.getElementById('input');
const sendBtn = document.getElementById('sendBtn');

input.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});

async function send() {
  var text = input.value.trim();
  if (!text) return;

  appendMsg('user', '👤 你', text);
  input.value = '';
  sendBtn.disabled = true;

  var thinkDiv = appendMsg('assistant', '🤖 助手', '思考中...');
  thinkDiv.classList.add('thinking');

  try {
    var resp = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    });
    var data = await resp.json();
    thinkDiv.remove();

    if (data.error) {
      appendMsg('assistant', '🤖 助手', '❌ ' + data.error);
    } else {
      if (data.tool_calls && data.tool_calls.length > 0) {
        data.tool_calls.forEach(function(tc) {
          var tcDiv = document.createElement('div');
          tcDiv.className = 'tool-call';
          tcDiv.textContent = '🔧 调用工具: ' + tc;
          chat.appendChild(tcDiv);
        });
      }
      appendMsg('assistant', '🤖 助手', data.reply || '(无回复)');
    }
  } catch (e) {
    thinkDiv.remove();
    appendMsg('assistant', '🤖 助手', '❌ 网络错误: ' + e.message);
  }

  sendBtn.disabled = false;
  chat.scrollTop = chat.scrollHeight;
}

function appendMsg(role, label, content) {
  var div = document.createElement('div');
  div.className = 'msg ' + role;
  div.innerHTML = '<div class="label">' + label + '</div>' + escapeHtml(content);
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function escapeHtml(text) {
  var div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
</script>
</body>
</html>
""".replace("TOOL_LIST", json.dumps(tool_names))


class Handler(BaseHTTPRequestHandler):
    """HTTP 请求处理"""

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            content = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/chat":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            user_msg = data.get("message", "").strip()

            if not user_msg:
                self._json({"error": "消息为空"})
                return

            try:
                from langchain_core.messages import HumanMessage
                result = agent.invoke({"messages": [HumanMessage(content=user_msg)]})

                reply = ""
                tool_calls = []
                for msg in result.get("messages", []):
                    if hasattr(msg, "type"):
                        if msg.type == "ai" and hasattr(msg, "content") and msg.content:
                            reply = msg.content
                        if msg.type == "tool":
                            tool_calls.append(getattr(msg, "name", "unknown"))

                self._json({"reply": reply or "处理完成", "tool_calls": tool_calls})

            except Exception as e:
                self._json({"error": str(e)})
        else:
            self.send_error(404)

    def _json(self, data):
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(content))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        pass  # 精简日志


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"\n{'='*50}")
    print(f"  Browser: {url}")
    print(f"  LAN: http://<your-ip>:{PORT}")
    print(f"  Ctrl+C to stop")
    print(f"{'='*50}\n")

    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        server.shutdown()
