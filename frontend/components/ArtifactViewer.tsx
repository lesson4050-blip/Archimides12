"use client";

import { useState, useEffect } from "react";
import { X, Copy, Check, FileJson, FileText, FileCode, Download, ExternalLink } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";

export interface ArtifactData {
  name: string;
  content: string;
  language?: string;
  path?: string;
}

interface ArtifactViewerProps {
  artifact: ArtifactData | null;
  onClose: () => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

function getLanguageFromFilename(name: string): string {
  const ext = name.split(".").pop()?.toLowerCase() || "";
  const map: Record<string, string> = {
    py: "python", js: "javascript", ts: "typescript", tsx: "typescriptreact",
    jsx: "javascriptreact", html: "html", css: "css", json: "json",
    md: "markdown", yaml: "yaml", yml: "yaml", sh: "shell",
    sql: "sql", xml: "xml", txt: "plaintext",
  };
  return map[ext] || "plaintext";
}

function getFileIcon(name: string) {
  const ext = name.split(".").pop()?.toLowerCase() || "";
  if (ext === "json") return <FileJson size={18} className="text-yellow-400" />;
  if (["md", "txt"].includes(ext)) return <FileText size={18} className="text-blue-400" />;
  return <FileCode size={18} className="text-green-400" />;
}

export default function ArtifactViewer({ artifact, onClose }: ArtifactViewerProps) {
  const [copied, setCopied] = useState(false);
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!artifact) return;

    // If we already have content inline, use it
    if (artifact.content && artifact.content.trim().length > 0) {
      setContent(artifact.content);
      setError(null);
      return;
    }

    // Otherwise fetch from API
    const fetchContent = async () => {
      setLoading(true);
      setError(null);
      try {
        const path = artifact.path || artifact.name;
        const res = await fetch(`${API_BASE}/api/v1/workspace/file?path=${encodeURIComponent(path)}`);
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();
        setContent(data.content || "");
      } catch (err: any) {
        setError(err.message || "Не удалось загрузить файл");
        setContent("");
      } finally {
        setLoading(false);
      }
    };

    fetchContent();
  }, [artifact]);

  if (!artifact) return null;

  const lang = artifact.language || getLanguageFromFilename(artifact.name);
  const isMarkdown = lang === "markdown";
  const isJson = lang === "json";

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Format JSON for display
  let displayContent = content;
  if (isJson && content) {
    try {
      displayContent = JSON.stringify(JSON.parse(content), null, 2);
    } catch {
      // keep as is
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="relative w-[90vw] max-w-3xl max-h-[80vh] bg-[#1A1B26] rounded-xl border border-[#2A2B3D] shadow-2xl flex flex-col overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="h-12 bg-[#12131C] border-b border-[#2A2B3D] flex items-center justify-between px-4 shrink-0">
            <div className="flex items-center gap-3">
              {getFileIcon(artifact.name)}
              <span className="text-white font-medium text-sm">{artifact.name}</span>
              {artifact.path && (
                <span className="text-gray-500 text-xs font-mono truncate max-w-[200px]">{artifact.path}</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md transition-colors text-gray-400 hover:text-white hover:bg-white/10"
                title="Скопировать"
              >
                {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
                {copied ? "Скопировано" : "Копировать"}
              </button>
              <button
                onClick={onClose}
                className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-md transition-colors"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-auto custom-scrollbar">
            {loading ? (
              <div className="flex items-center justify-center h-full py-20">
                <div className="flex items-center gap-3 text-gray-400">
                  <div className="w-5 h-5 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
                  <span className="text-sm">Загрузка файла...</span>
                </div>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center h-full py-20 text-gray-400 gap-3">
                <FileText size={32} className="opacity-30" />
                <p className="text-sm">{error}</p>
              </div>
            ) : isMarkdown ? (
              <div className="p-6 prose prose-invert prose-sm max-w-none">
                <ReactMarkdown>{displayContent}</ReactMarkdown>
              </div>
            ) : (
              <pre className="p-6 text-[13px] font-mono leading-relaxed text-gray-300 whitespace-pre-wrap break-words">
                <code>{displayContent}</code>
              </pre>
            )}
          </div>

          {/* Footer */}
          <div className="h-10 bg-[#12131C] border-t border-[#2A2B3D] flex items-center justify-between px-4 text-xs text-gray-500 shrink-0">
            <span>{lang.toUpperCase()}</span>
            <span>{content.length.toLocaleString()} chars</span>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
