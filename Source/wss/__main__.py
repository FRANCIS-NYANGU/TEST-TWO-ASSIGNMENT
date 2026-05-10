"""
Entry point for the WebSocket live-feed server.

This service is responsible for:
    - Receiving telemetry readings from a shared queue
    - Broadcasting readings to all connected WebSocket clients
    - Providing real-time live sensor updates to dashboards

Integration:
    TCP Server  →  Queue  →  WebSocket Broadcaster  →  Clients
"""

from __future__ import annotations

import asyncio
import json
import os
import websockets

from wss.broadcaster import Broadcaster
from wss.handler import live


# =============================================================
# Background Consumer
# =============================================================
async def reading_consumer(
    broadcaster: Broadcaster,
    queue: asyncio.Queue,
) -> None:
    """
    Continuously consume sensor readings from the shared queue
    and broadcast them to all connected WebSocket clients.
    """

    while True:

        # Wait for next telemetry reading from TCP server
        reading = await queue.get()

        try:
            # Send reading to all connected WebSocket clients
            await broadcaster.publish(reading)

        finally:
            # Mark task as processed
            queue.task_done()


# =============================================================
# Main Entry Point
# =============================================================
async def main() -> None:
    """
    Boot the WebSocket live-feed server.

    Responsibilities:
        1. Create broadcaster (manages WebSocket clients)
        2. Create shared queue (receives TCP readings)
        3. Start background consumer task
        4. Start WebSocket server
        5. Run indefinitely
    """

    # ---------------------------------------------------------
    # Configuration (can be changed via environment variables)
    # ---------------------------------------------------------
    host = os.getenv("WS_HOST", "0.0.0.0")
    port = int(os.getenv("WS_PORT", "8765"))

    # ---------------------------------------------------------
    # Broadcaster handles all connected WebSocket clients
    # ---------------------------------------------------------
    broadcaster = Broadcaster()

    # ---------------------------------------------------------
    # Shared queue for incoming telemetry readings
    #
    # IMPORTANT:
    # TCP server MUST push data into this queue:
    #   await queue.put(reading)
    # ---------------------------------------------------------
    reading_queue: asyncio.Queue = asyncio.Queue(
        maxsize=1000
    )

    # ---------------------------------------------------------
    # Start background consumer task
    #
    # This connects queue → broadcaster pipeline
    # ---------------------------------------------------------
    consumer_task = asyncio.create_task(
        reading_consumer(
            broadcaster,
            reading_queue,
        )
    )

    # =========================================================
    # WebSocket Connection Handler
    # =========================================================
    async def websocket_handler(websocket):

        """
        Handle a new WebSocket client connection.

        Each client:
            - Is registered inside broadcaster
            - Receives live sensor updates
        """

        # Register broadcaster in connection context
        websocket.server.broadcaster = broadcaster

        # Start live streaming session
        await live(websocket, "/live")

    # ---------------------------------------------------------
    # Start WebSocket server
    # ---------------------------------------------------------
    server = await websockets.serve(
        websocket_handler,
        host,
        port,
    )

    print(f"WebSocket server running at ws://{host}:{port}/live")

    # =========================================================
    # Keep server alive
    # =========================================================
    try:
        await asyncio.Future()  # run forever

    finally:
        # Cleanup on shutdown
        consumer_task.cancel()

        server.close()

        await server.wait_closed()


# =============================================================
# Entry point
# =============================================================
if __name__ == "__main__":
    asyncio.run(main())