from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional, Set
from app.auth import get_current_user
from app.websocket.manager import manager

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    user_id: str = Depends(get_current_user)
):
    """
    WebSocket endpoint for real-time notifications.
    Connects to receive payment updates, split notifications, and settlement alerts.
    """
    connection_id = await manager.connect(websocket, user_id)

    try:
        while True:
            # Wait for incoming messages from client
            data = await websocket.receive_json()

            # Handle different message types from client
            message_type = data.get("type")

            if message_type == "subscribe":
                # Client subscribes to specific notification types
                subscription_types = data.get("types", ["all"])
                # In a more complex system, you'd track subscriptions per user
                # For now, we just acknowledge
                await websocket.send_json({
                    "type": "subscription_ack",
                    "data": {"types": subscription_types}
                })

            elif message_type == "unsubscribe":
                # Client unsubscribes from notification types
                subscription_types = data.get("types", [])
                await websocket.send_json({
                    "type": "unsubscription_ack",
                    "data": {"types": subscription_types}
                })

            elif message_type == "ping":
                # Heartbeat from client
                await websocket.send_json({
                    "type": "pong",
                    "data": {"timestamp": data.get("timestamp")}
                })

            else:
                # Unknown message type
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"Unknown message type: {message_type}"}
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        manager.disconnect(websocket, user_id)


@router.get("/status")
async def get_websocket_status():
    """Get WebSocket connection status."""
    return {
        "active_connections": len(manager.active_connections),
        "users_connected": len(manager.user_connections),
        "connection_details": {
            user_id: len(conns) for user_id, conns in manager.active_connections.items()
        }
    }
