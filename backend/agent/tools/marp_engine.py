"""
Archimedes Marp Engine — High-performance premium presentation generator.

Generates beautiful, responsive presentations in Marp Markdown format,
and compiles them instantly to self-contained interactive HTML or vector PDF.
"""
import os
import re
import json
import logging
import subprocess
import tempfile
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Premium Archimedes CSS styling for Marp
MARP_THEME_CSS = """
section {
  font-family: 'Inter', -apple-system, sans-serif;
  background: radial-gradient(circle at 50% 50%, #111827 0%, #030712 100%);
  color: #e5e7eb;
  padding: 50px 80px;
  font-size: 1.4rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
h1, h2, h3 {
  font-family: 'Inter', -apple-system, sans-serif;
  font-weight: 800;
  margin-top: 0;
}
h1 {
  font-size: 3.2rem;
  color: #ffffff;
  margin-bottom: 20px;
  letter-spacing: -0.025em;
  background: linear-gradient(135deg, #a78bfa 0%, #6366f1 50%, #3b82f6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
h2 {
  font-size: 2.2rem;
  color: #a78bfa;
  margin-bottom: 15px;
  border-bottom: 1px solid rgba(167, 139, 250, 0.2);
  padding-bottom: 8px;
}
h3 {
  font-size: 1.6rem;
  color: #60a5fa;
  margin-bottom: 10px;
}
p, li {
  line-height: 1.6;
  color: #cbd5e1;
}
ul, ol {
  margin-top: 10px;
  margin-bottom: 10px;
}
li {
  margin-bottom: 8px;
}
strong {
  color: #f3f4f6;
  font-weight: 600;
}
code {
  background: rgba(255, 255, 255, 0.06);
  color: #38bdf8;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  padding: 0.1em 0.4em;
  font-size: 0.85em;
}
pre {
  background: #090d16 !important;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px;
  margin-top: 15px;
  overflow: auto;
}
pre code {
  background: transparent;
  border: none;
  color: #e5e7eb;
  padding: 0;
  font-size: 0.9em;
}
footer {
  font-size: 0.8rem;
  color: #6b7280;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 10px;
}
header {
  font-size: 0.8rem;
  color: #4b5563;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

/* Custom visual grid & card components */
.grid-2 {
  display: grid;
  grid-template-cols: 1fr 1fr;
  gap: 30px;
  margin-top: 15px;
  text-align: left;
}
.grid-3 {
  display: grid;
  grid-template-cols: 1fr 1fr 1fr;
  gap: 20px;
  margin-top: 15px;
  text-align: left;
}
.card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}
.card-purple {
  border-color: rgba(167, 139, 250, 0.2);
  background: linear-gradient(135deg, rgba(167, 139, 250, 0.02) 0%, rgba(99, 102, 241, 0.02) 100%);
}
.card-blue {
  border-color: rgba(96, 165, 250, 0.2);
  background: linear-gradient(135deg, rgba(96, 165, 250, 0.02) 0%, rgba(59, 130, 246, 0.02) 100%);
}
.highlight-text {
  font-size: 1.8rem;
  font-weight: 300;
  line-height: 1.7;
  color: #e2e8f0;
  text-align: center;
  font-style: italic;
}
.metric-value {
  font-size: 3.5rem;
  font-weight: 800;
  color: #ffffff;
  margin-bottom: 5px;
  background: linear-gradient(to right, #ffffff, #93c5fd);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.metric-label {
  font-size: 0.9rem;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
"""

MARP_GENERATION_PROMPT = """You are an elite, world-class presentation designer and strategic communicator for Archimedes AI.
Your goal is to synthesize the provided topic and research data into a beautiful, highly informative, and visually stunning slide deck using **Marp Markdown**.

TOPIC: {topic}
AUDIENCE: {audience}
SLIDE COUNT: {slide_count}
STYLE: {style}
RESEARCH DATA:
{research_data}

---

MARP SYNTAX RULES & FORMATTING:
1. Every slide starts with a separator `---` on a new line.
2. The very first slide (Cover Slide) must have YAML frontmatter configuring Marp:
   ```yaml
   ---
   marp: true
   theme: uncover
   class: invert
   paginate: true
   backgroundColor: #030712
   color: #e5e7eb
   style: |
     /* Embedded theme styles (already handled by MarpEngine - do not copy them) */
   ---
   ```
3. Do NOT output a custom CSS `style` key in the frontmatter. Just output the simple frontmatter as shown above.
4. Separate slides cleanly using `---`.
5. Footer and Header: You can define a global footer/header in the frontmatter or on any slide:
   `<!-- footer: "Archimedes AI • Confidential" -->`
   `<!-- header: "RESEARCH SYNTHESIS" -->`

DESIGN & LAYOUT GUIDELINES:
1. **Diverse Layouts**: Avoid using boring bullet lists on every slide! Marp allows standard HTML classes. Use these custom CSS classes to build beautiful slides:
   - **Split Pane (2 columns)**: Use `<div class="grid-2">` to create side-by-side content.
     ```html
     <div class="grid-2">
       <div>
         <h3>Column Left</h3>
         <p>Text content here...</p>
       </div>
       <div>
         <h3>Column Right</h3>
         <p>Text content here...</p>
       </div>
     </div>
     ```
   - **Cards Grid (3 columns)**: Use `<div class="grid-3">` with `<div class="card card-purple">` or `<div class="card card-blue">`.
     ```html
     <div class="grid-3">
       <div class="card card-purple">
         <h3>Card Title 1</h3>
         <p>Description...</p>
       </div>
       <div class="card card-blue">
         <h3>Card Title 2</h3>
         <p>Description...</p>
       </div>
       <div class="card">
         <h3>Card Title 3</h3>
         <p>Description...</p>
       </div>
     </div>
     ```
   - **Big Quote / Highlight**:
     ```html
     <p class="highlight-text">
       "This is a massive, highly inspiring quote that draws user attention."
     </p>
     ```
   - **Metrics Grid**: Combine split columns with big numbers:
     ```html
     <div class="grid-2">
       <div class="card">
         <div class="metric-value">99.9%</div>
         <div class="metric-label">System Uptime</div>
       </div>
       <div class="card">
         <div class="metric-value">$4.2B</div>
         <div class="metric-label">Market Value</div>
       </div>
     </div>
     ```
   - **Code Showcase**: Standard markdown fenced code blocks:
     ```python
     def hello():
         print("Archimedes AI initialized")
     ```
2. **Language Adaptive Rule**: If the topic or research data is in Russian (or Cyrillic), you MUST generate all slide content (titles, texts, quotes, tables) in flawless, professional Russian.
3. **Deep Content**: Write extremely informative, fact-based content. Forbid generic placeholders ("Lorem Ipsum", "point 1"). Use real names, dates, metrics, and technical terms from the RESEARCH DATA.
4. **Structured Bullets**: For any bullet points, always start with a bold concept name and a colon: `**Concept**: Detailed 1-2 sentence description.`

Output ONLY the raw Marp Markdown file. Do not wrap it in ```markdown blocks, do not explain anything, just output the raw slides."""


class MarpEngine:
    """Marp Markdown Presentation Generation & Compilation Engine."""

    def __init__(self, router=None):
        self.router = router

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "marp",
                "description": (
                    "Generate and compile premium Marp Markdown presentations. "
                    "Actions: generate (create slides markdown), compile_html (compile to standalone HTML), "
                    "compile_pdf (compile to premium PDF)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["generate", "compile_html", "compile_pdf"]
                        },
                        "topic": {"type": "string"},
                        "audience": {"type": "string", "default": "general"},
                        "slide_count": {"type": "integer", "default": 6},
                        "style": {"type": "string", "default": "professional"},
                        "research_data": {"type": "string"},
                        "markdown": {"type": "string", "description": "Markdown to compile"}
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(
        self,
        action: str,
        topic: str = None,
        audience: str = "general",
        slide_count: int = 6,
        style: str = "professional",
        research_data: str = "",
        markdown: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        
        if action == "generate":
            if not topic:
                return {"success": False, "error": "topic required"}
            if not self.router:
                from backend.models.model_router import ModelRouter
                self.router = ModelRouter()
            
            prompt = MARP_GENERATION_PROMPT.format(
                topic=topic,
                audience=audience,
                slide_count=slide_count,
                style=style,
                research_data=research_data or "Generate using your deep internal knowledge bases."
            )
            
            try:
                response = await self.router.generate(
                    messages=[{"role": "user", "content": prompt}],
                    task_hint="quality",
                    max_tokens=4000,
                    temperature=0.3
                )
                
                generated_md = response.get("text", "").strip()
                
                # Cleanup markdown wrapper if the LLM outputted ```markdown ... ```
                if generated_md.startswith("```markdown"):
                    generated_md = re.sub(r"^```markdown\n", "", generated_md)
                    generated_md = re.sub(r"\n```$", "", generated_md)
                elif generated_md.startswith("```"):
                    generated_md = re.sub(r"^```\n", "", generated_md)
                    generated_md = re.sub(r"\n```$", "", generated_md)
                
                # Inject our custom theme CSS variables dynamically into the frontmatter
                generated_md = self._inject_theme_css(generated_md)
                
                return {
                    "success": True,
                    "markdown": generated_md,
                    "model_used": response.get("model_used", "unknown")
                }
            except Exception as e:
                logger.error(f"Marp slide generation failed: {e}")
                return {"success": False, "error": str(e)}
        
        elif action in ["compile_html", "compile_pdf"]:
            if not markdown:
                return {"success": False, "error": "markdown string required"}
            
            # Inject theme CSS if not present
            markdown = self._inject_theme_css(markdown)
            
            # Setup workspace temp directory safely
            workspace_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            tmp_dir = os.path.join(workspace_dir, "tmp")
            os.makedirs(tmp_dir, exist_ok=True)
            
            # Generate safe temp file names
            timestamp = int(datetime.now(timezone.utc).timestamp())
            md_file = os.path.join(tmp_dir, f"slide_{timestamp}.md")
            out_ext = "html" if action == "compile_html" else "pdf"
            out_file = os.path.join(tmp_dir, f"slide_{timestamp}.{out_ext}")
            
            try:
                # Write markdown source
                with open(md_file, "w", encoding="utf-8") as f:
                    f.write(markdown)
                
                # Build Marp-CLI compilation command
                # npx -y @marp-team/marp-cli md_file -o out_file
                cmd = ["npx", "-y", "@marp-team/marp-cli", "--html", "true", md_file, "-o", out_file]
                
                # Add pdf flag if compiling to pdf
                if action == "compile_pdf":
                    cmd.append("--pdf")
                
                logger.info(f"Running Marp CLI: {' '.join(cmd)}")
                
                # Execute in subprocess
                # On Windows, shell=True is needed to run npx properly
                shell = os.name == "nt"
                process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    shell=shell,
                    timeout=45
                )
                
                if process.returncode != 0:
                    err_msg = process.stderr or process.stdout or "Unknown compiler error"
                    logger.error(f"Marp-CLI compilation failed: {err_msg}")
                    return {"success": False, "error": f"Marp-CLI failed: {err_msg}"}
                
                if not os.path.exists(out_file):
                    return {"success": False, "error": "Output file was not generated by compiler"}
                
                if action == "compile_html":
                    with open(out_file, "r", encoding="utf-8") as f:
                        compiled_html = f.read()
                    
                    # Cleanup temp files
                    self._cleanup_files([md_file, out_file])
                    
                    return {
                        "success": True,
                        "html": compiled_html
                    }
                else:
                    # PDF compilation: return the file path (do not cleanup yet, the caller will read/stream the file)
                    # We will only cleanup the md source file
                    self._cleanup_files([md_file])
                    return {
                        "success": True,
                        "pdf_path": out_file
                    }
            except subprocess.TimeoutExpired:
                logger.error("Marp compilation timed out after 45 seconds")
                self._cleanup_files([md_file, out_file])
                return {"success": False, "error": "Marp compilation timed out"}
            except Exception as e:
                logger.error(f"Marp compilation error: {e}")
                self._cleanup_files([md_file, out_file])
                return {"success": False, "error": str(e)}
        
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    def _inject_theme_css(self, markdown: str) -> str:
        """Parse frontmatter and inject Archimedes premium theme CSS."""
        if not markdown.strip().startswith("---"):
            # If no frontmatter at all, build default one
            header = f"---\nmarp: true\ntheme: uncover\nclass: invert\npaginate: true\nbackgroundColor: #030712\ncolor: #e5e7eb\nstyle: |\n{self._indent_css(MARP_THEME_CSS)}\n---\n"
            return header + markdown

        # We have frontmatter. Let's find the closing boundary of the first frontmatter block.
        parts = markdown.split("---", 2)
        if len(parts) < 3:
            return markdown
        
        frontmatter = parts[1]
        body = parts[2]
        
        # Check if style is already defined. If not, add style.
        if "style:" not in frontmatter:
            style_block = f"\nstyle: |\n{self._indent_css(MARP_THEME_CSS)}"
            # Strip trailing whitespace and append style block
            frontmatter = frontmatter.rstrip() + style_block
        else:
            # If style is already defined, let's append our custom CSS to it
            frontmatter = re.sub(
                r"(style:\s*\|[^\n]*)",
                r"\1\n" + self._indent_css(MARP_THEME_CSS),
                frontmatter
            )

        # Reassemble the document
        return f"---{frontmatter}\n---{body}"

    def _indent_css(self, css: str, spaces: int = 2) -> str:
        """Indent CSS text for valid YAML multiline block inclusion."""
        indent = " " * spaces
        lines = css.strip().split("\n")
        return "\n".join(f"{indent}{line}" for line in lines)

    def _cleanup_files(self, paths: List[str]):
        """Safely delete temp files."""
        for path in paths:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.debug(f"Failed to delete temp file {path}: {e}")
