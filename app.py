#!/usr/bin/env python3
"""AI Assistant with RAG - Web Interface"""

import json, sys, os, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

# ---- Proxy ----
_proxy = os.environ.get("HTTP_PROXY", "http://127.0.0.1:7890")
os.environ["http_proxy"] = os.environ["https_proxy"] = _proxy
os.environ["HTTP_PROXY"] = os.environ["HTTPS_PROXY"] = _proxy

# ---- Load Agent ----
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.config import get_config
from agent.core import create_agent
from agent.rag_tool import rag_add_document, get_rag_status

HOST = "0.0.0.0"
PORT = 7860

print("Loading Agent...")
config = get_config()
agent, tools = create_agent(config)
tool_names = [t.name for t in tools]
print(f"Agent ready | Model: {config['DEEPSEEK_MODEL']} | Tools: {', '.join(tool_names)}")

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Assistant with RAG</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#1a1a2e;color:#eee;height:100vh;display:flex;flex-direction:column}
.header{background:#16213e;padding:12px 24px;text-align:center;border-bottom:1px solid #0f3460}
.header h1{font-size:20px;color:#e94560}
.header p{font-size:11px;color:#888;margin-top:2px}
.chat{flex:1;overflow-y:auto;padding:16px 24px;display:flex;flex-direction:column;gap:14px}
.msg{max-width:82%;padding:10px 14px;border-radius:12px;line-height:1.5;white-space:pre-wrap;word-break:break-word;font-size:13px}
.msg.user{align-self:flex-end;background:#e94560;color:#fff}
.msg.assistant{align-self:flex-start;background:#0f3460;color:#eee}
.msg .label{font-size:10px;opacity:0.6;margin-bottom:3px}
.tools{display:flex;gap:5px;flex-wrap:wrap;padding:6px 24px}
.tool-tag{font-size:10px;padding:2px 8px;border-radius:8px;background:#0f3460;color:#a0c4ff}
.rag-bar{display:flex;gap:8px;padding:8px 24px;background:#0d1b36;align-items:center;border-top:1px solid #0f3460}
.rag-bar input{flex:1;padding:6px 10px;border-radius:6px;border:1px solid #0f3460;background:#1a1a2e;color:#eee;font-size:12px}
.rag-bar button{padding:6px 14px;border:none;border-radius:6px;background:#2563eb;color:#fff;font-size:12px;cursor:pointer;white-space:nowrap}
.rag-bar button:hover{opacity:0.85}
.rag-status{font-size:10px;color:#888;padding:0 24px 4px}
.input-area{display:flex;gap:10px;padding:12px 24px;border-top:1px solid #0f3460;background:#16213e}
.input-area textarea{flex:1;padding:10px;border-radius:8px;border:1px solid #0f3460;background:#1a1a2e;color:#eee;font-size:13px;resize:none;height:44px;font-family:inherit}
.input-area button{padding:10px 20px;border:none;border-radius:8px;background:#e94560;color:#fff;font-size:13px;cursor:pointer;font-weight:bold}
.input-area button:hover{background:#ff6b81}
.input-area button:disabled{opacity:0.5;cursor:not-allowed}
.thinking{color:#e94560;font-size:12px;padding:6px 0}
.tool-call{font-size:11px;color:#a0c4ff;padding:3px 10px;margin:3px 0;border-left:2px solid #e94560}
@media(max-width:600px){.msg{max-width:90%}.input-area{flex-direction:column}}
</style>
</head>
<body>
<div class="header">
  <h1>AI Assistant with RAG</h1>
  <p>Chat | Calculator | File I/O | Search | RAG Knowledge Base</p>
</div>
<div class="tools" id="tools"></div>
<div class="rag-status" id="ragStatus">RAG: loading...</div>
<div class="rag-bar">
  <input id="filepath" placeholder="Document path to add to knowledge base (e.g. C:\docs\manual.txt)">
  <button onclick="uploadDoc()">+ Add to KB</button>
</div>
<div class="chat" id="chat">
  <div class="msg assistant">
    <div class="label">Assistant</div>
    Hello! I can search documents you upload to the knowledge base. Try adding a file then ask me about its contents.
  </div>
</div>
<div class="input-area">
  <textarea id="input" placeholder="Ask anything... (Enter to send)" rows="1"></textarea>
  <button id="sendBtn" onclick="send()">Send</button>
</div>
<script>
var tools = TOOL_LIST;
document.getElementById('tools').innerHTML = tools.map(function(t){return '<span class="tool-tag">'+t+'</span>'}).join('');
loadRagStatus();

var chat = document.getElementById('chat');
var input = document.getElementById('input');
var sendBtn = document.getElementById('sendBtn');
input.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});

async function send() {
  var text = input.value.trim();
  if (!text) return;
  appendMsg('user', 'You', text);
  input.value = '';
  sendBtn.disabled = true;
  var thinkDiv = appendMsg('assistant', 'Assistant', 'Thinking...');
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
      appendMsg('assistant', 'Assistant', 'Error: ' + data.error);
    } else {
      if (data.tool_calls && data.tool_calls.length > 0) {
        data.tool_calls.forEach(function(tc) {
          var tcDiv = document.createElement('div');
          tcDiv.className = 'tool-call';
          tcDiv.textContent = '>> Tool: ' + tc;
          chat.appendChild(tcDiv);
        });
      }
      appendMsg('assistant', 'Assistant', data.reply || '(no response)');
    }
  } catch (e) {
    thinkDiv.remove();
    appendMsg('assistant', 'Assistant', 'Network error: ' + e.message);
  }
  sendBtn.disabled = false;
  chat.scrollTop = chat.scrollHeight;
}

async function uploadDoc() {
  var fp = document.getElementById('filepath').value.trim();
  if (!fp) return;
  var resp = await fetch('/api/upload', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({filepath: fp})
  });
  var data = await resp.json();
  appendMsg('assistant', 'System', data.result || data.error);
  loadRagStatus();
  document.getElementById('filepath').value = '';
}

async function loadRagStatus() {
  try {
    var resp = await fetch('/api/rag_status');
    var data = await resp.json();
    document.getElementById('ragStatus').textContent = data.status || 'RAG: -';
  } catch(e) {}
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
            data = json.loads(self.rfile.read(length))
            user_msg = data.get("message", "").strip()
            if not user_msg:
                self._json({"error": "empty message"})
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
                self._json({"reply": reply or "done", "tool_calls": tool_calls})
            except Exception as e:
                self._json({"error": str(e)})

        elif self.path == "/api/upload":
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            filepath = data.get("filepath", "").strip()
            if filepath:
                result = rag_add_document.invoke({"filepath": filepath})
                self._json({"result": result, "rag_status": get_rag_status()})
            else:
                self._json({"error": "no filepath"})

        elif self.path == "/api/rag_status":
            self._json({"status": get_rag_status()})

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
        pass


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
