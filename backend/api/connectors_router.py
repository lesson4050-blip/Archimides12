from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.auth.dependencies import get_current_user
import json, os, logging, datetime

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])
logger = logging.getLogger(__name__)

CONNECTORS_FILE = "data/connectors.json"


def _load() -> Dict:
    os.makedirs("data", exist_ok=True)
    if os.path.exists(CONNECTORS_FILE):
        try:
            with open(CONNECTORS_FILE) as f:
                return json.load(f)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Blind exception caught: {e}")
    return {"apps": {}, "api_keys": {}, "mcp_servers": {}}


def _save(data: Dict):
    os.makedirs("data", exist_ok=True)
    with open(CONNECTORS_FILE, "w") as f:
        json.dump(data, f, indent=2)


APPS_CATALOG = {
    "github": {
        "name": "GitHub", "icon": "🐙", "category": "dev",
        "description": "Repos, issues, PRs, code",
        "auth_type": "token", "env_key": "GITHUB_TOKEN",
        "docs": "https://github.com/settings/tokens"
    },
    "gmail": {
        "name": "Gmail", "icon": "📧", "category": "communication",
        "description": "Read and send emails",
        "auth_type": "oauth", "env_key": "GMAIL_TOKEN",
        "docs": "https://developers.google.com/gmail"
    },
    "slack": {
        "name": "Slack", "icon": "💬", "category": "communication",
        "description": "Messages and channels",
        "auth_type": "token", "env_key": "SLACK_BOT_TOKEN",
        "docs": "https://api.slack.com/apps"
    },
    "notion": {
        "name": "Notion", "icon": "📝", "category": "productivity",
        "description": "Pages and databases",
        "auth_type": "token", "env_key": "NOTION_TOKEN",
        "docs": "https://developers.notion.com"
    },
    "stripe": {
        "name": "Stripe", "icon": "💳", "category": "finance",
        "description": "Payments and billing",
        "auth_type": "token", "env_key": "STRIPE_SECRET_KEY",
        "docs": "https://dashboard.stripe.com/apikeys"
    },
    "supabase": {
        "name": "Supabase", "icon": "⚡", "category": "dev",
        "description": "Database and auth",
        "auth_type": "token", "env_key": "SUPABASE_KEY",
        "docs": "https://app.supabase.com"
    },
    "vercel": {
        "name": "Vercel", "icon": "▲", "category": "dev",
        "description": "Deploy and manage",
        "auth_type": "token", "env_key": "VERCEL_TOKEN",
        "docs": "https://vercel.com/account/tokens"
    },
    "telegram": {
        "name": "Telegram", "icon": "✈️", "category": "communication",
        "description": "Bot messages",
        "auth_type": "token", "env_key": "TELEGRAM_BOT_TOKEN",
        "docs": "https://t.me/BotFather"
    },
    "airtable": {
        "name": "Airtable", "icon": "🟦", "category": "productivity",
        "description": "Spreadsheet database",
        "auth_type": "token", "env_key": "AIRTABLE_TOKEN",
        "docs": "https://airtable.com/account"
    },
    "hubspot": {
        "name": "HubSpot", "icon": "🔶", "category": "sales",
        "description": "CRM and contacts",
        "auth_type": "token", "env_key": "HUBSPOT_TOKEN",
        "docs": "https://developers.hubspot.com"
    },
}

AI_PROVIDERS = {
    "openai": {
        "name": "OpenAI", "icon": "🤖",
        "description": "GPT-4o, Whisper, DALL-E",
        "env_key": "OPENAI_API_KEY",
        "docs": "https://platform.openai.com/api-keys"
    },
    "anthropic": {
        "name": "Anthropic", "icon": "🧠",
        "description": "Claude 4",
        "env_key": "ANTHROPIC_API_KEY",
        "docs": "https://console.anthropic.com"
    },
    "groq": {
        "name": "Groq", "icon": "⚡",
        "description": "Ultra-fast Llama",
        "env_key": "GROQ_API_KEY",
        "docs": "https://console.groq.com/keys"
    },
    "gemini": {
        "name": "Google Gemini", "icon": "✨",
        "description": "Gemini 2.5 Flash/Pro",
        "env_key": "GOOGLE_API_KEY",
        "docs": "https://aistudio.google.com/apikey"
    },
    "tavily": {
        "name": "Tavily", "icon": "🔍",
        "description": "AI web search",
        "env_key": "TAVILY_API_KEY",
        "docs": "https://app.tavily.com"
    },
    "elevenlabs": {
        "name": "ElevenLabs", "icon": "🎙️",
        "description": "Text-to-speech",
        "env_key": "ELEVENLABS_API_KEY",
        "docs": "https://elevenlabs.io"
    },
    "pexels": {
        "name": "Pexels", "icon": "📸",
        "description": "Free stock images for presentations",
        "env_key": "PEXELS_API_KEY",
        "docs": "https://www.pexels.com/api"
    },
}


@router.get("/catalog")
async def get_catalog(user: dict = Depends(get_current_user)):
    data = _load()
    connected_apps = data.get("apps", {})
    connected_keys = data.get("api_keys", {})
    
    services = {}
    for k, v in APPS_CATALOG.items():
        services[k] = {
            **v,
            "connected": k in connected_apps,
            "capabilities": v.get("capabilities", ["read", "write"]),
            "nango_key": v.get("nango_key", f"{k}-auth")
        }
    
    for k, v in AI_PROVIDERS.items():
        services[k] = {
            **v,
            "category": "ai",
            "auth_type": "token",
            "connected": k in connected_keys,
            "capabilities": v.get("capabilities", ["generate", "analyze"]),
            "nango_key": ""
        }
        
    categories = {
        "dev": {"name": "Developer Tools", "icon": "🛠️"},
        "communication": {"name": "Communication", "icon": "💬"},
        "productivity": {"name": "Productivity", "icon": "📝"},
        "finance": {"name": "Finance", "icon": "💳"},
        "sales": {"name": "Sales & CRM", "icon": "🔶"},
        "ai": {"name": "AI Models", "icon": "🧠"},
    }

    return {
        "services": services,
        "categories": categories,
        "mcp_servers": data.get("mcp_servers", {})
    }


class AppConnectRequest(BaseModel):
    app_id: str
    token: str


@router.post("/apps/connect")
async def connect_app(
    req: AppConnectRequest,
    user: dict = Depends(get_current_user)
):
    if req.app_id not in APPS_CATALOG:
        raise HTTPException(404, "App not found")
    app_info = APPS_CATALOG[req.app_id]
    _write_env_key(app_info["env_key"], req.token)
    data = _load()
    data["apps"][req.app_id] = {
        "connected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "env_key": app_info["env_key"]
    }
    _save(data)
    return {"success": True, "message": f"{app_info['name']} connected"}


@router.delete("/apps/{app_id}")
async def disconnect_app(
    app_id: str, user: dict = Depends(get_current_user)
):
    data = _load()
    if app_id in data.get("apps", {}):
        env_key = APPS_CATALOG.get(app_id, {}).get("env_key", "")
        _remove_env_key(env_key)
        del data["apps"][app_id]
        _save(data)
    return {"success": True}


class APIKeyRequest(BaseModel):
    provider_id: str
    api_key: str


@router.post("/api-keys")
async def save_api_key(
    req: APIKeyRequest,
    user: dict = Depends(get_current_user)
):
    if req.provider_id not in AI_PROVIDERS:
        raise HTTPException(404, "Provider not found")
    provider = AI_PROVIDERS[req.provider_id]
    _write_env_key(provider["env_key"], req.api_key)
    data = _load()
    data["api_keys"][req.provider_id] = {
        "connected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "env_key": provider["env_key"],
        "masked": "***" + req.api_key[-4:] if len(req.api_key) > 4 else "***"
    }
    _save(data)
    return {"success": True, "message": f"{provider['name']} key saved"}


@router.delete("/api-keys/{provider_id}")
async def remove_api_key(
    provider_id: str, user: dict = Depends(get_current_user)
):
    data = _load()
    if provider_id in data.get("api_keys", {}):
        env_key = AI_PROVIDERS.get(provider_id, {}).get("env_key", "")
        _remove_env_key(env_key)
        del data["api_keys"][provider_id]
        _save(data)
    return {"success": True}


class MCPServerRequest(BaseModel):
    name: str
    command: str
    args: Optional[List[str]] = []
    description: Optional[str] = ""


@router.post("/mcp")
async def add_mcp_server(
    req: MCPServerRequest,
    user: dict = Depends(get_current_user)
):
    data = _load()
    data["mcp_servers"][req.name] = {
        "command": req.command, "args": req.args,
        "description": req.description,
        "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    _save(data)
    return {"success": True}


@router.delete("/mcp/{server_name}")
async def remove_mcp_server(
    server_name: str, user: dict = Depends(get_current_user)
):
    data = _load()
    if server_name in data.get("mcp_servers", {}):
        del data["mcp_servers"][server_name]
        _save(data)
    return {"success": True}


@router.get("/status")
async def get_status(user: dict = Depends(get_current_user)):
    data = _load()
    return {
        "apps_connected": len(data.get("apps", {})),
        "api_keys_connected": len(data.get("api_keys", {})),
        "mcp_servers": len(data.get("mcp_servers", {}))
    }


def _write_env_key(key: str, value: str):
    env_path = ".env"
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"{key}={value}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)
    os.environ[key] = value


def _remove_env_key(key: str):
    if not key:
        return
    env_path = ".env"
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        lines = [l for l in f if not l.startswith(f"{key}=")]
    with open(env_path, "w") as f:
        f.writelines(lines)
    os.environ.pop(key, None)
