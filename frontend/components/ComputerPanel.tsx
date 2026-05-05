"use client";

import { useEffect, useState, useRef } from "react";
import { Terminal, Code2, Monitor, ChevronLeft, ChevronRight, PlaySquare, X, RefreshCw, FolderOpen } from "lucide-react";
import Editor from "@monaco-editor/react";
import { AgentEvent } from "@/lib/websocket";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface FileTab {
  path: string;
  name: string;
  content: string;
  language: string;
}

interface ComputerPanelProps {
  sessionId: string;
  onClose: () => void;
}

export default function ComputerPanel({ sessionId, onClose }: ComputerPanelProps) {
  const [activeTab, setActiveTab] = useState<"terminal" | "editor" | "browser">("editor");
  const [terminalLogs, setTerminalLogs] = useState<string[]>([]);
  const [fileTabs, setFileTabs] = useState<FileTab[]>([]);
  const [activeFileIdx, setActiveFileIdx] = useState(0);
  const [vncUrl, setVncUrl] = useState<string>("");
  const [desktopFrame, setDesktopFrame] = useState<string>("");
  const [browserLoading, setBrowserLoading] = useState(false);
  const [browserError, setBrowserError] = useState<string | null>(null);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Load file content via API
  const loadFile = async (filePath: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/workspace/file?path=${encodeURIComponent(filePath)}`);
      if (!res.ok) return null;
      const data = await res.json();
      return {
        path: data.path || filePath,
        name: data.filename || filePath.split("/").pop() || "file",
        content: data.content || "",
        language: data.language || "plaintext",
      } as FileTab;
    } catch {
      return null;
    }
  };

  // Add or update a file tab
  const upsertFileTab = (tab: FileTab) => {
    setFileTabs(prev => {
      const idx = prev.findIndex(t => t.path === tab.path || t.name === tab.name);
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = tab;
        setActiveFileIdx(idx);
        return updated;
      } else {
        setActiveFileIdx(prev.length);
        return [...prev, tab];
      }
    });
  };

  useEffect(() => {
    const handleEvent = (e: CustomEvent<AgentEvent>) => {
      const ev = e.detail;
      
      // Terminal events
      if (ev.type === "tool_call" && ev.tool === "shell") {
        setActiveTab("terminal");
        setTerminalLogs(prev => [...prev, `\n$ ${ev.params?.command || "Executing..."}`]);
      }

      // File write events — show in editor
      if (ev.type === "tool_call" && ev.tool === "file" && ev.params?.action === "write") {
        setActiveTab("editor");
        const path = ev.params.path || "untitled";
        const name = path.split("/").pop() || path;
        const ext = name.split(".").pop()?.toLowerCase() || "";
        const langMap: Record<string, string> = {
          py: "python", js: "javascript", ts: "typescript", tsx: "typescriptreact",
          jsx: "javascriptreact", html: "html", css: "css", json: "json",
          md: "markdown", sh: "shell", sql: "sql", yaml: "yaml",
        };
        upsertFileTab({
          path,
          name,
          content: ev.params.content || `// Writing ${name}...`,
          language: langMap[ext] || "plaintext",
        });
      }

      // File read — try loading via API
      if (ev.type === "tool_call" && ev.tool === "file" && ev.params?.action === "read") {
        setActiveTab("editor");
        const path = ev.params.path || "";
        loadFile(path).then(tab => {
          if (tab) upsertFileTab(tab);
        });
      }

      // Artifact events — show content in editor
      if (ev.type === "artifact") {
        setActiveTab("editor");
        const path = (ev as any).path || (ev as any).name || "artifact";
        const name = path.split("/").pop() || path;
        const content = (ev as any).content || "";
        
        if (content) {
          const ext = name.split(".").pop()?.toLowerCase() || "";
          const langMap: Record<string, string> = {
            py: "python", js: "javascript", ts: "typescript", json: "json",
            md: "markdown", html: "html", css: "css", sh: "shell",
          };
          upsertFileTab({
            path,
            name,
            content,
            language: langMap[ext] || "plaintext",
          });
        } else {
          // Load via API
          loadFile(path).then(tab => {
            if (tab) upsertFileTab(tab);
          });
        }
      }

      // Terminal output from tool results (messages containing commands)
      if ((ev.type === "message_info" || ev.type === "tool" || ev.type === "thought") && (ev.content || ev.text)) {
        const text = ev.content || ev.text || "";
        const lower = text.toLowerCase();
        
        if (lower.includes("запускаю команду") || lower.includes("терминал") || lower.includes("shell") || text.includes("$ ")) {
          setActiveTab("terminal");
          setTerminalLogs(prev => [...prev, text.split("терминале...").pop()?.trim() || text]);
        }
      }

      // Browser / VNC
      if (ev.type === "novnc_ready") {
        setActiveTab("browser");
        if ((ev as any).url) setVncUrl((ev as any).url);
      }
      
      if (ev.type === "desktop_frame" && (ev as any).data) {
        setDesktopFrame(`data:image/jpeg;base64,${(ev as any).data}`);
      }
      
      if (ev.type === "tool_call" && ev.tool === "browser") {
        setActiveTab("browser");
      }
    };

    window.addEventListener("archimedes-event", handleEvent as EventListener);
    return () => window.removeEventListener("archimedes-event", handleEvent as EventListener);
  }, []);

  useEffect(() => {
    if (activeTab === "terminal") {
      terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [terminalLogs, activeTab]);

  // Auto-retry VNC until ready
  useEffect(() => {
    if (activeTab === "browser" && !vncUrl && !desktopFrame) {
      const interval = setInterval(() => {
        retryVnc();
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [activeTab, vncUrl, desktopFrame]);

  // Retry VNC connection
  const retryVnc = async () => {
    setBrowserLoading(true);
    setBrowserError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/sandbox/${sessionId}/vnc`);
      if (res.ok) {
        const data = await res.json();
        if (data.url) {
          setVncUrl(data.url);
          setBrowserError(null);
        } else {
          setBrowserError("VNC URL не возвращен сервером.");
        }
      } else {
        const data = await res.json().catch(() => ({}));
        let errStr = data.detail || "Docker-контейнер ещё не готов или графическая сессия не активна.";
        if (errStr === "VNC URL not found for session") {
          errStr = "Песочница или графическая сессия пока не запущены.";
        }
        setBrowserError(errStr);
      }
    } catch {
      setBrowserError("Бэкенд недоступен. Проверьте подключение.");
    } finally {
      setBrowserLoading(false);
    }
  };

  const currentFile = fileTabs[activeFileIdx];

  // Get language for Monaco
  const getMonacoLanguage = (lang: string) => {
    const map: Record<string, string> = {
      python: "python", javascript: "javascript", typescript: "typescript",
      typescriptreact: "typescript", javascriptreact: "javascript",
      html: "html", css: "css", json: "json", markdown: "markdown",
      shell: "shell", sql: "sql", yaml: "yaml", xml: "xml",
    };
    return map[lang] || "plaintext";
  };

  return (
    <div className="flex flex-col h-full bg-[#1A1B26] text-white overflow-hidden shadow-2xl z-10 relative">
      {/* Header bar */}
      <div className="h-12 bg-[#12131C] border-b border-[#2A2B3D] flex items-center justify-between px-2 shrink-0">
        <div className="flex px-1 gap-1">
          <button 
            onClick={() => setActiveTab("editor")}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${activeTab === "editor" ? "bg-[#292E42] text-blue-400" : "text-gray-400 hover:text-white"}`}
          >
            <Code2 size={14} /> Editor
          </button>
          <button 
            onClick={() => setActiveTab("terminal")}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${activeTab === "terminal" ? "bg-[#292E42] text-green-400" : "text-gray-400 hover:text-white"}`}
          >
            <Terminal size={14} /> Terminal
          </button>
          <button 
            onClick={() => setActiveTab("browser")}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${activeTab === "browser" ? "bg-[#292E42] text-purple-400" : "text-gray-400 hover:text-white"}`}
          >
            <Monitor size={14} /> Browser
          </button>
        </div>
        <div className="flex items-center gap-4 px-2 text-xs text-gray-500">
           <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-green-500"></div> Online</div>
           <button onClick={onClose} className="p-1 hover:bg-white/10 rounded transition-colors text-gray-400 hover:text-white">
             <X size={16} />
           </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden relative">
        {activeTab === "editor" && (
          <div className="h-full flex flex-col">
            {/* File Tabs */}
            <div className="h-9 bg-[#1A1B26] flex items-center px-2 text-xs text-gray-400 border-b border-[#2A2B3D] overflow-x-auto custom-scrollbar gap-0.5">
              {fileTabs.length === 0 ? (
                <div className="flex items-center gap-2 px-3 py-1 text-gray-500">
                  <FolderOpen size={12} />
                  <span>Ожидание файлов...</span>
                </div>
              ) : (
                fileTabs.map((tab, idx) => (
                  <button
                    key={tab.path}
                    onClick={() => setActiveFileIdx(idx)}
                    className={`flex items-center gap-1.5 px-3 py-1 rounded-t-md font-mono text-[11px] whitespace-nowrap transition-colors ${
                      idx === activeFileIdx 
                        ? "bg-[#292E42] text-blue-300 border-b-2 border-blue-500" 
                        : "text-gray-500 hover:text-gray-300 hover:bg-[#1E1F2E]"
                    }`}
                  >
                    <Code2 size={10} />
                    {tab.name}
                  </button>
                ))
              )}
            </div>
            <div className="flex-1">
              {currentFile ? (
                <Editor
                  height="100%"
                  theme="vs-dark"
                  language={getMonacoLanguage(currentFile.language)}
                  value={currentFile.content}
                  options={{
                    readOnly: true,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    fontSize: 13,
                    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                    padding: { top: 16 }
                  }}
                />
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-3">
                  <Code2 size={32} className="opacity-20" />
                  <p className="text-sm">Файлы появятся при работе агента</p>
                  <p className="text-xs text-gray-600">Созданные и изменённые файлы отобразятся здесь автоматически</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "terminal" && (
          <div className="h-full bg-[#0D0D0D] p-4 overflow-y-auto font-mono text-[13px] leading-relaxed custom-scrollbar">
             {terminalLogs.length === 0 ? (
               <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-3">
                 <Terminal size={32} className="opacity-20" />
                 <p className="text-sm">Терминал пуст</p>
                 <p className="text-xs text-gray-600">Команды агента появятся здесь</p>
               </div>
             ) : (
               terminalLogs.map((log, i) => (
                 <div key={i} className="mb-1 text-gray-300 whitespace-pre-wrap">
                   {log.startsWith("$") ? <span className="text-green-400 font-bold">{log}</span> : log}
                 </div>
               ))
             )}
             <div ref={terminalEndRef} />
          </div>
        )}

        {activeTab === "browser" && (
          <div className="h-full bg-[#2B2B2B] relative">
             {desktopFrame ? (
                <img 
                  src={desktopFrame} 
                  alt="Agent Desktop Stream" 
                  className="w-full h-full object-contain bg-black"
                />
             ) : vncUrl ? (
                <iframe 
                  src={vncUrl} 
                  className="w-full h-full border-none"
                  title="Agent Browser"
                  allow="fullscreen"
                />
             ) : (
                <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-4">
                   <Monitor size={40} className="opacity-20" />
                   <p className="text-sm font-medium">Нет активной графической сессии</p>
                   <p className="text-xs text-gray-600 text-center max-w-xs">
                     Графическая сессия запустится автоматически, когда агент начнёт работу с браузером
                   </p>
                   {browserError && (
                     <p className="text-xs text-red-400/80 text-center max-w-xs mt-1">{browserError}</p>
                   )}
                   <button
                     onClick={retryVnc}
                     disabled={browserLoading}
                     className="flex items-center gap-2 px-4 py-2 bg-[#292E42] rounded-lg text-sm text-gray-300 hover:text-white hover:bg-[#333] transition-colors mt-2 disabled:opacity-50"
                   >
                     <RefreshCw size={14} className={browserLoading ? "animate-spin" : ""} />
                     {browserLoading ? "Проверка..." : "Обновить"}
                   </button>
                </div>
             )}
          </div>
        )}
      </div>

      {/* Bottom Time Machine Slider (Manus Style) */}
      <div className="h-14 bg-[#12131C] border-t border-[#2A2B3D] shrink-0 flex items-center px-4 gap-4">
         <div className="flex items-center gap-1 opacity-50 cursor-pointer hover:opacity-100 transition-opacity text-blue-400">
            <PlaySquare size={16} />
            <span className="text-xs font-semibold uppercase tracking-wider">Time Machine</span>
         </div>
         <input 
            type="range" 
            min="0" 
            max="100" 
            defaultValue="100" 
            className="flex-1 h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
         />
         <div className="text-xs font-mono text-gray-500">Live View</div>
      </div>
    </div>
  );
}
