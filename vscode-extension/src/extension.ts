import * as vscode from 'vscode';
import fetch from 'node-fetch';

const ARCHIMEDES_URL = () =>
  vscode.workspace.getConfiguration('archimedes').get<string>('serverUrl')
  || 'http://localhost:8001';

let chatPanel: vscode.WebviewPanel | undefined;

export function activate(context: vscode.ExtensionContext) {

  // Command: Open Chat Panel
  context.subscriptions.push(
    vscode.commands.registerCommand('archimedes.openChat', () => {
      if (chatPanel) {
        chatPanel.reveal();
        return;
      }
      chatPanel = vscode.window.createWebviewPanel(
        'archimedesChat',
        'Archimedes AI',
        vscode.ViewColumn.Beside,
        { enableScripts: true, retainContextWhenHidden: true }
      );
      chatPanel.webview.html = getChatHTML(ARCHIMEDES_URL());
      chatPanel.onDidDispose(() => { chatPanel = undefined; });
    })
  );

  // Command: Fix selected code
  context.subscriptions.push(
    vscode.commands.registerCommand('archimedes.fixSelection', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;

      const selection = editor.selection;
      const selectedText = editor.document.getText(selection);
      const language = editor.document.languageId;
      const filename = editor.document.fileName;

      if (!selectedText) {
        vscode.window.showWarningMessage('Select code to fix');
        return;
      }

      const task = (
        `Fix this ${language} code from ${filename}:\n\n` +
        `\`\`\`${language}\n${selectedText}\n\`\`\`\n\n` +
        `Return ONLY the fixed code, no explanation.`
      );

      const result = await sendToArchimedes(task);
      if (result) {
        const codeMatch = result.match(
          /```(?:\w+)?\n([\s\S]+?)\n```/
        );
        const fixedCode = codeMatch ? codeMatch[1] : result;

        editor.edit(editBuilder => {
          editBuilder.replace(selection, fixedCode);
        });
        vscode.window.showInformationMessage('Archimedes fixed the code');
      }
    })
  );

  // Command: Explain selected code
  context.subscriptions.push(
    vscode.commands.registerCommand('archimedes.explainSelection', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;

      const selectedText = editor.document.getText(editor.selection);
      if (!selectedText) return;

      const task = `Explain this code briefly (3-5 sentences):\n\n${selectedText}`;
      const result = await sendToArchimedes(task);

      if (result) {
        vscode.window.showInformationMessage(result.slice(0, 300));
      }
    })
  );

  // Command: Run custom task
  context.subscriptions.push(
    vscode.commands.registerCommand('archimedes.runTask', async () => {
      const task = await vscode.window.showInputBox({
        prompt: 'Enter a task for Archimedes AI',
        placeHolder: 'e.g. Write a quicksort function in Python'
      });
      if (!task) return;

      // Reveal or create chat panel
      if (chatPanel) {
        chatPanel.reveal();
      } else {
        chatPanel = vscode.window.createWebviewPanel(
          'archimedesChat',
          'Archimedes AI',
          vscode.ViewColumn.Beside,
          { enableScripts: true, retainContextWhenHidden: true }
        );
        chatPanel.webview.html = getChatHTML(ARCHIMEDES_URL());
        chatPanel.onDidDispose(() => { chatPanel = undefined; });
      }

      // Prepopulate and trigger task run in the chat panel
      setTimeout(() => {
        if (chatPanel) {
          chatPanel.webview.postMessage({ command: 'sendTask', task: task });
        }
      }, 400);
    })
  );

  // Status bar item
  const statusBar = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right, 100
  );
  statusBar.text = 'Archimedes';
  statusBar.command = 'archimedes.openChat';
  statusBar.tooltip = 'Open Archimedes AI Chat';
  statusBar.show();
  context.subscriptions.push(statusBar);

  checkServer(ARCHIMEDES_URL(), statusBar);
}

async function sendToArchimedes(task: string): Promise<string | null> {
  try {
    const resp = await fetch(`${ARCHIMEDES_URL()}/api/v1/quick-task`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task, stream: false }),
    });
    if (!resp.ok) return null;
    const data = await resp.json() as { result?: string };
    return data.result || null;
  } catch (e) {
    vscode.window.showErrorMessage(
      `Archimedes not reachable at ${ARCHIMEDES_URL()}`
    );
    return null;
  }
}

async function checkServer(url: string, bar: vscode.StatusBarItem) {
  try {
    const r = await fetch(`${url}/health`);
    if (r.ok) {
      bar.text = 'Archimedes OK';
      bar.backgroundColor = undefined;
    } else {
      bar.text = 'Archimedes OFF';
    }
  } catch {
    bar.text = 'Archimedes OFF';
  }
}

function getChatHTML(serverUrl: string): string {
  const wsUrl = serverUrl.replace('http', 'ws') + '/ws';
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src ${wsUrl.startsWith('ws://') ? 'ws:' : 'wss:'} ${serverUrl};">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #07070d; color: #f1f0ff;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    display: flex; flex-direction: column; height: 100vh;
    padding: 0; overflow: hidden;
  }
  #header {
    padding: 14px 20px;
    background: rgba(7, 7, 13, 0.6);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    font-size: 13px; font-weight: 600; color: #9b8fff;
    display: flex; align-items: center; justify-content: space-between;
  }
  #status-indicator {
    display: flex; align-items: center; gap: 6px;
    font-size: 11px; color: #5a5a7a; font-weight: 500;
  }
  #status-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #5a5a7a;
    box-shadow: 0 0 8px #5a5a7a;
    transition: all 0.3s ease;
  }
  #status-dot.connected {
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
  }
  #status-dot.disconnected {
    background: #ef4444;
    box-shadow: 0 0 8px #ef4444;
  }
  #messages {
    flex: 1; overflow-y: auto; padding: 20px;
    display: flex; flex-direction: column; gap: 14px;
    scroll-behavior: smooth;
  }
  .msg {
    padding: 10px 14px; border-radius: 12px;
    font-size: 13px; line-height: 1.6; max-width: 85%;
    word-wrap: break-word;
  }
  .msg.user {
    background: #15152a; border: 1px solid rgba(107, 95, 255, 0.25);
    align-self: flex-end; color: #f1f0ff;
    box-shadow: 0 4px 12px rgba(107, 95, 255, 0.05);
  }
  .msg.assistant {
    background: #0b0b14; border: 1px solid rgba(255, 255, 255, 0.04);
    align-self: flex-start; color: #d0d0e0;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  }
  .msg.thought {
    background: transparent;
    border-left: 2px solid #5a4eff;
    padding: 6px 12px; font-size: 11.5px;
    color: #6a6a8a; align-self: flex-start;
    font-style: italic; max-width: 90%;
  }
  .msg p { margin-bottom: 8px; }
  .msg p:last-child { margin-bottom: 0; }
  
  /* Markdown Styles */
  .code-block {
    background: #05050a;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    margin: 10px 0;
    overflow: hidden;
  }
  .code-header {
    background: rgba(255, 255, 255, 0.02);
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    padding: 6px 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    font-family: monospace;
    color: #8a8a9a;
  }
  .copy-btn {
    background: rgba(107, 95, 255, 0.15);
    border: 1px solid rgba(107, 95, 255, 0.3);
    border-radius: 4px;
    color: #9b8fff;
    padding: 2px 8px;
    font-size: 10px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .copy-btn:hover {
    background: #5a4eff;
    color: white;
  }
  pre {
    padding: 12px;
    margin: 0;
    overflow-x: auto;
  }
  code {
    font-family: Consolas, Monaco, monospace;
    font-size: 12px;
  }
  .inline-code {
    background: rgba(107, 95, 255, 0.1);
    color: #b8aeff;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: Consolas, Monaco, monospace;
    font-size: 11.5px;
  }
  ul {
    padding-left: 20px;
    margin-bottom: 8px;
  }
  li {
    margin-bottom: 4px;
  }
  
  #input-area {
    padding: 16px; border-top: 1px solid rgba(255, 255, 255, 0.05);
    display: flex; gap: 10px; background: #07070d;
  }
  #input {
    flex: 1; background: #0b0b14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px; color: white;
    padding: 10px 14px; font-size: 13px;
    outline: none; resize: none;
    font-family: inherit;
    transition: border-color 0.2s;
  }
  #input:focus {
    border-color: rgba(107, 95, 255, 0.5);
  }
  #send {
    background: #5a4eff; color: white; border: none;
    border-radius: 10px; padding: 0 20px;
    cursor: pointer; font-size: 13px; font-weight: 600;
    transition: background 0.2s, transform 0.1s;
  }
  #send:hover { background: #7c6fff; }
  #send:active { transform: scale(0.97); }
</style>
</head>
<body>
<div id="header">
  <span>Archimedes AI</span>
  <div id="status-indicator">
    <div id="status-dot"></div>
    <span id="status-text">connecting...</span>
  </div>
</div>
<div id="messages"></div>
<div id="input-area">
  <textarea id="input" rows="2" placeholder="Ask Archimedes anything..."></textarea>
  <button id="send">Send</button>
</div>
<script>
  const msgs = document.getElementById('messages');
  const input = document.getElementById('input');
  const sendBtn = document.getElementById('send');
  const statusDot = document.getElementById('status-dot');
  const statusText = document.getElementById('status-text');
  const SESSION_ID = 'vscode-' + Math.random().toString(36).slice(2);

  let currentAssistantText = "";

  // Highly robust custom offline markdown parser using compile-safe RegExp and string concatenation
  function renderMarkdown(text) {
    let html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    const placeholders = [];
    
    // 1. Extract code blocks using hex code \\u0060 instead of backticks to prevent TS template closing issues
    const codeBlockRegex = new RegExp('\\\\u0060\\\\u0060\\\\u0060(\\\\w*)\\\\n([\\\\s\\\\S]*?)\\\\u0060\\\\u0060\\\\u0060', 'g');
    html = html.replace(codeBlockRegex, (match, lang, code) => {
      const id = 'code-' + Math.random().toString(36).slice(2);
      const placeholder = '__CODE_BLOCK_PLACEHOLDER_' + placeholders.length + '__';
      placeholders.push('<div class="code-block">' +
        '<div class="code-header">' +
          '<span>' + (lang || 'code') + '</span>' +
          '<button class="copy-btn" onclick="copyCode(\\'' + id + '\\', this)">Copy</button>' +
        '</div>' +
        '<pre><code id="' + id + '">' + code + '</code></pre>' +
      '</div>');
      return placeholder;
    });

    // 2. Inline code using hex code \\u0060 for RegExp string literal compilation
    const inlineCodeRegex = new RegExp('\\\\u0060([^\\\\u0060\\\\n]+)\\\\u0060', 'g');
    html = html.replace(inlineCodeRegex, '<code class="inline-code">$1</code>');

    // 3. Bold using double escaped RegExp string
    const boldRegex = new RegExp('\\\\*\\\\*([^*]+)\\\\*\\\\*', 'g');
    html = html.replace(boldRegex, '<strong>$1</strong>');

    // 4. Line-by-line list and paragraph parser
    const lines = html.split('\\n');
    let inList = false;
    let processed = [];
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();
      if (trimmed.indexOf('- ') === 0) {
        if (!inList) {
          processed.push('<ul>');
          inList = true;
        }
        processed.push('<li>' + trimmed.substring(2) + '</li>');
      } else {
        if (inList) {
          processed.push('</ul>');
          inList = false;
        }
        if (trimmed && trimmed.indexOf('__CODE_BLOCK_') !== 0) {
          processed.push('<p>' + line + '</p>');
        } else {
          processed.push(line);
        }
      }
    }
    if (inList) {
      processed.push('</ul>');
    }
    html = processed.join('\\n');

    // 5. Restore code blocks
    for (let i = 0; i < placeholders.length; i++) {
      html = html.replace('__CODE_BLOCK_PLACEHOLDER_' + i + '__', placeholders[i]);
    }

    return html;
  }

  // Copy code helper
  window.copyCode = function(id, btn) {
    const code = document.getElementById(id).innerText;
    navigator.clipboard.writeText(code).then(() => {
      btn.textContent = 'Copied!';
      setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
    });
  };

  let ws;
  function connect() {
    ws = new WebSocket('${wsUrl}/' + SESSION_ID);
    ws.onopen = () => {
      statusText.textContent = 'connected';
      statusDot.className = 'connected';
    };
    ws.onclose = () => {
      statusText.textContent = 'disconnected';
      statusDot.className = 'disconnected';
      setTimeout(connect, 3000);
    };
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'thought') {
        addMessage('thought', data.content);
      } else if (data.type === 'token') {
        appendToLast(data.text);
      } else if (data.type === 'result' || data.type === 'message') {
        currentAssistantText = ""; // Reset stream text
        addMessage('assistant', data.content || data.text || '');
      }
    };
  }

  function addMessage(role, text) {
    const div = document.createElement('div');
    div.className = 'msg ' + role;
    if (role === 'assistant') {
      currentAssistantText = text;
      div.innerHTML = renderMarkdown(text);
    } else if (role === 'thought') {
      div.textContent = text;
    } else {
      div.textContent = text;
    }
    div.dataset.id = Date.now();
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  function appendToLast(text) {
    const last = msgs.querySelector('.msg.assistant:last-child');
    if (last) {
      currentAssistantText += text;
      last.innerHTML = renderMarkdown(currentAssistantText);
    } else {
      currentAssistantText = text;
      addMessage('assistant', text);
    }
    msgs.scrollTop = msgs.scrollHeight;
  }

  sendBtn.onclick = () => {
    const text = input.value.trim();
    if (!text || !ws || ws.readyState !== 1) return;
    addMessage('user', text);
    ws.send(JSON.stringify({ type: 'message', content: text }));
    input.value = '';
  };

  input.onkeydown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendBtn.click();
    }
  };

  // Handle messages passed from VS Code extension host (like prepopulated task)
  window.addEventListener('message', event => {
    const message = event.data;
    if (message.command === 'sendTask') {
      const text = message.task;
      if (!text) return;
      
      function trySend() {
        if (ws && ws.readyState === 1) {
          addMessage('user', text);
          ws.send(JSON.stringify({ type: 'message', content: text }));
        } else {
          setTimeout(trySend, 100);
        }
      }
      trySend();
    }
  });

  connect();
</script>
</body>
</html>`;
}

export function deactivate() {}
