"""
REST API for the IoT telemetry system.

This module provides HTTP endpoints for:
    - Listing sensors
    - Viewing sensor readings
    - Registering sensors
    - Deleting sensors

Implemented HTTP Features:
    ✅ Content Negotiation
    ✅ Cookies (Session Management)
    ✅ CORS Support

API Endpoints:
    GET     /sensors
    GET     /sensors/{id}/readings
    POST    /sensors
    DELETE  /sensors/{id}
"""

from __future__ import annotations

# Standard library imports
import uuid

# aiohttp web framework
from aiohttp import web

# CORS support for browser-based clients
import aiohttp_cors

# Local helper functions for content negotiation
from server.negotiation import negotiate, serialize


# -------------------------------------------------------------
# In-memory sensor registry
#
# Stores manually registered sensors.
# Example:
#   {
#       "sensor-1": {...},
#       "sensor-2": {...}
#   }
# -------------------------------------------------------------
SENSORS = {}


# =============================================================
# GET /sensors
# =============================================================
async def list_sensors(request: web.Request) -> web.Response:
    """
    Return all known sensors.

    Supports content negotiation:
        - JSON
        - XML
        - YAML
    """

    # Get database storage instance
    storage = request.app["storage"]

    # Fetch sensors from database
    payload = await storage.list_sensors()

    # Determine best response format
    media_type = negotiate(request)

    # Serialize response into requested format
    body = serialize(payload, media_type)

    # Return HTTP response
    return web.Response(
        body=body,
        content_type=media_type,
    )


# =============================================================
# GET /sensors/{id}/readings
# =============================================================
async def get_readings(request: web.Request) -> web.Response:
    """
    Return readings for a specific sensor.

    URL Example:
        /sensors/temp-01/readings

    Supports content negotiation.
    """

    # Extract sensor ID from URL
    sensor_id = request.match_info["id"]

    # Access shared storage object
    storage = request.app["storage"]

    # Retrieve readings from database
    readings = await storage.get_readings(sensor_id)

    # Build response payload
    payload = {
        "sensor_id": sensor_id,
        "readings": list(readings),
    }

    # Determine requested response format
    media_type = negotiate(request)

    # Convert payload into requested media type
    body = serialize(payload, media_type)

    # Return HTTP response
    return web.Response(
        body=body,
        content_type=media_type,
    )


# =============================================================
# POST /sensors
# =============================================================
async def register_sensor(request: web.Request) -> web.Response:
    """
    Register a new sensor.

    Example JSON request body:
        {
            "id": "temp-01",
            "type": "temperature"
        }
    """

    # Parse incoming JSON body
    payload = await request.json()

    # Extract sensor ID
    sensor_id = payload["id"]

    # Store sensor in memory
    SENSORS[sensor_id] = payload

    print(f"Registered sensor: {sensor_id}")

    # Return created sensor
    return web.json_response(
        payload,
        status=201,
    )


# =============================================================
# DELETE /sensors/{id}
# =============================================================
async def delete_sensor(request: web.Request) -> web.Response:
    """
    Delete a registered sensor.
    """

    # Extract sensor ID from URL
    sensor_id = request.match_info["id"]

    # Remove sensor if it exists
    SENSORS.pop(sensor_id, None)

    print(f"Deleted sensor: {sensor_id}")

    # 204 = No Content
    return web.Response(status=204)


# =============================================================
# Session Cookie Middleware
# =============================================================
@web.middleware
async def session_cookie_middleware(request, handler):
    """
    Middleware for handling session cookies.

    Behaviour:
        - Checks whether client already has a session
        - Creates a new session ID if missing
        - Stores session ID in request object
        - Sends session cookie back to client

    HTTP Feature Implemented:
        ✅ Cookies
    """

    # ---------------------------------------------------------
    # Read session cookie from client request
    # ---------------------------------------------------------
    session_id = request.cookies.get("session_id")

    # ---------------------------------------------------------
    # Create new session if cookie does not exist
    # ---------------------------------------------------------
    if not session_id:

        # Generate unique session identifier
        session_id = str(uuid.uuid4())

    # Store session ID in request object
    request["session_id"] = session_id

    # Continue processing request
    response = await handler(request)

    # ---------------------------------------------------------
    # Attach cookie to HTTP response
    # ---------------------------------------------------------
    response.set_cookie(
        "session_id",
        session_id,

        # Prevent JavaScript access
        httponly=True,
    )

    return response


# =============================================================
# Application Factory
# =============================================================
def build_app(storage) -> web.Application:
    """
    Create and configure aiohttp application.

    Responsibilities:
        - Register middleware
        - Register API routes
        - Configure CORS
        - Attach shared storage
    """

    # ---------------------------------------------------------
    # Create aiohttp application
    # ---------------------------------------------------------
    app = web.Application(
        middlewares=[
            session_cookie_middleware
        ]
    )

    # ---------------------------------------------------------
    # Register REST API routes
    # ---------------------------------------------------------
    app.router.add_get(
        "/sensors",
        list_sensors,
    )

    app.router.add_get(
        "/sensors/{id}/readings",
        get_readings,
    )

    app.router.add_post(
        "/sensors",
        register_sensor,
    )

    app.router.add_delete(
        "/sensors/{id}",
        delete_sensor,
    )

    # ---------------------------------------------------------
    # Store shared database instance
    # ---------------------------------------------------------
    app["storage"] = storage

    # ---------------------------------------------------------
    # Enable Cross-Origin Resource Sharing (CORS)
    #
    # Allows frontend applications hosted on other
    # origins to access this API.
    # ---------------------------------------------------------
    cors = aiohttp_cors.setup(app)

    # Apply CORS settings to all routes
    for route in list(app.router.routes()):

        cors.add(
            route,
            {
                "*": aiohttp_cors.ResourceOptions(

                    # Allow cookies/authentication
                    allow_credentials=True,

                    # Expose all response headers
                    expose_headers="*",

                    # Allow all request headers
                    allow_headers="*",
                )
            },
        )

    return app