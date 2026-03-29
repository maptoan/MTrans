# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import os
from typing import Dict, List, Optional

import yaml
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
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

class ConfigUpdate(BaseModel):
    """
    Pydantic model for updating configuration sections.

    Attributes:
        section (str): The name of the configuration section to update (e.g., "translation_settings").
        data (Dict): A dictionary containing the key-value pairs to update within that section.
    """
    section: str
    data: Dict

@app.get("/config")
def get_config():
    """
    Retrieves the current application configuration from config/config.yaml.

    Raises:
        HTTPException: If the config file is not found (status_code=404).

    Returns:
        Dict: The loaded configuration as a dictionary.
    """
    if not os.path.exists(CONFIG_PATH):
        raise HTTPException(status_code=404, detail="Config file not found")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@app.post("/config")
def update_config(update: ConfigUpdate):
    """
    Updates a specific section of the application configuration.

    If the section exists, its data is updated. If the section does not exist,
    it is created. The updated configuration is then saved back to config/config.yaml.

    Args:
        update (ConfigUpdate): An object containing the section to update and the data.

    Returns:
        Dict: A status message indicating success.
    """
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
    """
    Manages active WebSocket connections for broadcasting progress updates.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        Establishes a new WebSocket connection and adds it to the active connections.

        Args:
            websocket (WebSocket): The WebSocket object for the new connection.
        """
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """
        Removes a WebSocket connection from the active connections.

        Args:
            websocket (WebSocket): The WebSocket object to disconnect.
        """
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """
        Broadcasts a message to all active WebSocket connections.

        Args:
            message (str): The message to be sent to all connected clients.
        """
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time progress updates.

    Clients can connect to this endpoint to receive broadcast messages
    about the application's progress (e.g., translation status).

    Args:
        websocket (WebSocket): The incoming WebSocket connection.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Chờ nhận tin nhắn hoặc chỉ giữ kết nối mở
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Entry point để chạy server: uvicorn src.api.server:app --reload
