"use client";

import { useState, useEffect, useCallback } from "react";
import {
  X, Download, Image, FileText, FileCode, File, Presentation,
  Music, Video, RefreshCw, Search, Grid3X3, List, Trash2,
  ExternalLink, Eye, FolderOpen
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ArtifactItem {
  name: string;
  path: string;
  size: number;
  modified: string;
  type: string;
  preview_url?: string;
}

interface ArtifactGalleryProps {
  isOpen: boolean;
  onClose: () => void;
  onViewArtifact?: (artifact: { name: string; content: string; path: string }) => void;
}

type ViewMode = "grid" | "list";
type FilterType = "all" | "images" | "documents" | "code" | "presentations" | "media";

const FILTERS: { key: FilterType; label: string; icon: React.ReactNode; extensions: string[] }[] = [
  { key: "all", label: "Все", icon: <FolderOpen size={14} />, extensions: [] },
  { key: "images", label: "Изображения", icon: <Image size={14} />, extensions: ["png", "jpg", "jpeg", "gif", "webp", "svg"] },
  { key: "presentations", label: "Презентации", icon: <Presentation size={14} />, extensions: ["pptx", "pdf"] },
  { key: "documents", label: "Документы", icon: <FileText size={14} />, extensions: ["md", "txt", "json", "yaml", "yml", "csv"] },
  { key: "code", label: "Код", icon: <FileCode size={14} />, extensions: ["py", "js", "ts", "tsx", "jsx", "html", "css", "sql", "sh"] },
  { key: "media", label: "Медиа", icon: <Music size={14} />, extensions: ["mp3", "wav", "mp4", "webm", "ogg"] },
];

function getFileIcon(name: string) {
  const ext = name.split(".").pop()?.toLowerCase() || "";
  if (["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(ext))
    return <Image size={20} className="text-purple-400" />;
  if (["pptx"].includes(ext))
    return <Presentation size={20} className="text-orange-400" />;
  if (["pdf"].includes(ext))
    return <FileText size={20} className="text-red-400" />;
  if (["md", "txt"].includes(ext))
    return <FileText size={20} className="text-blue-400" />;
  if (["py", "js", "ts", "tsx", "jsx", "html", "css"].includes(ext))
    return <FileCode size={20} className="text-green-400" />;
  if (["mp3", "wav", "ogg"].includes(ext))
    return <Music size={20} className="text-pink-400" />;
  if (["mp4", "webm"].includes(ext))
    return <Video size={20} className="text-cyan-400" />;
  return <File size={20} className="text-gray-400" />;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function isImageFile(name: string): boolean {
  const ext = name.split(".").pop()?.toLowerCase() || "";
  return ["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(ext);
}

export default function ArtifactGallery({ isOpen, onClose, onViewArtifact }: ArtifactGalleryProps) {
  const [artifacts, setArtifacts] = useState<ArtifactItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [activeFilter, setActiveFilter] = useState<FilterType>("all");
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());

  const fetchArtifacts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/workspace/artifacts`);
      if (res.ok) {
        const data = await res.json();
        setArtifacts(data.artifacts || []);
      }
    } catch (err) {
      console.error("Failed to fetch artifacts:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) fetchArtifacts();
  }, [isOpen, fetchArtifacts]);

  const filtered = artifacts.filter((a) => {
    // Search filter
    if (searchQuery && !a.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    // Type filter
    if (activeFilter === "all") return true;
    const ext = a.name.split(".").pop()?.toLowerCase() || "";
    const filterDef = FILTERS.find((f) => f.key === activeFilter);
    return filterDef?.extensions.includes(ext) ?? true;
  });

  const handleDownload = async (artifact: ArtifactItem) => {
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/workspace/file/download?path=${encodeURIComponent(artifact.path)}`
      );
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = artifact.name;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download error:", err);
    }
  };

  const handleView = async (artifact: ArtifactItem) => {
    if (onViewArtifact) {
      try {
        const res = await fetch(
          `${API_BASE}/api/v1/workspace/file?path=${encodeURIComponent(artifact.path)}`
        );
        if (res.ok) {
          const data = await res.json();
          onViewArtifact({
            name: artifact.name,
            content: data.content || "",
            path: artifact.path,
          });
        }
      } catch (err) {
        console.error("View error:", err);
      }
    }
  };

  const toggleSelect = (name: string) => {
    setSelectedItems((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  if (!isOpen) return null;

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
          className="relative w-[92vw] max-w-5xl max-h-[85vh] bg-[#0F1017] rounded-2xl border border-[#1E1F2E] shadow-2xl flex flex-col overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* ── Header ────────────────────────────── */}
          <div className="shrink-0 border-b border-[#1E1F2E] px-6 py-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
                  <FolderOpen size={16} className="text-white" />
                </div>
                <div>
                  <h2 className="text-white font-semibold text-lg leading-tight">Artifact Gallery</h2>
                  <p className="text-gray-500 text-xs">{artifacts.length} файлов</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={fetchArtifacts}
                  className="p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                  title="Обновить"
                >
                  <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
                </button>
                <button
                  onClick={onClose}
                  className="p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Search + View Toggle */}
            <div className="flex items-center gap-3">
              <div className="flex-1 relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Поиск по названию..."
                  className="w-full bg-[#1A1B26] border border-[#2A2B3D] rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-violet-500/50 transition-colors"
                />
              </div>
              <div className="flex bg-[#1A1B26] border border-[#2A2B3D] rounded-lg overflow-hidden">
                <button
                  onClick={() => setViewMode("grid")}
                  className={`p-2 transition-colors ${viewMode === "grid" ? "bg-violet-500/20 text-violet-400" : "text-gray-500 hover:text-white"}`}
                >
                  <Grid3X3 size={14} />
                </button>
                <button
                  onClick={() => setViewMode("list")}
                  className={`p-2 transition-colors ${viewMode === "list" ? "bg-violet-500/20 text-violet-400" : "text-gray-500 hover:text-white"}`}
                >
                  <List size={14} />
                </button>
              </div>
            </div>

            {/* Filter Tabs */}
            <div className="flex items-center gap-1.5 mt-3 overflow-x-auto scrollbar-hide">
              {FILTERS.map((f) => (
                <button
                  key={f.key}
                  onClick={() => setActiveFilter(f.key)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
                    activeFilter === f.key
                      ? "bg-violet-500/20 text-violet-300 border border-violet-500/30"
                      : "text-gray-500 hover:text-gray-300 border border-transparent hover:bg-white/5"
                  }`}
                >
                  {f.icon}
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* ── Content ───────────────────────────── */}
          <div className="flex-1 overflow-auto p-4">
            {loading ? (
              <div className="flex items-center justify-center h-60">
                <div className="flex items-center gap-3 text-gray-400">
                  <div className="w-5 h-5 rounded-full border-2 border-violet-500 border-t-transparent animate-spin" />
                  <span className="text-sm">Загрузка артефактов...</span>
                </div>
              </div>
            ) : filtered.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-60 text-gray-500">
                <FolderOpen size={40} className="mb-3 opacity-20" />
                <p className="text-sm">Артефакты не найдены</p>
              </div>
            ) : viewMode === "grid" ? (
              /* ── Grid View ── */
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {filtered.map((item) => (
                  <motion.div
                    key={item.name}
                    layout
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className={`group relative bg-[#15161F] rounded-xl border transition-all cursor-pointer hover:border-violet-500/40 hover:bg-[#1A1B28] ${
                      selectedItems.has(item.name) ? "border-violet-500/60 ring-1 ring-violet-500/20" : "border-[#1E1F2E]"
                    }`}
                    onClick={() => toggleSelect(item.name)}
                  >
                    {/* Preview Area */}
                    <div className="aspect-square rounded-t-xl overflow-hidden bg-[#0D0E14] flex items-center justify-center">
                      {isImageFile(item.name) && item.preview_url ? (
                        <img
                          src={item.preview_url}
                          alt={item.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="flex flex-col items-center gap-2 text-gray-600">
                          {getFileIcon(item.name)}
                          <span className="text-[10px] uppercase tracking-wider">
                            {item.name.split(".").pop()}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Info */}
                    <div className="p-2.5">
                      <p className="text-xs text-white font-medium truncate" title={item.name}>
                        {item.name}
                      </p>
                      <p className="text-[10px] text-gray-500 mt-0.5">{formatSize(item.size)}</p>
                    </div>

                    {/* Hover Actions */}
                    <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleView(item); }}
                        className="p-1.5 bg-black/60 rounded-md text-gray-300 hover:text-white backdrop-blur-sm"
                        title="Просмотр"
                      >
                        <Eye size={12} />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDownload(item); }}
                        className="p-1.5 bg-black/60 rounded-md text-gray-300 hover:text-white backdrop-blur-sm"
                        title="Скачать"
                      >
                        <Download size={12} />
                      </button>
                    </div>
                  </motion.div>
                ))}
              </div>
            ) : (
              /* ── List View ── */
              <div className="space-y-1">
                {filtered.map((item) => (
                  <motion.div
                    key={item.name}
                    layout
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={`group flex items-center gap-3 px-4 py-3 rounded-lg transition-all cursor-pointer hover:bg-[#1A1B28] ${
                      selectedItems.has(item.name) ? "bg-violet-500/10 border border-violet-500/30" : "border border-transparent"
                    }`}
                    onClick={() => toggleSelect(item.name)}
                  >
                    {getFileIcon(item.name)}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white truncate">{item.name}</p>
                      <p className="text-[11px] text-gray-500">{item.path}</p>
                    </div>
                    <span className="text-xs text-gray-500 shrink-0">{formatSize(item.size)}</span>
                    <span className="text-xs text-gray-600 shrink-0 w-28 text-right">{formatDate(item.modified)}</span>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleView(item); }}
                        className="p-1.5 rounded-md text-gray-400 hover:text-white hover:bg-white/10"
                        title="Просмотр"
                      >
                        <Eye size={14} />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDownload(item); }}
                        className="p-1.5 rounded-md text-gray-400 hover:text-white hover:bg-white/10"
                        title="Скачать"
                      >
                        <Download size={14} />
                      </button>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>

          {/* ── Footer ────────────────────────────── */}
          <div className="shrink-0 border-t border-[#1E1F2E] px-6 py-3 flex items-center justify-between">
            <span className="text-xs text-gray-500">
              {filtered.length} из {artifacts.length} файлов
              {selectedItems.size > 0 && ` • ${selectedItems.size} выбрано`}
            </span>
            {selectedItems.size > 0 && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    filtered
                      .filter((a) => selectedItems.has(a.name))
                      .forEach((a) => handleDownload(a));
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-500/20 text-violet-300 text-xs font-medium hover:bg-violet-500/30 transition-colors"
                >
                  <Download size={12} />
                  Скачать выбранные
                </button>
                <button
                  onClick={() => setSelectedItems(new Set())}
                  className="px-3 py-1.5 rounded-lg text-gray-500 text-xs hover:text-white hover:bg-white/5 transition-colors"
                >
                  Снять выбор
                </button>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
