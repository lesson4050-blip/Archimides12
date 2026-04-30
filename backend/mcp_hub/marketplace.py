"""
MCP Marketplace Catalog.
"""
MCP_CATALOG = {
    "fetch": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-fetch"]
    },
    "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/ubuntu/workspace"]
    },
    "memory": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "brave-search": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-brave-search"]
    },
    "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"]
    },
    "postgres": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/postgres"]
    },
    "sqlite": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sqlite", "/home/ubuntu/workspace/mcp.db"]
    },
    "puppeteer": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"]
    },
    "slack": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-slack"]
    },
    "gmail": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-gmail"]
    },
    # ── Community servers ──
    "docker": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-docker"],
        "description": "Docker management — containers, images, volumes",
        "category": "infrastructure",
    },
    "redis": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-redis"],
        "description": "Redis — cache, pub/sub, data structures",
        "category": "database",
    },
    "google-drive": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-google-drive"],
        "description": "Google Drive — files, folders, sharing",
        "category": "storage",
    },
    "notion": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-notion"],
        "description": "Notion API — pages, databases, blocks",
        "category": "productivity",
        "env_required": ["NOTION_API_KEY"],
    },
    "linear": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-linear"],
        "description": "Linear — issues, projects, teams",
        "category": "project-management",
        "env_required": ["LINEAR_API_KEY"],
    },
    "sentry": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sentry"],
        "description": "Sentry — error tracking and monitoring",
        "category": "monitoring",
        "env_required": ["SENTRY_AUTH_TOKEN"],
    },
}

def search_catalog(query: str = "", category: str = "") -> list:
    """Search MCP catalog by name or category."""
    results = []
    for name, config in MCP_CATALOG.items():
        if query and query.lower() not in name and query.lower() not in config.get("description", "").lower():
            continue
        if category and config.get("category", "") != category:
            continue
        results.append({
            "name": name,
            "description": config.get("description", ""),
            "category": config.get("category", ""),
            "requires_env": config.get("env_required", []),
        })
    return results

def get_categories() -> list:
    return sorted(set(c.get("category", "") for c in MCP_CATALOG.values() if c.get("category")))
