# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import os
from typing import Dict, List, Optional

import yaml
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

app = FastAPI(title="Novel Translator API Bridge")

# Cấu hình CORS cho React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_PATH = "config/config.yaml"

# Define API key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    expected_api_key = os.getenv("API_KEY")
    if not expected_api_key:
        raise HTTPException(status_code=500, detail="API_KEY environment variable not set on server.")
    if api_key != expected_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Key")
    return api_key

class ConfigUpdate(BaseModel):
    section: str
    data: Dict

@app.get("/config", dependencies=[Depends(get_api_key)])
def get_config():
    if not os.path.exists(CONFIG_PATH):
        raise HTTPException(status_code=404, detail="Config file not found")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@app.post("/config", dependencies=[Depends(get_api_key)])
def update_config(update: ConfigUpdate):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    if update.section in config:
        config[update.section].update(update.data)
    else:
        config[update.section] = update.data
        
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True)
    return {"status": "success"}

# WebSocket để truyền progress
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Chờ nhận tin nhắn hoặc chỉ giữ kết nối mở
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Entry point để chạy server: uvicorn src.api.server:app --reload
