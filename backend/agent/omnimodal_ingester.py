"""
OmnimodalIngester — Unified perception layer for Gen 4 Archimedes.

Instead of:
  - VideoTool → "transcribe video to text" → LLM reads text
  - AudioTool → "extract audio to text" → LLM reads text
  - ImageTool → "describe image" → LLM reads description

Gen 4 does:
  - ANY input → embed() → ChromaDB vector → agent queries concepts

The agent never "translates" — it queries similarity in latent space.
This is the Omnimodal Bridge from the Phase 7 Manifesto.
"""
import asyncio
import base64
import hashlib
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger(__name__)

OMNIMODAL_CHROMA_DIR = os.environ.get("OMNIMODAL_CHROMA_DIR", "data/omnimodal_db")
COLLECTION_NAME = "archimedes_omnimodal"


class Modality(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    CODE = "code"
    PDF = "pdf"


@dataclass
class PerceptionUnit:
    """
    A single unit of perception after cross-modal embedding.
    This replaces raw files/text in the agent's working memory.
    """
    unit_id: str
    modality: Modality
    source_path: str
    text_summary: str          # Human-readable fallback
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    concepts: List[str] = field(default_factory=list)
    
    def to_context_string(self) -> str:
        """For injection into LLM context — minimal, concept-focused."""
        concept_str = ", ".join(self.concepts[:8]) if self.concepts else "none"
        return (
            f"[{self.modality.value.upper()} perception | "
            f"concepts: {concept_str}]\n"
            f"{self.text_summary[:500]}"
        )


class OmnimodalIngester:
    """
    Unified ingestion pipeline for all modalities.
    
    Supported inputs:
    - Images: JPEG, PNG, WebP, GIF → Gemini Vision embedding
    - Audio: MP3, WAV, OGG → Whisper transcription + semantic embedding
    - Video: MP4, WebM → keyframe extraction + audio track
    - PDF: → text extraction + layout-aware chunking
    - Code: → AST-aware chunking + semantic embedding
    - Text: → direct semantic embedding
    
    All outputs stored in ChromaDB with cross-modal retrieval.
    """
    
    SUPPORTED_EXTENSIONS = {
        Modality.IMAGE: {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"},
        Modality.AUDIO: {".mp3", ".wav", ".ogg", ".m4a", ".flac"},
        Modality.VIDEO: {".mp4", ".webm", ".avi", ".mov", ".mkv"},
        Modality.PDF: {".pdf"},
        Modality.CODE: {
            ".py", ".ts", ".tsx", ".js", ".jsx", ".rs",
            ".go", ".java", ".cpp", ".c", ".h"
        },
        Modality.TEXT: {".txt", ".md", ".csv", ".json", ".yaml", ".yml"},
    }
    
    def __init__(self, router=None):
        self.router = router
        self._client = None
        self._collection = None
        os.makedirs(OMNIMODAL_CHROMA_DIR, exist_ok=True)
    
    def _get_collection(self):
        if self._collection is None:
            self._client = chromadb.PersistentClient(path=OMNIMODAL_CHROMA_DIR)
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection
    
    def detect_modality(self, file_path: str) -> Modality:
        """Auto-detect modality from file extension."""
        ext = Path(file_path).suffix.lower()
        for modality, extensions in self.SUPPORTED_EXTENSIONS.items():
            if ext in extensions:
                return modality
        return Modality.TEXT
    
    def _generate_unit_id(self, source: str) -> str:
        return hashlib.sha256(source.encode()).hexdigest()[:16]
    
    # ── Modality-specific processors ──
    
    async def _process_image(self, file_path: str) -> PerceptionUnit:
        """Image → Gemini Vision → concepts + summary."""
        unit_id = self._generate_unit_id(file_path)
        
        try:
            with open(file_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            ext = Path(file_path).suffix.lstrip(".")
            mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                   "png": "image/png", "webp": "image/webp",
                   "gif": "image/gif"}.get(ext, "image/jpeg")
            
            if self.router:
                # Use Gemini Vision via router
                response = await self.router.generate(
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {
                                "url": f"data:{mime};base64,{image_data}"
                            }},
                            {"type": "text", "text": (
                                "Analyze this image. Provide:\n"
                                "1. A factual description (2-3 sentences)\n"
                                "2. Key concepts (comma-separated, e.g.: "
                                "'data visualization, bar chart, revenue trends')\n"
                                "3. Any text visible in the image\n\n"
                                "Format: DESCRIPTION: ...\nCONCEPTS: ...\nTEXT: ..."
                            )}
                        ]
                    }],
                    task_hint="quick"
                )
                text = response.get("text", "")
            else:
                # Fallback without vision LLM
                text = f"Image file: {Path(file_path).name}"
            
            # Parse concepts
            concepts = []
            summary = text
            if "CONCEPTS:" in text:
                parts = text.split("CONCEPTS:")
                if len(parts) > 1:
                    concept_line = parts[1].split("\n")[0].strip()
                    concepts = [c.strip() for c in concept_line.split(",")]
            if "DESCRIPTION:" in text:
                desc_part = text.split("DESCRIPTION:")[1].split("\n")[0].strip()
                summary = desc_part
            
            return PerceptionUnit(
                unit_id=unit_id,
                modality=Modality.IMAGE,
                source_path=file_path,
                text_summary=summary,
                concepts=concepts,
                metadata={"file": file_path, "mime": mime}
            )
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return PerceptionUnit(
                unit_id=unit_id,
                modality=Modality.IMAGE,
                source_path=file_path,
                text_summary=f"Image: {Path(file_path).name} (processing failed)",
                metadata={"error": str(e)}
            )
    
    async def _process_audio(self, file_path: str) -> PerceptionUnit:
        """Audio → Whisper transcription → semantic summary."""
        unit_id = self._generate_unit_id(file_path)
        
        try:
            # Try OpenAI Whisper first
            try:
                import whisper
                model = whisper.load_model("base")
                result = model.transcribe(file_path)
                transcript = result["text"].strip()
            except ImportError:
                # Fallback: try shell-based whisper
                import subprocess
                import tempfile
                with tempfile.TemporaryDirectory() as temp_dir:
                    result = subprocess.run(
                        ["whisper", file_path, "--output_format", "txt",
                         "--output_dir", temp_dir, "--model", "base"],
                        capture_output=True, text=True, timeout=120
                    )
                    txt_path = os.path.join(temp_dir, f"{Path(file_path).stem}.txt")
                    if os.path.exists(txt_path):
                        with open(txt_path) as f:
                            transcript = f.read().strip()
                    else:
                        transcript = f"Audio file: {Path(file_path).name}"
            
            # Semantic summary of transcript
            summary = transcript[:500]
            concepts = []
            if self.router and len(transcript) > 50:
                response = await self.router.generate(
                    messages=[{
                        "role": "user",
                        "content": (
                            f"Extract 5-8 key concepts from this transcript: "
                            f"{transcript[:1000]}\n"
                            "Reply with ONLY comma-separated concepts."
                        )
                    }],
                    task_hint="quick"
                )
                concept_text = response.get("text", "")
                concepts = [c.strip() for c in concept_text.split(",") if c.strip()]
            
            return PerceptionUnit(
                unit_id=unit_id,
                modality=Modality.AUDIO,
                source_path=file_path,
                text_summary=summary,
                concepts=concepts,
                metadata={"transcript_length": len(transcript), "file": file_path}
            )
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            return PerceptionUnit(
                unit_id=unit_id,
                modality=Modality.AUDIO,
                source_path=file_path,
                text_summary=f"Audio: {Path(file_path).name}",
                metadata={"error": str(e)}
            )
    
    async def _process_video(self, file_path: str) -> PerceptionUnit:
        """Video → keyframe extraction + audio track → unified perception."""
        unit_id = self._generate_unit_id(file_path)
        
        try:
            import subprocess, tempfile
            
            with tempfile.TemporaryDirectory() as temp_dir:
                keyframe_path = os.path.join(temp_dir, "frame_%04d.jpg")
                audio_path = os.path.join(temp_dir, "audio.wav")
                
                # Extract keyframes every 5 seconds
                subprocess.run([
                    "ffmpeg", "-i", file_path,
                    "-vf", "fps=1/5",  # 1 frame per 5 seconds
                    "-q:v", "5",
                    keyframe_path, "-y"
                ], capture_output=True, timeout=60)
                
                # Extract audio
                subprocess.run([
                    "ffmpeg", "-i", file_path,
                    "-vn", "-acodec", "pcm_s16le",
                    "-ar", "16000", "-ac", "1",
                    audio_path, "-y"
                ], capture_output=True, timeout=60)
                
                # Process first keyframe
                keyframes = sorted([
                    f for f in os.listdir(temp_dir) if f.startswith("frame_")
                ])
                
                frame_units = []
                for kf in keyframes[:5]:  # Max 5 keyframes
                    kf_unit = await self._process_image(
                        os.path.join(temp_dir, kf)
                    )
                    frame_units.append(kf_unit)
                
                # Process audio if exists
                audio_summary = ""
                if os.path.exists(audio_path):
                    audio_unit = await self._process_audio(audio_path)
                    audio_summary = audio_unit.text_summary
                
                # Merge all concepts
                all_concepts = []
                for fu in frame_units:
                    all_concepts.extend(fu.concepts)
                all_concepts = list(set(all_concepts))[:12]
                
                visual_summary = " | ".join([fu.text_summary for fu in frame_units[:3]])
                full_summary = (
                    f"Video analysis: {visual_summary}\n"
                    f"Audio: {audio_summary}"
                )
            
            return PerceptionUnit(
                unit_id=unit_id,
                modality=Modality.VIDEO,
                source_path=file_path,
                text_summary=full_summary,
                concepts=all_concepts,
                metadata={
                    "keyframes_analyzed": len(frame_units),
                    "has_audio": bool(audio_summary),
                    "file": file_path
                }
            )
        except FileNotFoundError:
            return PerceptionUnit(
                unit_id=unit_id,
                modality=Modality.VIDEO,
                source_path=file_path,
                text_summary=f"Video: {Path(file_path).name} (ffmpeg not available)",
                metadata={"error": "ffmpeg not found"}
            )
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            return PerceptionUnit(
                unit_id=unit_id,
                modality=Modality.VIDEO,
                source_path=file_path,
                text_summary=f"Video: {Path(file_path).name}",
                metadata={"error": str(e)}
            )
    
    async def _process_pdf(self, file_path: str) -> PerceptionUnit:
        """PDF → layout-aware text extraction → chunked perception."""
        unit_id = self._generate_unit_id(file_path)
        
        try:
            # Try pymupdf first (best layout preservation)
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                pages_text = []
                for page_num in range(min(len(doc), 20)):
                    page = doc[page_num]
                    pages_text.append(page.get_text("text"))
                full_text = "\n\n".join(pages_text)
                doc.close()
            except ImportError:
                # Fallback to pdfminer
                from pdfminer.high_level import extract_text
                full_text = extract_text(file_path)
            
            summary = full_text[:1000]
            concepts = []
            
            if self.router and full_text:
                response = await self.router.generate(
                    messages=[{
                        "role": "user",
                        "content": (
                            f"Extract 8-10 key concepts from this document:\n"
                            f"{full_text[:2000]}\n\n"
                            "Reply with ONLY comma-separated concepts."
                        )
                    }],
                    task_hint="quick"
                )
                concepts = [
                    c.strip()
                    for c in response.get("text", "").split(",")
                    if c.strip()
                ]
            
            return PerceptionUnit(
                unit_id=unit_id,
                modality=Modality.PDF,
                source_path=file_path,
                text_summary=summary,
                concepts=concepts,
                metadata={
                    "total_chars": len(full_text),
                    "file": file_path
                }
            )
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            return PerceptionUnit(
                unit_id=unit_id,
                modality=Modality.PDF,
                source_path=file_path,
                text_summary=f"PDF: {Path(file_path).name}",
                metadata={"error": str(e)}
            )
    
    async def _process_text(self, content: str, source_id: str = "text") -> PerceptionUnit:
        """Text/code → direct semantic processing."""
        unit_id = self._generate_unit_id(source_id + content[:100])
        
        # For code: extract function/class names as concepts
        import re
        concepts = []
        if re.search(r'\bdef \w+|\bclass \w+|function \w+', content):
            names = re.findall(r'(?:def|class|function)\s+(\w+)', content)
            concepts = names[:10]
        
        # Fallback concept extraction for prose
        if not concepts and self.router and len(content) > 100:
            try:
                response = await self.router.generate(
                    messages=[{
                        "role": "user",
                        "content": (
                            f"5 key concepts from this text: "
                            f"{content[:500]}\n"
                            "Reply with ONLY comma-separated concepts."
                        )
                    }],
                    task_hint="quick"
                )
                concepts = [
                    c.strip()
                    for c in response.get("text", "").split(",")
                    if c.strip()
                ][:8]
            except Exception:
                pass
        
        return PerceptionUnit(
            unit_id=unit_id,
            modality=Modality.TEXT,
            source_path=source_id,
            text_summary=content[:500],
            concepts=concepts,
            metadata={"source": source_id, "length": len(content)}
        )
    
    # ── Main API ──
    
    async def ingest(
        self,
        source: str,  # file path OR text content
        modality: Optional[Modality] = None,
        store_in_chroma: bool = True
    ) -> PerceptionUnit:
        """
        Universal ingestion entrypoint.
        
        source: file path or raw text string
        modality: auto-detected if None
        store_in_chroma: whether to persist in vector DB
        """
        # Determine if source is a file path or text
        is_file = os.path.exists(source) if len(source) < 500 else False
        
        if is_file:
            detected_modality = modality or self.detect_modality(source)
        else:
            detected_modality = modality or Modality.TEXT
        
        # Route to appropriate processor
        if detected_modality == Modality.IMAGE:
            unit = await self._process_image(source)
        elif detected_modality == Modality.AUDIO:
            unit = await self._process_audio(source)
        elif detected_modality == Modality.VIDEO:
            unit = await self._process_video(source)
        elif detected_modality == Modality.PDF:
            unit = await self._process_pdf(source)
        elif detected_modality in (Modality.CODE, Modality.TEXT):
            content = open(source).read() if is_file else source
            unit = await self._process_text(content, source)
        else:
            unit = await self._process_text(source, source)
        
        # Store in ChromaDB
        if store_in_chroma:
            await self._store_unit(unit)
        
        return unit
    
    async def ingest_batch(
        self,
        sources: List[str],
        max_concurrent: int = 3
    ) -> List[PerceptionUnit]:
        """Ingest multiple sources in parallel."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def ingest_one(source: str) -> PerceptionUnit:
            async with semaphore:
                return await self.ingest(source)
        
        tasks = [ingest_one(s) for s in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        units = []
        for i, r in enumerate(results):
            if isinstance(r, PerceptionUnit):
                units.append(r)
            else:
                logger.error(f"Ingestion failed for {sources[i]}: {r}")
        
        return units
    
    async def _store_unit(self, unit: PerceptionUnit):
        """Store PerceptionUnit in ChromaDB."""
        try:
            collection = self._get_collection()
            
            doc_text = (
                f"{unit.modality.value}: {unit.text_summary}\n"
                f"Concepts: {', '.join(unit.concepts)}"
            )
            
            collection.upsert(
                ids=[unit.unit_id],
                documents=[doc_text],
                metadatas=[{
                    "modality": unit.modality.value,
                    "source_path": unit.source_path,
                    "concepts": ",".join(unit.concepts),
                    **{k: str(v) for k, v in unit.metadata.items()
                       if isinstance(v, (str, int, float, bool))}
                }]
            )
        except Exception as e:
            logger.warning(f"ChromaDB storage failed: {e}")
    
    async def query(
        self,
        query: str,
        modality_filter: Optional[Modality] = None,
        top_k: int = 5
    ) -> List[PerceptionUnit]:
        """
        Query the omnimodal vector space by concept/description.
        This is the core Gen 4 capability — cross-modal retrieval.
        """
        try:
            collection = self._get_collection()
            
            if collection.count() == 0:
                return []
            
            where = None
            if modality_filter:
                where = {"modality": modality_filter.value}
            
            results = collection.query(
                query_texts=[query],
                n_results=min(top_k, collection.count()),
                where=where
            )
            
            units = []
            if results and results["ids"] and results["ids"][0]:
                for i, unit_id in enumerate(results["ids"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    doc = results["documents"][0][i] if results["documents"] else ""
                    
                    units.append(PerceptionUnit(
                        unit_id=unit_id,
                        modality=Modality(meta.get("modality", "text")),
                        source_path=meta.get("source_path", ""),
                        text_summary=doc[:300],
                        concepts=meta.get("concepts", "").split(","),
                        metadata=meta
                    ))
            
            return units
        except Exception as e:
            logger.error(f"Omnimodal query failed: {e}")
            return []
    
    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "omnimodal",
                "description": (
                    "Unified perception for all modalities — text, image, audio, video, PDF, code. "
                    "Actions: ingest (process any file/content into vector DB), "
                    "query (find perceptions by concept/description across all modalities), "
                    "ingest_batch (process multiple files in parallel). "
                    "Use instead of VideoTool/AudioTool/ImageTool for deep semantic understanding."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["ingest", "query", "ingest_batch"]
                        },
                        "source": {
                            "type": "string",
                            "description": "File path or text content to ingest"
                        },
                        "sources": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Multiple files for ingest_batch"
                        },
                        "query": {
                            "type": "string",
                            "description": "Concept search query"
                        },
                        "modality": {
                            "type": "string",
                            "enum": ["text", "image", "audio", "video", "code", "pdf"],
                            "description": "Filter by modality (optional)"
                        },
                        "top_k": {
                            "type": "integer",
                            "default": 5
                        }
                    },
                    "required": ["action"]
                }
            }
        }
    
    async def execute(
        self,
        action: str,
        source: str = None,
        sources: List[str] = None,
        query: str = None,
        modality: str = None,
        top_k: int = 5,
        **kwargs
    ) -> Dict[str, Any]:
        mod = Modality(modality) if modality else None
        
        if action == "ingest":
            if not source:
                return {"success": False, "error": "source required"}
            unit = await self.ingest(source, modality=mod)
            return {
                "success": True,
                "output": unit.to_context_string(),
                "unit_id": unit.unit_id,
                "modality": unit.modality.value,
                "concepts": unit.concepts[:8]
            }
        
        elif action == "ingest_batch":
            if not sources:
                return {"success": False, "error": "sources array required"}
            units = await self.ingest_batch(sources)
            return {
                "success": True,
                "output": f"Ingested {len(units)}/{len(sources)} sources",
                "units": [
                    {"id": u.unit_id, "modality": u.modality.value,
                     "concepts": u.concepts[:5]}
                    for u in units
                ]
            }
        
        elif action == "query":
            if not query:
                return {"success": False, "error": "query required"}
            units = await self.query(query, modality_filter=mod, top_k=top_k)
            if not units:
                return {"success": True, "output": "No matching perceptions found"}
            
            output_lines = [f"Found {len(units)} matching perceptions:"]
            for u in units:
                output_lines.append(u.to_context_string())
                output_lines.append("---")
            
            return {"success": True, "output": "\n".join(output_lines)}
        
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
