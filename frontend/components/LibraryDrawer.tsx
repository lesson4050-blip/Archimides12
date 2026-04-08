"use client";

import { useState, useEffect } from "react";
import { X, Library, FileText, Download, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface WorkspaceFile {
  name: string;
  path: string;
  size: number;
  modified: string;
}

interface LibraryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function LibraryDrawer({ isOpen, onClose }: LibraryDrawerProps) {
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchFiles();
    }
  }, [isOpen]);

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/workspace");
      const data = await res.json();
      if (data.files) {
        setFiles(data.files.sort((a: WorkspaceFile, b: WorkspaceFile) => new Date(b.modified).getTime() - new Date(a.modified).getTime()));
      }
    } catch (e) {
      console.error("Failed to fetch workspace files", e);
    } finally {
      setLoading(false);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return bytes + " B";
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    else return (bytes / 1048576).toFixed(1) + " MB";
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div 
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed inset-y-0 left-[260px] z-30 w-full max-w-[320px] bg-[#121212] border-r border-[#222] shadow-2xl flex flex-col text-[#ECECEC]"
          >
            {/* Header */}
            <div className="px-5 py-4 flex items-center justify-between border-b border-[#222] shrink-0">
              <div className="flex items-center gap-3 text-lg font-medium">
                <Library size={20} className="text-gray-400" />
                Библиотека
              </div>
              <button 
                onClick={onClose}
                className="text-gray-400 hover:text-white p-1.5 rounded-md hover:bg-[#262626] transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-3 flex flex-col gap-2 bg-[#181818]">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-40 text-gray-400 gap-3">
                  <Loader2 size={24} className="animate-spin text-blue-500" />
                  <span className="text-sm">Загрузка файлов...</span>
                </div>
              ) : files.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 text-gray-500 gap-2">
                  <Library size={32} className="opacity-50" />
                  <span className="text-sm">Workspace пуст</span>
                </div>
              ) : (
                files.map((file, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-[#222] border border-[#333] hover:border-[#555] transition-colors group cursor-pointer">
                    <div className="flex items-center gap-3 overflow-hidden">
                       <FileText size={18} className="text-blue-400 shrink-0" />
                       <div className="flex flex-col overflow-hidden">
                          <span className="text-sm font-medium text-white truncate">{file.name}</span>
                          <span className="text-xs text-gray-500">{formatSize(file.size)}</span>
                       </div>
                    </div>
                    <button className="p-1.5 text-gray-500 hover:text-white opacity-0 group-hover:opacity-100 transition-all rounded hover:bg-[#333]">
                       <Download size={14} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
