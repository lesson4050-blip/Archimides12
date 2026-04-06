# Archimedes Agent Benchmark Results (Final)
**Model**: gemma4:26b
**Environment**: Ubuntu Sandbox (cosmo-sandbox:latest)
**Hardware Constraints**: 4GB VRAM (CPU-heavy inference required sequential execution)

| Task | Category | Description | Status | Iterations | Remarks |
|---|---|---|---|---|---|
| **1** | File Sys | Create and manipulate files (`test1.txt`, `test2.txt`). | ✅ **Success** | 2 | Completed flawlessly during phase 1. |
| **2** | Shell | Run basic bash commands and capture output. | ✅ **Success** | 3 | Required list-based commands fix in executor to handle quotes. |
| **3** | Search | Use search tool to research and save a markdown file. | ✅ **Success** | 3 | Output properly saved to `test3.md`. |
| **4** | Code Gen | Write Python code to sort numbers and execute. | ✅ **Success** | 4 | Successfully wrote, executed, and captured output for `test4.py`. |
| **5** | Front-end | Build a single-file HTML/CSS/JS calculator. | ⚠️ **Partial** | 1* | Model generated perfect HTML code, but complex string escapes broke JSON parsing. HTML saved manually. |
| **6** | Browser | Extract top 5 trending GitHub repos using Browser. | ❌ **Failed** | 1 | Model output raw `<thought>` tags and aborted loop instead of calling a tool. |
| **7** | Back-end | Create FastAPI REST API, test with `curl`, run background port. | ✅ **Success** | 11 | Complete success. Code generated, endpoints tested via CURL, ngrok port exposed successfully. |
| **8** | Data Sci | Generate 100 sales records, calculate revenue, save report. | ⚠️ **Partial** | 1* | Generated perfectly correct python code, but JSON parsing failed due to newlines. Script tested locally. |
| **9** | Web App | Create Notes App with localStorage, dark theme, serve on 8090. | ✅ **Success** | 6 | Web app created, python `http.server` started in background, and ngrok exposed port successfully. Operator hung at the final message format. |
| **10** | Research | Compare Gemma 4 vs Llama 4, generate 500+ word markdown report. | ✅ **Success** | 3 | Connected to internet, researched, and generated a correctly formatted markdown report (`test10_report.md`). |

---

### **Executive Summary & Observations**
1. **Tool Execution:** The agent executes tools effectively (especially shell and file system operations). The `nohup` fixes and reliability rules improved stability significantly for Phase 2 tasks (Servers and Data Science).
2. **JSON Parsing Resiliency:** The native JSON output formatting from the local `gemma4:26b` model is sometimes brittle when producing large strings containing double-quotes `"` or newlines `\n` inside the JSON value. This accounts for the partial failures in Tasks 5 and 8.
3. **Execution Mode:** Due to the physical constraint of running a 26B model on 4GB VRAM, processing is slow and parallel runs crash. Sequential evaluation is extremely stable.
