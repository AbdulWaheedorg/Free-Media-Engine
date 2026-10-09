"""Free Media Engine (FME) — WebSocket Bridge Server.

Hosts the local WebSocket server that the browser extension connects to.
Proxies RPC envelopes, tracks session health, and passes messages to FlowClient.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional
import websockets
from websockets.server import WebSocketServerProtocol

from fme_engine.core.config import settings
from fme_engine.services.flow_client import get_flow_client

logger = logging.getLogger(__name__)

_CALLBACK_SECRET = "fme_internal_secret_" + str(int(time.time()))


class WebSocketBridge:
    def __init__(self):
        self.server = None
        self.active_extension: Optional[WebSocketServerProtocol] = None
        self.extension_meta: Dict[str, Any] = {}
        self.last_heartbeat: float = 0.0
        self.connected_at: Optional[float] = None

    @property
    def is_connected(self) -> bool:
        if self.active_extension is None:
            return False
        if hasattr(self.active_extension, "closed"):
            return not self.active_extension.closed
        if hasattr(self.active_extension, "state"):
            return getattr(self.active_extension.state, "name", "") == "OPEN"
        if hasattr(self.active_extension, "open"):
            return bool(self.active_extension.open)
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self.is_connected,
            "connected_at": self.connected_at,
            "last_heartbeat": self.last_heartbeat,
            "extension_meta": self.extension_meta,
            "port": settings.FME_WS_PORT,
        }

    async def ws_handler(self, websocket: WebSocketServerProtocol) -> None:
        client = get_flow_client()
        client.set_extension(websocket)
        self.active_extension = websocket
        self.connected_at = time.time()
        self.last_heartbeat = time.time()
        logger.info("[WS Bridge] Extension connected from %s", websocket.remote_address)

        # Send callback secret so extension can authenticate local callbacks
        try:
            await websocket.send(json.dumps({"type": "callback_secret", "secret": _CALLBACK_SECRET}))
        except Exception:
            pass

        try:
            async for raw in websocket:
                self.last_heartbeat = time.time()
                try:
                    data = json.loads(raw)
                    msg_type = data.get("type")
                    if msg_type == "extension_ready":
                        self.extension_meta = {
                            "version": data.get("extensionVersion"),
                            "flowKeyPresent": data.get("flowKeyPresent"),
                            "tokenAge": data.get("tokenAge"),
                        }
                        logger.info("[WS Bridge] Extension ready: %s", self.extension_meta)

                    await client.handle_message(data, websocket)
                except json.JSONDecodeError:
                    logger.warning("[WS Bridge] Received non-JSON message")
                except Exception as e:
                    logger.exception("[WS Bridge] Error handling extension payload: %s", e)
        except websockets.ConnectionClosed:
            logger.info("[WS Bridge] Extension connection closed")
        finally:
            client.clear_extension(websocket)
            if self.active_extension == websocket:
                self.active_extension = None
            logger.info("[WS Bridge] Extension disconnected")

    async def start(self) -> None:
        """Start WebSocket bridge server listening for browser extension."""
        logger.info(
            "[WS Bridge] Starting WebSocket server on ws://%s:%d",
            settings.FME_WS_HOST,
            settings.FME_WS_PORT,
        )
        self.server = await websockets.serve(
            self.ws_handler,
            settings.FME_WS_HOST,
            settings.FME_WS_PORT,
        )

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
            logger.info("[WS Bridge] WebSocket server stopped")


# Global bridge singleton
ws_bridge = WebSocketBridge()
