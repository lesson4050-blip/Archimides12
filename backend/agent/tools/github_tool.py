import os
import logging
from typing import Dict, Any
try:
    from github import Github
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

logger = logging.getLogger(__name__)

class GithubTool:
    """
    Инструмент для работы с репозиториями GitHub.
    Обеспечивает создание репозиториев, коммиты, чтение файлов и поиск.
    """

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "github",
                "description": "Интеграция с GitHub: работа с репозиториями, файлами и поиском.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["get_repo", "search_repos", "get_file", "list_files", "create_repo"],
                            "description": "Действие для выполнения"
                        },
                        "repo_name": {"type": "string", "description": "Полное имя репозитория (owner/repo)"},
                        "path": {"type": "string", "description": "Путь к файлу в репозитории"},
                        "query": {"type": "string", "description": "Поисковый запрос"},
                        "token": {"type": "string", "description": "GitHub Access Token (опционально)"}
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        if not GITHUB_AVAILABLE:
            return {"success": False, "error": "Библиотека PyGithub не установлена. Установите её с помощью 'pip install PyGithub'"}
            
        try:
            token = kwargs.get("token") or os.environ.get("GITHUB_TOKEN")
            g = Github(token) if token else Github()
            
            if action == "get_repo":
                repo_name = kwargs.get("repo_name")
                if not repo_name:
                    return {"success": False, "error": "Имя репозитория не указано"}
                repo = g.get_repo(repo_name)
                return {
                    "success": True,
                    "name": repo.full_name,
                    "description": repo.description,
                    "stars": repo.stargazers_count,
                    "url": repo.html_url
                }
                
            elif action == "search_repos":
                query = kwargs.get("query")
                if not query:
                    return {"success": False, "error": "Запрос не указан"}
                repos = g.search_repositories(query)
                results = []
                for i, repo in enumerate(repos):
                    if i >= 5: break
                    results.append({
                        "name": repo.full_name,
                        "description": repo.description,
                        "url": repo.html_url
                    })
                return {"success": True, "results": results}
                
            elif action == "get_file":
                repo_name = kwargs.get("repo_name")
                path = kwargs.get("path")
                if not repo_name or not path:
                    return {"success": False, "error": "Репозиторий или путь не указаны"}
                repo = g.get_repo(repo_name)
                content = repo.get_contents(path)
                return {
                    "success": True,
                    "content": content.decoded_content.decode('utf-8'),
                    "sha": content.sha
                }
            
            else:
                return {"success": False, "error": f"Неизвестное действие: {action}"}
                
        except Exception as e:
            logger.error(f"Ошибка GithubTool: {e}")
            return {"success": False, "error": str(e)}
