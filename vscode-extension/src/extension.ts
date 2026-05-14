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
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0a0a12; color: #f1f0ff;
    font-family: 'Geist', system-ui, sans-serif;
    display: flex; flex-direction: column; height: 100vh;
  }
  #header {
    padding: 12px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    font-size: 13px; font-weight: 600; color: #9b8fff;
    display: flex; align-items: center; gap: 8px;
  }
  #messages {
    flex: 1; overflow-y: auto; padding: 16px;
    display: flex; flex-direction: column; gap: 8px;
  }
  .msg {
    padding: 8px 12px; border-radius: 8px;
    font-size: 13px; line-height: 1.5; max-width: 90%;
  }
  .msg.user {
    background: #1a1a2e; border: 1px solid rgba(107,95,255,0.3);
    align-self: flex-end;
  }
  .msg.assistant {
    background: #0d0d1a; border: 1px solid rgba(255,255,255,0.06);
    align-self: flex-start; color: #a0a0c0;
  }
  .msg.thought {
    background: transparent;
    border-left: 2px solid #6b5fff;
    padding: 4px 8px; font-size: 11px;
    color: #5a5a7a; align-self: flex-start;
  }
  #input-area {
    padding: 12px; border-top: 1px solid rgba(255,255,255,0.08);
    display: flex; gap: 8px;
  }
  #input {
    flex: 1; background: #0d0d1a;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; color: white;
    padding: 8px 12px; font-size: 13px;
    outline: none; resize: none;
    font-family: inherit;
  }
  #send {
    background: #6b5fff; color: white; border: none;
    border-radius: 8px; padding: 8px 14px;
    cursor: pointer; font-size: 13px; font-weight: 500;
  }
  #send:hover { background: #5a4eff; }
</style>
</head>
<body>
<div id="header">Archimedes AI <span id="status" style="font-size:10px;color:#5a5a7a">connecting...</span></div>
<div id="messages"></div>
<div id="input-area">
  <textarea id="input" rows="2" placeholder="Ask Archimedes anything..."></textarea>
  <button id="send">Send</button>
</div>
<script>
  const msgs = document.getElementById('messages');
  const input = document.getElementById('input');
  const sendBtn = document.getElementById('send');
  const status = document.getElementById('status');
  const SESSION_ID = 'vscode-' + Math.random().toString(36).slice(2);

  let ws;
  function connect() {
    ws = new WebSocket('${wsUrl}/' + SESSION_ID);
    ws.onopen = () => { status.textContent = 'connected'; };
    ws.onclose = () => {
      status.textContent = 'disconnected';
      setTimeout(connect, 3000);
    };
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'thought') {
        addMessage('thought', data.content);
      } else if (data.type === 'token') {
        appendToLast(data.text);
      } else if (data.type === 'result' || data.type === 'message') {
        addMessage('assistant', data.content || data.text || '');
      }
    };
  }

  function addMessage(role, text) {
    const div = document.createElement('div');
    div.className = 'msg ' + role;
    div.textContent = text;
    div.dataset.id = Date.now();
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  function appendToLast(text) {
    const last = msgs.querySelector('.msg.assistant:last-child');
    if (last) last.textContent += text;
    else addMessage('assistant', text);
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

  connect();
</script>
</body>
</html>`;
}

export function deactivate() {}
