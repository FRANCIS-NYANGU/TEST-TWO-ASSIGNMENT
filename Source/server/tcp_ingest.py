"""
Asynchronous TCP telemetry ingest server.

This module is responsible for:
    - Accepting sensor TCP connections
    - Receiving framed protobuf messages
    - Decoding telemetry readings
    - Storing readings in the database
    - Broadcasting live updates (optional)

Compatible with:
    ✅ SensorSimulator client
    ✅ Protocol Buffers framing
    ✅ Asyncio networking

Communication Flow:
    Sensor -> TCP Server -> Database -> REST API/WebSocket
"""

from __future__ import annotations

# Standard library imports
import asyncio
import struct

# Generated protobuf classes
from proto import telemetry_pb2


# =============================================================
# Handle Single Sensor Connection
# =============================================================
async def handle_sensor(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    """
    Handle one connected sensor.

    Responsibilities:
        - Read incoming telemetry frames
        - Decode protobuf messages
        - Validate message sizes
        - Save readings to storage
        - Broadcast readings to live clients
    """

    # ---------------------------------------------------------
    # Get remote client address
    # ---------------------------------------------------------
    address = writer.get_extra_info("peername")

    print(f"[CONNECTED] Sensor {address}")

    # ---------------------------------------------------------
    # Access shared services attached to server
    # ---------------------------------------------------------
    storage = writer.transport._server.storage
    broadcaster = writer.transport._server.broadcaster

    try:

        # Keep processing messages until disconnect
        while True:

            try:
                # -------------------------------------------------
                # Read frame header
                #
                # Frame format:
                #   [4-byte payload size][protobuf payload]
                # -------------------------------------------------
                header = await reader.readexactly(4)

                # Convert header bytes into integer length
                message_length = struct.unpack(
                    "!I",
                    header
                )[0]

                # -------------------------------------------------
                # Validate payload size
                #
                # Protects server from malformed or huge frames
                # -------------------------------------------------
                if message_length <= 0 or message_length > 10_000:

                    raise ValueError(
                        f"Invalid message length: {message_length}"
                    )

                # -------------------------------------------------
                # Read protobuf payload
                # -------------------------------------------------
                payload = await reader.readexactly(
                    message_length
                )

                # -------------------------------------------------
                # Decode protobuf message
                # -------------------------------------------------
                reading = telemetry_pb2.Reading()

                reading.ParseFromString(payload)

                # -------------------------------------------------
                # Convert protobuf object into Python dictionary
                # -------------------------------------------------
                reading_data = {
                    "sensor_id": reading.sensor_id,
                    "reading_type": reading.reading_type,
                    "value": reading.value,
                    "unit": reading.unit,
                    "timestamp": reading.timestamp,
                }

                # Display received telemetry
                print(
                    f"[RECEIVED] "
                    f"{reading.sensor_id} | "
                    f"{reading.reading_type} | "
                    f"{reading.value} {reading.unit}"
                )

                # -------------------------------------------------
                # Store reading in database
                # -------------------------------------------------
                if storage is not None:

                    await storage.add_reading(reading_data)

                # -------------------------------------------------
                # Broadcast reading to live WebSocket clients
                # -------------------------------------------------
                if broadcaster is not None:

                    await broadcaster.broadcast(reading_data)

            # -----------------------------------------------------
            # Sensor disconnected normally
            # -----------------------------------------------------
            except asyncio.IncompleteReadError:

                print(f"[DISCONNECTED] {address}")

                break

            # -----------------------------------------------------
            # Malformed frame or protobuf decoding issue
            # -----------------------------------------------------
            except Exception as e:

                print(f"[MALFORMED MESSAGE] {e}")

                # Continue listening for next message
                continue

    finally:
        # ---------------------------------------------------------
        # Close TCP connection cleanly
        # ---------------------------------------------------------
        writer.close()

        await writer.wait_closed()

        print(f"[CLOSED] Connection with {address}")


# =============================================================
# Start TCP Server
# =============================================================
async def start_tcp_server(
    host: str,
    port: int,
    storage,
    broadcaster,
) -> asyncio.AbstractServer:
    """
    Start the asynchronous TCP ingest server.

    Args:
        host:
            IP address to bind server

        port:
            TCP listening port

        storage:
            Shared database storage object

        broadcaster:
            Optional WebSocket broadcaster

    Returns:
        Running asyncio TCP server
    """

    # ---------------------------------------------------------
    # Create asyncio TCP server
    # ---------------------------------------------------------
    server = await asyncio.start_server(
        handle_sensor,
        host,
        port,
    )

    # ---------------------------------------------------------
    # Attach shared services to server object
    #
    # These become accessible inside handle_sensor()
    # ---------------------------------------------------------
    server.storage = storage
    server.broadcaster = broadcaster

    print(f"TCP server listening on {host}:{port}")

    return server