"""
WebSocket Broadcaster for real-time telemetry system.

This component is responsible for:
    - Managing connected WebSocket clients
    - Handling per-client sensor subscriptions
    - Broadcasting incoming sensor readings
    - Ensuring slow or broken clients do not block the system

Architecture role:
    TCP Server → Queue → Consumer → Broadcaster → WebSocket Clients
"""

from __future__ import annotations

import asyncio
import json


class Broadcaster:
    """
    Manages all active WebSocket clients and broadcasts sensor data.

    Features:
        - Client registration/unregistration
        - Optional sensor filtering per client
        - Safe concurrent broadcasting
    """

    def __init__(self) -> None:

        # ---------------------------------------------------------
        # Stores active WebSocket connections
        #
        # Format:
        #   websocket -> set(sensor_ids) OR None
        #
        # None means: client receives ALL sensor data
        # ---------------------------------------------------------
        self._clients: dict = {}

        # Lock to prevent race conditions when modifying clients
        self._lock = asyncio.Lock()

    # =========================================================
    # Register Client
    # =========================================================
    async def register(self, websocket) -> None:
        """
        Register a new WebSocket client.

        By default, client receives all sensor readings.
        """

        async with self._lock:
            self._clients[websocket] = None

        print("[BROADCASTER] Client connected")

    # =========================================================
    # Unregister Client
    # =========================================================
    async def unregister(self, websocket) -> None:
        """
        Remove a disconnected WebSocket client.
        """

        async with self._lock:
            self._clients.pop(websocket, None)

        print("[BROADCASTER] Client disconnected")

    # =========================================================
    # Subscription Management
    # =========================================================
    async def set_subscription(self, websocket, sensor_ids) -> None:
        """
        Set sensor filter for a specific client.

        Args:
            websocket:
                Client connection

            sensor_ids:
                List or set of allowed sensor IDs
        """

        async with self._lock:

            if websocket in self._clients:
                self._clients[websocket] = set(sensor_ids)

    # =========================================================
    # Broadcast Reading
    # =========================================================
    async def publish(self, reading) -> None:
        """
        Broadcast a sensor reading to all interested clients.

        Behaviour:
            - Converts reading to JSON
            - Sends to all subscribed clients
            - Removes slow/broken clients automatically
        """

        # ---------------------------------------------------------
        # Convert reading to JSON message
        # ---------------------------------------------------------
        message = json.dumps(
            {
                "sensor_id": reading.get("sensor_id"),
                "type": reading.get("reading_type"),
                "value": reading.get("value"),
                "unit": reading.get("unit"),
                "ts": reading.get("timestamp"),
            }
        )

        # ---------------------------------------------------------
        # Take snapshot of clients (avoid locking during send)
        # ---------------------------------------------------------
        async with self._lock:
            clients_snapshot = list(self._clients.items())

        # =========================================================
        # Send to a single client
        # =========================================================
        async def send_to_client(websocket, subscriptions):
            """
            Send a message to one client safely.
            """

            sensor_id = reading.get("sensor_id")

            # -----------------------------------------------------
            # Apply subscription filter (if any)
            # -----------------------------------------------------
            if subscriptions is not None:

                if sensor_id not in subscriptions:
                    return

            try:
                # Timeout prevents slow clients blocking system
                await asyncio.wait_for(
                    websocket.send(message),
                    timeout=2.0,
                )

            except Exception:

                # -------------------------------------------------
                # Remove broken or slow client
                # -------------------------------------------------
                await self.unregister(websocket)

                try:
                    await websocket.close()
                except Exception:
                    pass

        # ---------------------------------------------------------
        # Broadcast concurrently to all clients
        # ---------------------------------------------------------
        await asyncio.gather(
            *[
                send_to_client(ws, subs)
                for ws, subs in clients_snapshot
            ],
            return_exceptions=True,
        )