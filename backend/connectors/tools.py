"""
ConnectorTools: real actions agents can perform using connected services.
Each method calls the actual service API via Nango proxy.
"""
import base64
import logging
from typing import Dict, Any, List
from backend.connectors.service import nango

logger = logging.getLogger(__name__)


class GitHubTools:
    def __init__(self, connection_id: str):
        self.cid = connection_id
        self.integration = "github"

    async def _api(self, method: str, path: str, data=None, params=None):
        return await nango.make_proxy_request(
            self.integration, self.cid, method, path, data, params
        )

    async def list_repos(self) -> Dict:
        return await self._api("GET", "user/repos",
                               params={"per_page": 50, "sort": "updated"})

    async def read_file(self, repo: str, path: str, ref: str = "main") -> Dict:
        r = await self._api("GET", f"repos/{repo}/contents/{path}",
                            params={"ref": ref})
        if r.get("success") and r["data"].get("content"):
            content = base64.b64decode(r["data"]["content"]).decode("utf-8")
            r["data"]["decoded_content"] = content
        return r

    async def create_file(self, repo: str, path: str,
                          content: str, message: str) -> Dict:
        encoded = base64.b64encode(content.encode()).decode()
        return await self._api("PUT", f"repos/{repo}/contents/{path}", {
            "message": message, "content": encoded
        })

    async def update_file(self, repo: str, path: str, content: str,
                          message: str, sha: str) -> Dict:
        encoded = base64.b64encode(content.encode()).decode()
        return await self._api("PUT", f"repos/{repo}/contents/{path}", {
            "message": message, "content": encoded, "sha": sha
        })

    async def list_issues(self, repo: str) -> Dict:
        return await self._api("GET", f"repos/{repo}/issues",
                               params={"state": "open", "per_page": 30})

    async def create_issue(self, repo: str, title: str,
                           body: str, labels: List[str] = None) -> Dict:
        return await self._api("POST", f"repos/{repo}/issues", {
            "title": title, "body": body, "labels": labels or []
        })

    async def list_prs(self, repo: str) -> Dict:
        return await self._api("GET", f"repos/{repo}/pulls",
                               params={"state": "open"})

    async def create_pr(self, repo: str, title: str, head: str,
                        base: str, body: str = "") -> Dict:
        return await self._api("POST", f"repos/{repo}/pulls", {
            "title": title, "head": head, "base": base, "body": body
        })

    async def create_branch(self, repo: str, branch: str, sha: str) -> Dict:
        return await self._api("POST", f"repos/{repo}/git/refs", {
            "ref": f"refs/heads/{branch}", "sha": sha
        })

    async def search_code(self, query: str) -> Dict:
        return await self._api("GET", "search/code",
                               params={"q": query, "per_page": 10})


class GmailTools:
    def __init__(self, connection_id: str):
        self.cid = connection_id
        self.integration = "google-mail"

    async def _api(self, method: str, path: str, data=None, params=None):
        return await nango.make_proxy_request(
            self.integration, self.cid, method, path, data, params
        )

    async def list_emails(self, max_results: int = 20,
                          query: str = "") -> Dict:
        params = {"maxResults": max_results}
        if query:
            params["q"] = query
        return await self._api("GET",
                               "gmail/v1/users/me/messages", params=params)

    async def get_email(self, message_id: str) -> Dict:
        return await self._api("GET",
                               f"gmail/v1/users/me/messages/{message_id}",
                               params={"format": "full"})

    async def send_email(self, to: str, subject: str,
                         body: str, html: bool = False) -> Dict:
        content_type = "text/html" if html else "text/plain"
        raw = (
            f"To: {to}\r\n"
            f"Subject: {subject}\r\n"
            f"Content-Type: {content_type}; charset=utf-8\r\n\r\n"
            f"{body}"
        )
        encoded = base64.urlsafe_b64encode(raw.encode()).decode()
        return await self._api("POST",
                               "gmail/v1/users/me/messages/send",
                               {"raw": encoded})

    async def search_emails(self, query: str) -> Dict:
        return await self._api("GET",
                               "gmail/v1/users/me/messages",
                               params={"q": query, "maxResults": 20})

    async def mark_read(self, message_id: str) -> Dict:
        return await self._api(
            "POST",
            f"gmail/v1/users/me/messages/{message_id}/modify",
            {"removeLabelIds": ["UNREAD"]}
        )


class SlackTools:
    def __init__(self, connection_id: str):
        self.cid = connection_id
        self.integration = "slack"

    async def _api(self, method: str, path: str, data=None, params=None):
        return await nango.make_proxy_request(
            self.integration, self.cid, method, path, data, params
        )

    async def send_message(self, channel: str, text: str,
                           blocks=None) -> Dict:
        payload = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks
        return await self._api("POST", "chat.postMessage", payload)

    async def list_channels(self) -> Dict:
        return await self._api("GET", "conversations.list",
                               params={"limit": 100})

    async def read_channel(self, channel: str,
                           limit: int = 50) -> Dict:
        return await self._api("GET", "conversations.history",
                               params={"channel": channel, "limit": limit})

    async def upload_file(self, channel: str, filename: str,
                          content: str) -> Dict:
        return await self._api("POST", "files.upload", {
            "channels": channel,
            "filename": filename,
            "content": content
        })


class NotionTools:
    def __init__(self, connection_id: str):
        self.cid = connection_id
        self.integration = "notion"

    async def _api(self, method: str, path: str, data=None, params=None):
        return await nango.make_proxy_request(
            self.integration, self.cid, method, path, data, params
        )

    async def search(self, query: str) -> Dict:
        return await self._api("POST", "search",
                               {"query": query, "page_size": 20})

    async def read_page(self, page_id: str) -> Dict:
        return await self._api("GET", f"pages/{page_id}")

    async def create_page(self, parent_id: str, title: str,
                          content: str = "") -> Dict:
        return await self._api("POST", "pages", {
            "parent": {"page_id": parent_id},
            "properties": {
                "title": {"title": [{"text": {"content": title}}]}
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": content}}]
                    }
                }
            ] if content else []
        })

    async def query_database(self, db_id: str,
                             filter_obj: Dict = None) -> Dict:
        body = {"page_size": 50}
        if filter_obj:
            body["filter"] = filter_obj
        return await self._api("POST", f"databases/{db_id}/query", body)


class StripeTools:
    def __init__(self, connection_id: str):
        self.cid = connection_id
        self.integration = "stripe"

    async def _api(self, method: str, path: str, data=None, params=None):
        return await nango.make_proxy_request(
            self.integration, self.cid, method, path, data, params
        )

    async def list_customers(self, limit: int = 20) -> Dict:
        return await self._api("GET", "v1/customers",
                               params={"limit": limit})

    async def list_payments(self, limit: int = 20) -> Dict:
        return await self._api("GET", "v1/payment_intents",
                               params={"limit": limit})

    async def get_balance(self) -> Dict:
        return await self._api("GET", "v1/balance")

    async def create_payment_link(self, price_id: str,
                                  quantity: int = 1) -> Dict:
        return await self._api("POST", "v1/payment_links", {
            "line_items": [{"price": price_id, "quantity": quantity}]
        })

    async def list_subscriptions(self) -> Dict:
        return await self._api("GET", "v1/subscriptions",
                               params={"limit": 50})


# Tool factory — returns the right tool class for a service
TOOL_CLASSES = {
    "github": GitHubTools,
    "google-mail": GmailTools,
    "slack": SlackTools,
    "notion": NotionTools,
    "stripe": StripeTools,
}


def get_tools(integration: str, connection_id: str):
    """Get tool instance for a connected service."""
    cls = TOOL_CLASSES.get(integration)
    if not cls:
        return None
    return cls(connection_id)
