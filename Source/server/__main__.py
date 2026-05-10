"""
Main entry point for the telemetry server system.

This module is responsible for:
    - Initializing database storage
    - Starting the TCP telemetry ingest server
    - Starting the HTTP REST API server
    - Running all services concurrently

System Components:
    1. TCP Server
        Receives telemetry readings from sensors

    2. REST API
        Exposes stored telemetry data over HTTP

    3. SQLite Storage
        Persists sensor readings locally
"""

from __future__ import annotations

# Standard library imports
import asyncio

# aiohttp web framework
from aiohttp import web

# Local application imports
from server.rest import build_app
from server.storage import SQLiteStorage
from server.tcp_ingest import start_tcp_server


async def main() -> None:
    """
    Main asynchronous server startup function.

    Steps:
        1. Initialize SQLite database
        2. Start TCP ingest server
        3. Build HTTP REST API
        4. Start HTTP web server
        5. Keep all services running forever
    """

    # ---------------------------------------------------------
    # Initialize database storage
    # ---------------------------------------------------------
    storage = SQLiteStorage()

    # Create database tables if they do not exist
    await storage.initialize()

    # ---------------------------------------------------------
    # Start TCP telemetry ingest server
    # ---------------------------------------------------------
    # Sensors connect here and push protobuf readings.
    #
    # Compatible with your SensorSimulator client:
    #   host = server host
    #   port = 9000
    # ---------------------------------------------------------
    tcp_server = await start_tcp_server(
        host="0.0.0.0",
        port=9000,
        storage=storage,

        # WebSocket broadcaster can be added later
        broadcaster=None,
    )

    print("TCP telemetry server running on port 9000")

    # ---------------------------------------------------------
    # Build REST API application
    # ---------------------------------------------------------
    # This API will later support:
    #   - Content negotiation
    #   - Cookies
    #   - Sensor data retrieval
    # ---------------------------------------------------------
    app = build_app(storage)

    # ---------------------------------------------------------
    # Configure aiohttp application runner
    # ---------------------------------------------------------
    runner = web.AppRunner(app)

    await runner.setup()

    # ---------------------------------------------------------
    # Start HTTP server
    # ---------------------------------------------------------
    site = web.TCPSite(
        runner,

        # Listen on all network interfaces
        "0.0.0.0",

        # REST API port
        8080,
    )

    await site.start()

    print("REST API running on http://0.0.0.0:8080")

    print("Telemetry server system is fully operational.")

    # ---------------------------------------------------------
    # Keep TCP server running forever
    # ---------------------------------------------------------
    async with tcp_server:

        # Continuously accept sensor connections
        await tcp_server.serve_forever()


# -------------------------------------------------------------
# Program entry point
# -------------------------------------------------------------
if __name__ == "__main__":

    # Start asyncio event loop
    asyncio.run(main())