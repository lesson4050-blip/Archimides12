"use client";

import { memo } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import MessagePill from "../MessagePill";
import { useAppStore, Message } from "@/lib/store";

const MessageItem = memo(({ msg, isConsecutive }: { msg: Message, isConsecutive?: boolean }) => {
  const { setViewingArtifact } = useAppStore();

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex w-full ${msg.role === "user" ? "justify-end" : "justify-start"} ${isConsecutive ? "-mt-4" : ""}`}
    >
      {msg.role === "user" ? (
        <div className="bg-[#2B2B2B] text-white/90 px-5 py-3 rounded-[24px] max-w-[85%] text-[15px] font-medium leading-relaxed rounded-tr-sm">
          {msg.content}
        </div>
      ) : msg.type === "artifact" && msg.artifactData ? (
        <div className="flex gap-4 w-full max-w-[90%] group">
          <div className="w-8 h-8 rounded shrink-0 flex items-center justify-center mt-0.5">
            {!isConsecutive && (
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/20 flex items-center justify-center group overflow-hidden">
                 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-400 group-hover:scale-110 group-hover:rotate-12 transition-all duration-300 drop-shadow-[0_0_8px_rgba(96,165,250,0.5)]"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.29 7 12 12 20.71 7"></polyline><line x1="12" y1="22" x2="12" y2="12"></line></svg>
              </div>
            )}
          </div>
          <div className="flex flex-col gap-1 w-full">
            {!isConsecutive && (
              <div className="flex items-center gap-2 text-sm text-gray-500 font-medium tracking-wide">
                archimedes <span className="bg-[#262626] text-[10px] px-1.5 py-0.5 rounded text-gray-400">Lite</span>
              </div>
            )}
            <div className={!isConsecutive ? "mt-2" : "mt-0"}>
              <button
                 onClick={() => setViewingArtifact(msg.artifactData!)}
                 className="flex items-center gap-3 px-4 py-3 bg-[#1A1B26] border border-[#2A2B3D] rounded-xl hover:border-blue-500/40 hover:bg-[#1E1F2E] transition-all cursor-pointer group/artifact w-fit max-w-full"
              >
                 <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/20 flex items-center justify-center shrink-0">
                   <span className="text-lg">📄</span>
                 </div>
                 <div className="flex flex-col items-start min-w-0">
                   <span className="text-white text-sm font-medium truncate">{msg.artifactData.name}</span>
                   <span className="text-gray-500 text-xs">Нажмите для просмотра</span>
                 </div>
                 <svg className="w-4 h-4 text-gray-500 group-hover/artifact:text-blue-400 transition-colors ml-2 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex gap-4 w-full max-w-[90%] group">
          <div className="w-8 h-8 rounded shrink-0 flex items-center justify-center mt-0.5">
            {!isConsecutive && (
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/20 flex items-center justify-center group overflow-hidden">
                 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-400 group-hover:scale-110 group-hover:rotate-12 transition-all duration-300 drop-shadow-[0_0_8px_rgba(96,165,250,0.5)]"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.29 7 12 12 20.71 7"></polyline><line x1="12" y1="22" x2="12" y2="12"></line></svg>
              </div>
            )}
          </div>
          <div className="flex flex-col gap-1 w-full">
            {!isConsecutive && (
              <div className="flex items-center gap-2 text-sm text-gray-500 font-medium tracking-wide">
                archimedes <span className="bg-[#262626] text-[10px] px-1.5 py-0.5 rounded text-gray-400">Lite</span>
              </div>
            )}
            <div className={!isConsecutive ? "mt-2" : "mt-0"}>
              {(msg.type === "thought" || msg.type === "tool" || msg.type === "plan") ? (
                <MessagePill type={msg.type} content={msg.content} />
              ) : msg.type === "file_download" ? (
                <div className="flex items-center gap-3 p-4 rounded-xl bg-violet-600/10 border border-violet-500/30 mt-2">
                  <span className="text-2xl">📊</span>
                  <div className="flex-1">
                    <div className="font-medium text-sm text-white">
                      {msg.content}
                    </div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      {msg.filename} • {msg.size_kb} KB
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {msg.preview_url && (
                      <a href={msg.preview_url}
                         target="_blank" rel="noreferrer"
                         className="text-xs px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors">
                        Preview
                      </a>
                    )}
                    <a href={msg.download_url}
                       download={msg.filename}
                       className="text-xs px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-700 text-white transition-colors font-medium">
                      ↓ Download
                    </a>
                  </div>
                </div>
              ) : (
                <div className="markdown-content prose prose-invert prose-sm max-w-none text-[#ECECEC] text-[15px] leading-relaxed mt-1">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
});

MessageItem.displayName = "MessageItem";
export default MessageItem;
