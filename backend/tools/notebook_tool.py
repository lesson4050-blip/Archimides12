"""
Notebook Tool — Jupyter notebook manipulation.
Read, edit cells, insert cells, delete cells in .ipynb files.
"""
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class NotebookTool:
    """Manipulate Jupyter notebooks programmatically."""

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "notebook",
                "description": "Read, edit, insert, or delete cells in Jupyter notebooks (.ipynb).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["read", "edit_cell", "insert_cell", "delete_cell"]},
                        "path": {"type": "string", "description": "Path to the .ipynb file"},
                        "cell_index": {"type": "integer", "description": "0-based cell index"},
                        "content": {"type": "string", "description": "New cell content"},
                        "cell_type": {"type": "string", "enum": ["code", "markdown"], "default": "code"},
                    },
                    "required": ["action", "path"],
                }
            }
        }

    async def execute(self, action: str, path: str, **kwargs) -> Dict[str, Any]:
        if action == "read":
            return await self._read(path)
        elif action == "edit_cell":
            return await self._edit_cell(path, kwargs.get("cell_index", 0), kwargs.get("content", ""))
        elif action == "insert_cell":
            return await self._insert_cell(path, kwargs.get("cell_index", -1), kwargs.get("content", ""), kwargs.get("cell_type", "code"))
        elif action == "delete_cell":
            return await self._delete_cell(path, kwargs.get("cell_index", 0))
        return {"error": f"Unknown action: {action}"}

    async def _read(self, path: str) -> Dict[str, Any]:
        try:
            with open(path) as f:
                nb = json.load(f)
            cells = []
            for i, cell in enumerate(nb.get("cells", [])):
                cells.append({"index": i, "type": cell.get("cell_type", "code"), "source": "".join(cell.get("source", [])), "outputs": len(cell.get("outputs", []))})
            return {"cells": cells, "total_cells": len(cells)}
        except Exception as e:
            return {"error": str(e)}

    async def _edit_cell(self, path: str, index: int, content: str) -> Dict[str, Any]:
        try:
            with open(path) as f:
                nb = json.load(f)
            cells = nb.get("cells", [])
            if index >= len(cells):
                return {"error": f"Cell index {index} out of range (total: {len(cells)})"}
            cells[index]["source"] = content.split("\n")
            with open(path, "w") as f:
                json.dump(nb, f, indent=1)
            return {"success": True, "message": f"Cell {index} updated"}
        except Exception as e:
            return {"error": str(e)}

    async def _insert_cell(self, path: str, index: int, content: str, cell_type: str) -> Dict[str, Any]:
        try:
            with open(path) as f:
                nb = json.load(f)
            new_cell: Dict[str, Any] = {"cell_type": cell_type, "source": content.split("\n"), "metadata": {}}
            if cell_type == "code":
                new_cell["outputs"] = []
                new_cell["execution_count"] = None
            cells = nb.get("cells", [])
            if index < 0:
                cells.append(new_cell)
            else:
                cells.insert(index, new_cell)
            nb["cells"] = cells
            with open(path, "w") as f:
                json.dump(nb, f, indent=1)
            return {"success": True, "message": f"Cell inserted at {index}"}
        except Exception as e:
            return {"error": str(e)}

    async def _delete_cell(self, path: str, index: int) -> Dict[str, Any]:
        try:
            with open(path) as f:
                nb = json.load(f)
            cells = nb.get("cells", [])
            if index >= len(cells):
                return {"error": f"Cell index {index} out of range"}
            removed = cells.pop(index)
            nb["cells"] = cells
            with open(path, "w") as f:
                json.dump(nb, f, indent=1)
            return {"success": True, "removed_type": removed.get("cell_type")}
        except Exception as e:
            return {"error": str(e)}
