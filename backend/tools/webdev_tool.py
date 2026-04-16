import logging
from typing import Dict, Any
from backend.sandbox.executor import SandboxExecutor
from backend.sandbox.filesystem import SandboxFilesystem

logger = logging.getLogger(__name__)

class WebDevTool:
    """
    Scaffolds web projects inside the sandbox.
    """
    def __init__(self, executor: SandboxExecutor, filesystem: SandboxFilesystem):
        self.executor = executor
        self.filesystem = filesystem

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "webdev",
                "description": "Tools for web development and project scaffolding.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["init", "install", "run_dev", "create_snake_game"]},
                        "project_name": {"type": "string", "default": "archimedes-app"},
                        "template": {"type": "string", "enum": ["react", "react-ts", "vue", "vue-ts"], "default": "react-ts"},
                        "path": {"type": "string", "description": "Output path for file creation actions"}
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(self, session_id: str, action: str, project_name: str = "archimedes-app", template: str = "react-ts", **kwargs) -> Dict[str, Any]:
        if action == "init":
            # Use npm create vite@latest
            # -- --template [template]
            # Since we want it non-interactive
            cmd = f"npm create vite@latest {project_name} -- --template {template} --yes"
            
            logger.info(f"Scaffolding web project {project_name} for session {session_id}...")
            return await self.executor.run_command(session_id, cmd, timeout=300)
            
        elif action == "install":
            cmd = f"cd {project_name} && npm install"
            return await self.executor.run_command(session_id, cmd, timeout=600)
            
        elif action == "run_dev":
            cmd = f"cd /home/ubuntu/workspace/{project_name} && nohup npm run dev -- --host 0.0.0.0 --port 5173 > /tmp/vite_dev.log 2>&1 &"
            result = await self.executor.run_command(session_id, cmd, timeout=30)
            if result.get("success"):
                return {
                    "success": True,
                    "output": f"Dev server started for '{project_name}' on port 5173. Use expose tool to get public URL. Logs: /tmp/vite_dev.log"
                }
            return result
        
        elif action == "create_snake_game":
            # Generate a self-contained Snake game
            path = kwargs.get("path", "index.html")
            snake_html = """<!DOCTYPE html>
<html>
<head>
    <title>Snake Game</title>
    <style>
        body { display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #222; color: #fff; font-family: Arial, sans-serif; }
        canvas { border: 5px solid #fff; box-shadow: 0 0 20px rgba(0,0,0,0.5); }
        #score { position: absolute; top: 20px; font-size: 24px; }
    </style>
</head>
<body>
    <div id="score">Score: 0</div>
    <canvas id="snakeGame" width="400" height="400"></canvas>
    <script>
        const canvas = document.getElementById('snakeGame');
        const ctx = canvas.getContext('2d');
        const scoreElement = document.getElementById('score');
        const box = 20;
        let score = 0;
        let snake = [{x: 9 * box, y: 10 * box}];
        let food = {x: Math.floor(Math.random() * 19 + 1) * box, y: Math.floor(Math.random() * 19 + 1) * box};
        let d;

        document.addEventListener('keydown', direction);
        function direction(event) {
            if(event.keyCode == 37 && d != 'RIGHT') d = 'LEFT';
            else if(event.keyCode == 38 && d != 'DOWN') d = 'UP';
            else if(event.keyCode == 39 && d != 'LEFT') d = 'RIGHT';
            else if(event.keyCode == 40 && d != 'UP') d = 'DOWN';
        }

        function draw() {
            ctx.fillStyle = '#222';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            for(let i = 0; i < snake.length; i++) {
                ctx.fillStyle = (i == 0) ? 'green' : 'lime';
                ctx.fillRect(snake[i].x, snake[i].y, box, box);
                ctx.strokeStyle = '#222';
                ctx.strokeRect(snake[i].x, snake[i].y, box, box);
            }
            ctx.fillStyle = 'red';
            ctx.fillRect(food.x, food.y, box, box);
            let snakeX = snake[0].x;
            let snakeY = snake[0].y;
            if( d == 'LEFT') snakeX -= box;
            if( d == 'UP') snakeY -= box;
            if( d == 'RIGHT') snakeX += box;
            if( d == 'DOWN') snakeY += box;
            if(snakeX == food.x && snakeY == food.y) {
                score++;
                scoreElement.innerHTML = 'Score: ' + score;
                food = {x: Math.floor(Math.random() * 19 + 1) * box, y: Math.floor(Math.random() * 19 + 1) * box};
            } else {
                snake.pop();
            }
            let newHead = {x: snakeX, y: snakeY};
            if(snakeX < 0 || snakeX >= canvas.width || snakeY < 0 || snakeY >= canvas.height || collision(newHead, snake)) {
                clearInterval(game);
                alert('Game Over! Score: ' + score);
                location.reload();
            }
            snake.unshift(newHead);
        }

        function collision(head, array) {
            for(let i = 0; i < array.length; i++) {
                if(head.x == array[i].x && head.y == array[i].y) return true;
            }
            return false;
        }
        let game = setInterval(draw, 100);
    </script>
</body>
</html>"""
            # Use SandboxFilesystem to write the file safely
            return await self.filesystem.write_file(session_id, path, snake_html)
            
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
