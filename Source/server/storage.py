"""
Database storage layer for the IoT telemetry system.

This module provides:
    - Abstract storage interface
    - SQLite implementation using aiosqlite
    - Persistent storage for sensors and readings

Features:
    ✅ Async database operations
    ✅ SQLite persistence
    ✅ Sensor management
    ✅ Telemetry reading storage

Database Tables:
    1. sensors
    2. readings
"""

from __future__ import annotations

# Typing helpers
from typing import Iterable, Optional

# Async SQLite driver
import aiosqlite


# =============================================================
# Abstract Storage Interface
# =============================================================
class Storage:
    """
    Abstract storage interface.

    Defines methods that every storage backend
    must implement.
    """

    async def add_sensor(self, sensor) -> None:
        """Store a new sensor."""
        raise NotImplementedError

    async def remove_sensor(self, sensor_id: str) -> None:
        """Delete a sensor."""
        raise NotImplementedError

    async def list_sensors(self) -> Iterable:
        """Return all sensors."""
        raise NotImplementedError

    async def add_reading(self, reading) -> None:
        """Store a telemetry reading."""
        raise NotImplementedError

    async def get_readings(
        self,
        sensor_id: str,
        from_ts: Optional[float] = None,
        to_ts: Optional[float] = None,
    ) -> Iterable:
        """
        Return readings for a sensor.

        Optional timestamp filters:
            from_ts:
                Return readings after this timestamp

            to_ts:
                Return readings before this timestamp
        """
        raise NotImplementedError


# =============================================================
# SQLite Storage Implementation
# =============================================================
class SQLiteStorage(Storage):
    """
    SQLite-based storage backend.

    Uses:
        - SQLite database file
        - aiosqlite for asynchronous queries
    """

    def __init__(self, db_path: str = "telemetry.db"):
        """
        Initialize storage object.

        Args:
            db_path:
                Path to SQLite database file
        """

        self.db_path = db_path

    # =========================================================
    # Database Initialization
    # =========================================================
    async def initialize(self) -> None:
        """
        Create database tables if they do not exist.
        """

        async with aiosqlite.connect(self.db_path) as db:

            # -------------------------------------------------
            # Sensor metadata table
            # -------------------------------------------------
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sensors (
                    id TEXT PRIMARY KEY,
                    type TEXT
                )
            """)

            # -------------------------------------------------
            # Sensor readings table
            # -------------------------------------------------
            await db.execute("""
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_id TEXT,
                    reading_type TEXT,
                    value REAL,
                    unit TEXT,
                    timestamp TEXT
                )
            """)

            # Save changes
            await db.commit()

    # =========================================================
    # Add Sensor
    # =========================================================
    async def add_sensor(self, sensor) -> None:
        """
        Store a sensor in the database.

        Uses INSERT OR IGNORE to prevent duplicates.
        """

        async with aiosqlite.connect(self.db_path) as db:

            await db.execute("""
                INSERT OR IGNORE INTO sensors(id, type)
                VALUES (?, ?)
            """, (
                sensor["id"],
                sensor["type"],
            ))

            await db.commit()

    # =========================================================
    # Remove Sensor
    # =========================================================
    async def remove_sensor(self, sensor_id: str) -> None:
        """
        Delete a sensor from the database.
        """

        async with aiosqlite.connect(self.db_path) as db:

            await db.execute(
                "DELETE FROM sensors WHERE id = ?",
                (sensor_id,)
            )

            await db.commit()

    # =========================================================
    # List Sensors
    # =========================================================
    async def list_sensors(self):
        """
        Return all registered sensors.

        Returns:
            List of dictionaries
        """

        async with aiosqlite.connect(self.db_path) as db:

            cursor = await db.execute(
                "SELECT id, type FROM sensors"
            )

            rows = await cursor.fetchall()

            # Convert database rows into dictionaries
            return [
                {
                    "id": row[0],
                    "type": row[1],
                }
                for row in rows
            ]

    # =========================================================
    # Add Reading
    # =========================================================
    async def add_reading(self, reading) -> None:
        """
        Store a telemetry reading.
        """

        async with aiosqlite.connect(self.db_path) as db:

            await db.execute("""
                INSERT INTO readings (
                    sensor_id,
                    reading_type,
                    value,
                    unit,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                reading["sensor_id"],
                reading["reading_type"],
                reading["value"],
                reading["unit"],
                reading["timestamp"],
            ))

            await db.commit()

    # =========================================================
    # Get Readings
    # =========================================================
    async def get_readings(
        self,
        sensor_id: str,
        from_ts=None,
        to_ts=None,
    ):
        """
        Return telemetry readings for a sensor.

        Optional filters:
            from_ts:
                Minimum timestamp

            to_ts:
                Maximum timestamp
        """

        # -----------------------------------------------------
        # Base SQL query
        # -----------------------------------------------------
        query = """
            SELECT
                sensor_id,
                reading_type,
                value,
                unit,
                timestamp
            FROM readings
            WHERE sensor_id = ?
        """

        # Query parameters
        params = [sensor_id]

        # -----------------------------------------------------
        # Optional time filtering
        # -----------------------------------------------------
        if from_ts is not None:

            query += " AND timestamp >= ?"

            params.append(from_ts)

        if to_ts is not None:

            query += " AND timestamp <= ?"

            params.append(to_ts)

        # -----------------------------------------------------
        # Execute query
        # -----------------------------------------------------
        async with aiosqlite.connect(self.db_path) as db:

            cursor = await db.execute(query, params)

            rows = await cursor.fetchall()

            # Convert rows into dictionaries
            return [
                {
                    "sensor_id": row[0],
                    "reading_type": row[1],
                    "value": row[2],
                    "unit": row[3],
                    "timestamp": row[4],
                }
                for row in rows
            ]