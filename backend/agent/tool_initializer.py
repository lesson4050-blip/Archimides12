"""
Tool Initializer — extracted from core.py god object.

Handles registration of all agent tools with granular error handling.
Each tool registration is isolated in its own try/except block.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ToolInitializer:
    """
    Registers all available tools for the Archimedes agent.
    Extracted from ArchimedesCosmoAgent._init_extended_tools().
    """

    def __init__(self, tool_registry, session_id: str, agent: Any):
        self.tool_registry = tool_registry
        self.session_id = session_id
        self.agent = agent

    def initialize_all(self) -> None:
        """Register every tool with individual error isolation."""
        from backend.sandbox.singleton import sandbox_manager

        # --- Core tools ---
        try:
            from backend.tools.file_tool import FileTool
            self.agent.file_tool = FileTool(sandbox_manager.filesystem)
            self.agent.register_tool("file", self.agent.file_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register FileTool: {e}")

        try:
            from backend.tools.search_tool import SearchTool
            self.agent.search_tool = SearchTool()
            self.agent.register_tool("search", self.agent.search_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register SearchTool: {e}")

        try:
            from backend.tools.shell_tool import ShellTool
            self.agent.shell_tool = ShellTool(sandbox_manager.executor)
            self.agent.register_tool("shell", self.agent.shell_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register ShellTool: {e}")

        try:
            from backend.tools.browser_tool import BrowserTool
            self.agent.browser_tool = BrowserTool(sandbox_manager.executor)
            self.agent.register_tool("browser", self.agent.browser_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register BrowserTool: {e}")

        try:
            from backend.tools.web_tool import WebTool
            self.agent.web_tool = WebTool()
            self.agent.register_tool("web_read", self.agent.web_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register WebTool: {e}")

        # --- Extended tools ---
        try:
            from backend.agent.tools.pdf_tool import PDFTool
            self.agent.pdf_tool = PDFTool()
            self.agent.register_tool("pdf", self.agent.pdf_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register PDFTool: {e}")

        try:
            from backend.agent.tools.image_gen_tool import ImageGenTool
            self.agent.image_gen_tool = ImageGenTool()
            self.agent.register_tool("image_gen", self.agent.image_gen_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register ImageGenTool: {e}")

        try:
            from backend.agent.tools.github_tool import GithubTool
            self.agent.github_tool = GithubTool()
            self.agent.register_tool("github", self.agent.github_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register GithubTool: {e}")

        try:
            from backend.agent.tools.email_tool import EmailTool
            self.agent.email_tool = EmailTool()
            self.agent.register_tool("email", self.agent.email_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register EmailTool: {e}")

        try:
            from backend.agent.tools.utility_tools import VideoTool, AudioTool, SheetsTool
            self.agent.video_tool = VideoTool()
            self.agent.register_tool("video", self.agent.video_tool.execute)
            self.agent.audio_tool = AudioTool()
            self.agent.register_tool("audio", self.agent.audio_tool.execute)
            self.agent.sheets_tool = SheetsTool()
            self.agent.register_tool("sheets", self.agent.sheets_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register utility tools (Video/Audio/Sheets): {e}")

        try:
            from backend.tools.schedule_tool import ScheduleTool
            self.agent.schedule_tool = ScheduleTool()
            self.agent.register_tool("schedule", self.agent.schedule_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register ScheduleTool: {e}")

        try:
            from backend.tools.trigger_tool import TriggerTool
            self.agent.trigger_tool = TriggerTool()
            self.agent.register_tool("trigger", self.agent.trigger_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register TriggerTool: {e}")

        try:
            from backend.tools.voice_tool import VoiceTool
            self.agent.voice_tool = VoiceTool()
            self.agent.register_tool("voice", self.agent.voice_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register VoiceTool: {e}")

        try:
            from backend.tools.monitor_tool import MonitorTool
            self.agent.monitor_tool = MonitorTool()
            self.agent.register_tool("monitor", self.agent.monitor_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register MonitorTool: {e}")

        try:
            from backend.tools.document_tool import DocumentTool
            self.agent.document_tool = DocumentTool()
            self.agent.register_tool("document", self.agent.document_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register DocumentTool: {e}")

        try:
            from backend.tools.mirofish_tool import MiroFishTool
            self.agent.mirofish_tool = MiroFishTool()
            self.agent.register_tool("mirofish", self.agent.mirofish_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register MiroFishTool: {e}")

        try:
            from backend.tools.ast_tool import ASTTool
            self.agent.ast_tool = ASTTool()
            self.tool_registry.register("ast_navigator", self.agent.ast_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register ASTTool: {e}")

        try:
            from backend.agent.tools.infra_tool import InfraTool
            self.agent.infra_tool = InfraTool()
            self.tool_registry.register("infra", self.agent.infra_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register InfraTool: {e}")

        try:
            from backend.tools.log_analyzer_tool import LogAnalyzerTool
            self.agent.log_analyzer = LogAnalyzerTool()
            self.tool_registry.register("log_analyzer", self.agent.log_analyzer.execute)
        except Exception as e:
            logger.error(f"Failed to register LogAnalyzerTool: {e}")

        try:
            from backend.tools.cosmo_tool import CosmoPresentationTool
            self.agent.cosmo_tool = CosmoPresentationTool()
            self.tool_registry.register("presentation", self.agent.cosmo_tool.execute)
            logger.info("COSMO Presentation tool registered")
        except Exception as e:
            logger.error(f"Failed to register CosmoPresentationTool: {e}")

        try:
            from backend.tools.plan_tool import PlanTool
            from backend.agent.planner import PlanManager
            self.agent.plan_manager = PlanManager(session_id=self.session_id or "default")
            self.agent.plan_tool = PlanTool(plan_manager=self.agent.plan_manager)
            self.agent.register_tool("plan", self.agent.plan_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register PlanTool: {e}")

        try:
            from backend.tools.expose_tool import ExposeTool
            self.agent.expose_tool = ExposeTool(sandbox_manager.executor)
            self.agent.register_tool("expose", self.agent.expose_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register ExposeTool: {e}")

        try:
            from backend.tools.mcp_tool import MCPTool
            self.agent.mcp_tool = MCPTool(self.agent.mcp_client, sync_callback=self.agent.sync_mcp_tools)
            self.agent.register_tool("mcp_connect", self.agent.mcp_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register MCPTool: {e}")

        try:
            from backend.tools.media_tool import MediaTool
            self.agent.media_tool = MediaTool()
            self.agent.register_tool("media", self.agent.media_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register MediaTool: {e}")

        try:
            from backend.tools.repo_map_tool import RepoMapTool
            self.agent.repo_map_tool = RepoMapTool()
            self.tool_registry.register("repo_map", self.agent.repo_map_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register RepoMapTool: {e}")

        try:
            from backend.tools.linter_tool import LinterTool
            self.agent.linter_tool = LinterTool()
            self.tool_registry.register("fast_linter", self.agent.linter_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register LinterTool: {e}")

        try:
            from backend.tools.git_forensics_tool import GitForensicsTool
            self.agent.git_forensics_tool = GitForensicsTool()
            self.tool_registry.register("git_forensics", self.agent.git_forensics_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register GitForensicsTool: {e}")

        try:
            from backend.tools.repl_tool import ReplTool
            self.agent.repl_tool = ReplTool()
            self.tool_registry.register("python_repl", self.agent.repl_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register ReplTool: {e}")

        try:
            from backend.tools.deploy_tool import DeployTool
            self.agent.deploy_tool = DeployTool()
            self.tool_registry.register("deploy", self.agent.deploy_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register DeployTool: {e}")

        # Dummy message handler
        try:
            async def _dummy_message(**kwargs):
                return {"success": True, "output": "Message generated."}
            self.agent.register_tool("message", _dummy_message)
        except Exception as e:
            logger.error(f"Failed to register message handler: {e}")

        try:
            from backend.tools.patch_tool import PatchTool
            self.agent.patch_tool = PatchTool()
            self.agent.register_tool("patch", self.agent.patch_tool.execute)
        except Exception as e:
            logger.error(f"Failed to register PatchTool: {e}")

        logger.info("ToolInitializer: all tools registered")

        # Auto-discover any additional tools
        try:
            new_count = self.tool_registry.auto_discover_tools("backend/tools")
            if new_count > 0:
                logger.info(f"ToolInitializer: auto-discovered {new_count} additional tools")
        except Exception as e:
            logger.debug(f"Auto-discovery skipped: {e}")
