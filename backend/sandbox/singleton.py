from backend.sandbox.manager import SandboxManager

# Global singleton for SandboxManager to avoid redundant connections and reloads
sandbox_manager = SandboxManager()
