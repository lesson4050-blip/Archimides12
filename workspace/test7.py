from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.post("/echo")
async def echo(request: Request):
    payload = await request.json()
    return payload

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)