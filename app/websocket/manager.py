from typing import Dict, Set, Optional
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications."""

    def __init__(self):
        # Map user_id to set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map user_id to set of connection_ids (for tracking)
        self.user_connections: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        """Accept a connection and assign a connection ID."""
        await websocket.accept()
        connection_id = f"{user_id}_{len(self.active_connections.get(user_id, []))}_{id(websocket)}"

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
            self.user_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        self.user_connections[user_id].add(connection_id)

        logger.info(f"User {user_id} connected with connection {connection_id}")
        return connection_id

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Remove a connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        if user_id in self.user_connections:
            # Find and remove the connection ID
            for conn_id in self.user_connections[user_id]:
                # This is a simplified check - in production you'd track connections better
                pass
            self.user_connections[user_id].clear()
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        logger.info(f"User {user_id} disconnected")

    async def send_personal_message(self, message: dict, user_id: str) -> None:
        """Send a message to a specific user."""
        if user_id not in self.active_connections:
            logger.warning(f"No active connections for user {user_id}")
            return

        disconnected = set()
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                disconnected.add(connection)

        # Clean up disconnected connections
        for connection in disconnected:
            self.active_connections[user_id].discard(connection)

    async def broadcast(self, message: dict, user_ids: Optional[Set[str]] = None) -> None:
        """Broadcast a message to specific users or all users."""
        targets = user_ids if user_ids else set(self.active_connections.keys())

        disconnected = set()
        for user_id in targets:
            if user_id not in self.active_connections:
                continue

            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
                    disconnected.add(connection)

        # Clean up disconnected connections
        for user_id in targets:
            for connection in disconnected:
                if user_id in self.active_connections:
                    self.active_connections[user_id].discard(connection)

    async def send_payment_update(self, payment_data: dict, user_ids: Optional[Set[str]] = None) -> None:
        """Send payment update notification."""
        message = {
            "type": "payment_update",
            "data": payment_data
        }
        await self.broadcast(message, user_ids)

    async def send_split_notification(self, split_data: dict, user_ids: Optional[Set[str]] = None) -> None:
        """Send split request notification."""
        message = {
            "type": "split_notification",
            "data": split_data
        }
        await self.broadcast(message, user_ids)

    async def send_settlement_alert(self, settlement_data: dict, user_ids: Optional[Set[str]] = None) -> None:
        """Send settlement alert notification."""
        message = {
            "type": "settlement_alert",
            "data": settlement_data
        }
        await self.broadcast(message, user_ids)

    async def send_authorization_update(self, auth_data: dict, user_ids: Optional[Set[str]] = None) -> None:
        """Send authorization update notification."""
        message = {
            "type": "authorization_update",
            "data": auth_data
        }
        await self.broadcast(message, user_ids)

    def get_user_connection_count(self, user_id: str) -> int:
        """Get the number of active connections for a user."""
        return len(self.active_connections.get(user_id, set()))


manager = ConnectionManager()
