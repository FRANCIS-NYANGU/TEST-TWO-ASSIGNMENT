"""
WebSocket connection handler for /live endpoint.

This module handles:
    - Client connections
    - Optional subscription messages
    - Receiving broadcast updates from Broadcaster
    - Sending real-time sensor data to clients

IMPORTANT DESIGN:
    This works with Broadcaster.publish()
    NOT a per-client queue system
"""

from __future__ import annotations

import asyncio
import json


# =============================================================
# WebSocket Live Handler
# =============================================================
async def live(websocket, path: str) -> None:
    """
    Handle a single WebSocket client connection.

    Protocol:
        Client → Server:
            {"action": "subscribe", "sensors": [...]}

        Server → Client:
            {"sensor_id": ..., "type": ..., "value": ..., "ts": ...}
    """

    # ---------------------------------------------------------
    # Access shared broadcaster from server context
    # ---------------------------------------------------------
    broadcaster = websocket.server.broadcaster

    # ---------------------------------------------------------
    # Subscription filter for this client
    # None = receive all sensors
    # ---------------------------------------------------------
    subscriptions: set[str] | None = None

    # Register client in broadcaster
    await broadcaster.register(websocket)

    print("[WS CONNECTED] Client connected")

    # =========================================================
    # Handle incoming client messages
    # =========================================================
    async def receiver() -> None:
        """
        Listen for subscription messages from client.
        """

        nonlocal subscriptions

        async for message in websocket:

            try:
                payload = json.loads(message)

                action = payload.get("action")

                # -------------------------------------------------
                # Handle subscription request
                # -------------------------------------------------
                if action == "subscribe":

                    sensors = payload.get("sensors", [])

                    subscriptions = set(sensors)

                    # Store subscription in broadcaster
                    await broadcaster.set_subscription(
                        websocket,
                        sensors,
                    )

                    await websocket.send(
                        json.dumps(
                            {
                                "status": "subscribed",
                                "sensors": sensors,
                            }
                        )
                    )

            except Exception as e:

                await websocket.send(
                    json.dumps(
                        {
                            "error": str(e)
                        }
                    )
                )

    # =========================================================
    # Handle disconnect cleanup
    # =========================================================
    try:

        # Run receiver loop (sender handled by broadcaster)
        await receiver()

    finally:

        # Remove client safely
        await broadcaster.unregister(websocket)

        try:
            await websocket.close()
        except Exception:
            pass

        print("[WS DISCONNECTED] Client disconnected")