from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class EchoRequest(BaseModel):
    data: dict

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/echo")
async def echo(request: EchoRequest):
    return request.data