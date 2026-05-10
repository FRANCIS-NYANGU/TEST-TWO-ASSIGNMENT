"""
Single sensor simulation module.

This module contains the SensorSimulator class which:
    - Connects to the telemetry server
    - Generates fake sensor readings
    - Serializes readings using Protocol Buffers
    - Sends data continuously over TCP
    - Automatically reconnects if connection fails
"""

from __future__ import annotations

# Standard library imports
import asyncio
import random
import struct
import time

# Generated protobuf classes
from proto import telemetry_pb2


class SensorSimulator:
    """
    Simulates a single IoT sensor device.

    Each simulator:
        - Creates fake readings
        - Connects to the server
        - Sends readings repeatedly at fixed intervals
    """

    def __init__(
        self,
        sensor_id: str,
        sensor_type: str,
        interval_seconds: float,
        host: str,
        port: int,
    ) -> None:
        """
        Initialize a sensor simulator.

        Args:
            sensor_id:
                Unique sensor identifier

            sensor_type:
                Type of sensor
                Example: temperature, humidity, light

            interval_seconds:
                Time delay between readings

            host:
                Telemetry server IP/hostname

            port:
                Telemetry server TCP port
        """

        # Store sensor information
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type

        # Frequency for sending readings
        self.interval_seconds = interval_seconds

        # Server connection details
        self.host = host
        self.port = port

    async def run(self) -> None:
        """
        Main sensor loop.

        Behaviour:
            1. Connect to telemetry server
            2. Generate sensor readings
            3. Serialize readings using protobuf
            4. Send readings continuously
            5. Reconnect automatically on failure
        """

        # Delay before reconnecting after failure
        backoff = 3

        # Keep running forever
        while True:

            try:
                print(f"[{self.sensor_id}] Connecting to server...")

                # Open TCP connection to telemetry server
                reader, writer = await asyncio.open_connection(
                    self.host,
                    self.port
                )

                print(f"[{self.sensor_id}] Connected successfully.")

                # Send readings forever while connected
                while True:

                    # Generate fake sensor reading
                    reading = self._generate_reading()

                    # -------------------------------------------------
                    # Serialize protobuf message into bytes
                    # -------------------------------------------------
                    payload = reading.SerializeToString()

                    # -------------------------------------------------
                    # Create framed message
                    #
                    # Frame format:
                    #   [4-byte payload length][protobuf payload]
                    # -------------------------------------------------
                    frame = struct.pack("!I", len(payload)) + payload

                    # Send frame to server
                    writer.write(frame)

                    # Ensure data is fully transmitted
                    await writer.drain()

                    # Display sent reading
                    print(
                        f"[{self.sensor_id}] "
                        f"Sent {reading.reading_type} "
                        f"= {reading.value} {reading.unit}"
                    )

                    # Wait before sending next reading
                    await asyncio.sleep(self.interval_seconds)

            except Exception as e:

                # Connection failure or server unavailable
                print(f"[{self.sensor_id}] Connection error: {e}")

                print(
                    f"[{self.sensor_id}] "
                    f"Retrying connection in {backoff} seconds..."
                )

                # Wait before reconnecting
                await asyncio.sleep(backoff)

    def _generate_reading(self):
        """
        Generate a realistic fake sensor reading.

        Returns:
            telemetry_pb2.Reading protobuf object
        """

        # Create protobuf reading object
        reading = telemetry_pb2.Reading()

        # Common metadata
        reading.sensor_id = self.sensor_id
        reading.reading_type = self.sensor_type

        # Current UNIX timestamp
        reading.timestamp = int(time.time())

        # ---------------------------------------------------------
        # Generate value based on sensor type
        # ---------------------------------------------------------

        if self.sensor_type == "temperature":

            # Temperature range: 18°C to 35°C
            reading.value = round(random.uniform(18, 35), 2)
            reading.unit = "C"

        elif self.sensor_type == "humidity":

            # Humidity range: 40% to 90%
            reading.value = round(random.uniform(40, 90), 2)
            reading.unit = "%"

        elif self.sensor_type == "soil_moisture":

            # Soil moisture range: 20% to 80%
            reading.value = round(random.uniform(20, 80), 2)
            reading.unit = "%"

        elif self.sensor_type == "light":

            # Light intensity range: 100 to 1000 lux
            reading.value = round(random.uniform(100, 1000), 2)
            reading.unit = "lux"

        else:

            # Unknown sensor type fallback
            reading.value = 0
            reading.unit = "unknown"

        return reading