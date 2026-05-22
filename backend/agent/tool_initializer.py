"""
Tool Initializer — Declarative Tool Registry
Replaces the 468-line God Object initialization script.
"""
import logging
import os
import importlib
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Declarative tool registry.
# Format: { "name": "...", "module": "...", "class": "...", "kwargs": {"arg_name": "dep_name"} }
# If kwargs is present, it maps the tool's __init__ argument name to a string representing the dependency.
TOOL_CONFIG = [
    {"name": "file", "module": "backend.tools.file_tool", "class": "FileTool", "kwargs": {"filesystem": "filesystem"}},
    {"name": "search", "module": "backend.tools.search_tool", "class": "SearchTool"},
    {"name": "shell", "module": "backend.tools.shell_tool", "class": "ShellTool", "kwargs": {"executor": "executor"}},
    {"name": "browser", "module": "backend.agent.tools.browser_tool", "class": "BrowserTool", "kwargs": {"sandbox_manager": "sandbox_manager"}},
    {"name": "web_read", "module": "backend.tools.web_tool", "class": "WebTool"},
    {"name": "mcts_snapshot", "module": "backend.tools.mcts_snapshot_tool", "class": "MCTSSnapshotTool", "kwargs": {"filesystem": "filesystem"}},
    {"name": "vision_critic", "module": "backend.tools.vision_critic_tool", "class": "VisionCriticTool", "kwargs": {"router": "router"}},
    {"name": "pdf", "module": "backend.agent.tools.pdf_tool", "class": "PDFTool"},
    {"name": "image_gen", "module": "backend.agent.tools.image_gen_tool", "class": "ImageGenTool"},
    {"name": "github", "module": "backend.agent.tools.github_tool", "class": "GithubTool"},
    {"name": "email", "module": "backend.agent.tools.email_tool", "class": "EmailTool"},
    {"name": "vision_browser", "module": "backend.tools.vision_browser_tool", "class": "VisionBrowserTool", "kwargs": {"router": "router"}},
    {"name": "canvas", "module": "backend.agent.tools.canvas_engine", "class": "CanvasEngine", "kwargs": {"router": "router"}},
    {"name": "marp", "module": "backend.agent.tools.marp_engine", "class": "MarpEngine", "kwargs": {"router": "router"}},
    {"name": "omnimodal", "module": "backend.agent.omnimodal_ingester", "class": "OmnimodalIngester", "kwargs": {"router": "router"}},
    {"name": "computer", "module": "backend.agent.tools.desktop_tool", "class": "DesktopTool"},
    {"name": "mutate_test", "module": "backend.agent.tools.mutation_tool", "class": "MutationTool"},
    {"name": "swe_rag", "module": "backend.agent.tools.swe_rag_tool", "class": "SWERagTool"},
    {"name": "video", "module": "backend.agent.tools.utility_tools", "class": "VideoTool"},
    {"name": "audio", "module": "backend.agent.tools.utility_tools", "class": "AudioTool"},
    {"name": "sheets", "module": "backend.agent.tools.utility_tools", "class": "SheetsTool"},
    {"name": "schedule", "module": "backend.tools.schedule_tool", "class": "ScheduleTool"},
    {"name": "trigger", "module": "backend.tools.trigger_tool", "class": "TriggerTool"},
    {"name": "voice", "module": "backend.tools.voice_tool", "class": "VoiceTool"},
    {"name": "monitor", "module": "backend.tools.monitor_tool", "class": "MonitorTool"},
    {"name": "document", "module": "backend.tools.document_tool", "class": "DocumentTool"},
    {"name": "mirofish", "module": "backend.tools.mirofish_tool", "class": "MiroFishTool"},
    {"name": "ast_navigator", "module": "backend.tools.ast_tool", "class": "ASTTool"},
    {"name": "infra", "module": "backend.agent.tools.infra_tool", "class": "InfraTool"},
    {"name": "log_analyzer", "module": "backend.tools.log_analyzer_tool", "class": "LogAnalyzerTool"},
    {"name": "vector_search", "module": "backend.tools.vector_search", "class": "VectorSearchEngine", "kwargs": {"workspace_dir": "workspace_dir"}},
    {"name": "expose", "module": "backend.tools.expose_tool", "class": "ExposeTool", "kwargs": {"executor": "executor"}},
    {"name": "mcp_connect", "module": "backend.tools.mcp_tool", "class": "MCPTool", "kwargs": {"mcp_client": "mcp_client", "sync_callback": "sync_callback"}},
    {"name": "media", "module": "backend.tools.media_tool", "class": "MediaTool"},
    {"name": "repo_map", "module": "backend.tools.repo_map_tool", "class": "RepoMapTool"},
    {"name": "fast_linter", "module": "backend.tools.linter_tool", "class": "LinterTool"},
    {"name": "git_forensics", "module": "backend.tools.git_forensics_tool", "class": "GitForensicsTool"},
    {"name": "git", "module": "backend.tools.git_tool", "class": "GitTool"},
    {"name": "python_repl", "module": "backend.tools.repl_tool", "class": "ReplTool"},
    {"name": "deploy", "module": "backend.tools.deploy_tool", "class": "DeployTool"},
    {"name": "patch", "module": "backend.tools.patch_tool", "class": "PatchTool"},
    {"name": "vision", "module": "backend.tools.vision_tool", "class": "VisionTool"},
    {"name": "code_edit", "module": "backend.tools.code_editor_tool", "class": "CodeEditorTool"},
    {"name": "parallel_search", "module": "backend.tools.parallel_search_tool", "class": "ParallelSearchTool"},
    {"name": "audio_synth", "module": "backend.tools.audio_synth_tool", "class": "AudioSynthTool"},
    {"name": "bio", "module": "backend.tools.bio_tool", "class": "BioTool"},
    {"name": "finance", "module": "backend.tools.finance_tool", "class": "FinanceTool"},
    {"name": "notebook", "module": "backend.tools.notebook_tool", "class": "NotebookTool"},
    {"name": "grep", "module": "backend.tools.grep_tool", "class": "GrepTool"},
    {"name": "glob", "module": "backend.tools.glob_tool", "class": "GlobTool"},
    {"name": "semantic_search", "module": "backend.tools.semantic_search", "class": "SemanticSearchEngine", "kwargs": {"root_dir": "workspace_dir"}},
]

class ToolInitializer:
    """
    Registers all available tools dynamically based on TOOL_CONFIG.
    """
    def __init__(self, tool_registry, session_id: str, agent: Any):
        self.tool_registry = tool_registry
        self.session_id = session_id
        self.agent = agent
        self._critical_tools = {"file", "search", "shell", "message"}

    def _build_dependencies(self) -> Dict[str, Any]:
        """Gather all possible dependencies a tool might need."""
        from backend.sandbox.singleton import sandbox_manager
        
        deps = {
            "sandbox_manager": sandbox_manager,
            "filesystem": sandbox_manager.filesystem,
            "executor": sandbox_manager.executor,
            "router": getattr(self.agent, "router", None),
            "mcp_client": getattr(self.agent, "mcp_client", None),
            "sync_callback": getattr(self.agent, "sync_mcp_tools", None),
            "workspace_dir": os.environ.get("WORKSPACE_DIR", "/home/ubuntu/workspace"),
        }
        return deps

    def initialize_all(self) -> Dict[str, Any]:
        _pre_count = len(self.tool_registry.tools)
        deps = self._build_dependencies()

        # 1. Register specialized inline tools (that don't fit the generic pattern)
        try:
            from backend.tools.plan_tool import PlanTool
            from backend.agent.planner import PlanManager
            self.agent.plan_manager = PlanManager(session_id=self.session_id or "default")
            self.agent.plan_tool = PlanTool(plan_manager=self.agent.plan_manager)
            self.tool_registry.register("plan", self.agent.plan_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register PlanTool: {e}")

        try:
            async def _dummy_message(**kwargs):
                return {"success": True, "output": "Message generated."}
            self.tool_registry.register("message", _dummy_message)
        except Exception as e:
            logger.error(f"Failed to register message handler: {e}")

        # 2. Declarative Registration
        for config in TOOL_CONFIG:
            tool_name = config["name"]
            try:
                module = importlib.import_module(config["module"])
                tool_class = getattr(module, config["class"])
                
                # Resolve kwargs
                init_kwargs = {}
                for kwarg_name, dep_name in config.get("kwargs", {}).items():
                    init_kwargs[kwarg_name] = deps.get(dep_name)
                    
                tool_instance = tool_class(**init_kwargs)
                
                # Register tool logic
                if hasattr(self.agent, "register_tool"):
                    self.agent.register_tool(tool_name, tool_instance.execute)
                else:
                    self.tool_registry.register(tool_name, tool_instance.execute)
                    
                # Save to agent namespace for backwards compatibility
                setattr(self.agent, f"{tool_name}_tool", tool_instance)

            except Exception as e:
                logger.debug(f"Tool '{tool_name}' unavailable: {e}")

        logger.info("ToolInitializer: explicit registration complete")

        # 3. Auto-discover additional tools
        for path in ["backend/tools", "backend/agent/tools"]:
            try:
                new_count = self.tool_registry.auto_discover_tools(path)
                if new_count > 0:
                    logger.info(f"ToolInitializer: auto-discovered {new_count} tools from {path}")
            except Exception as e:
                logger.debug(f"Auto-discovery in {path} skipped: {e}")

        # 4. Consolidated Registration Report
        total_active = len(self.tool_registry.tools)
        registered_this_session = total_active - _pre_count
        
        report_lines = [
            f"TOOL REGISTRATION: {registered_this_session} tools registered this session, "
            f"{total_active} total active"
        ]
        
        missing_critical = []
        for critical in sorted(self._critical_tools):
            is_active = critical in self.tool_registry.tools
            status = "✅ YES" if is_active else "🚨 NO"
            report_lines.append(f"  CRITICAL [{critical}]: {status}")
            if not is_active:
                missing_critical.append(critical)
        
        if missing_critical:
            report_lines.append(
                f"🚨 ALERT: {len(missing_critical)} critical tools missing: "
                f"{', '.join(missing_critical)}"
            )
        
        for line in report_lines:
            logger.info(f"ToolInitializer: {line}")

        return {
            "registered": list(self.tool_registry.tools.keys()),
            "total": len(self.tool_registry.tools),
            "missing_critical": missing_critical
        }
