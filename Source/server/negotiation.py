"""
HTTP content negotiation utilities.

This module provides helper functions for:
    - Detecting the client's preferred response format
    - Serializing API responses into different media types
    - Supporting multiple representations of the same resource

Supported formats:
    - JSON
    - XML
    - YAML

This module implements the HTTP feature:
    ✅ Content Negotiation

Example:

    Client Request:
        Accept: application/xml

    Server Response:
        Content-Type: application/xml
"""

from __future__ import annotations

# Standard library imports
import json
import xml.etree.ElementTree as ET

# Third-party YAML library
import yaml

# aiohttp request/response utilities
from aiohttp import web


# -------------------------------------------------------------
# Supported response media types
# -------------------------------------------------------------
SUPPORTED_TYPES = {
    "application/json",
    "application/xml",
    "application/yaml",
    "text/yaml",
}


def negotiate(request: web.Request) -> str:
    """
    Determine the best response media type.

    This function reads the HTTP Accept header
    sent by the client and chooses the best
    supported response format.

    Example Accept headers:
        application/json
        application/xml
        application/yaml

    If no supported type is found,
    JSON is used as the default.

    Args:
        request:
            Incoming aiohttp request object

    Returns:
        Selected media type string
    """

    # ---------------------------------------------------------
    # Read Accept header from HTTP request
    #
    # Default to JSON if header is missing
    # ---------------------------------------------------------
    accept = request.headers.get(
        "Accept",
        "application/json",
    )

    # ---------------------------------------------------------
    # Accept header may contain multiple types:
    #
    # Example:
    #   Accept: application/xml, application/json
    # ---------------------------------------------------------
    for media_type in accept.split(","):

        # Remove spaces and optional parameters
        #
        # Example:
        #   application/json;q=0.9
        # becomes:
        #   application/json
        media_type = media_type.strip().split(";")[0]

        # Check if media type is supported
        if media_type in SUPPORTED_TYPES:

            # Normalize YAML media types
            if media_type == "text/yaml":
                return "application/yaml"

            return media_type

    # ---------------------------------------------------------
    # Fallback response format
    # ---------------------------------------------------------
    return "application/json"


def to_xml(payload) -> bytes:
    """
    Convert Python data into XML format.

    Supports:
        - Dictionaries
        - Lists of dictionaries

    Args:
        payload:
            Data to convert into XML

    Returns:
        XML bytes
    """

    # Create XML root element
    root = ET.Element("response")

    # ---------------------------------------------------------
    # Handle list payloads
    # ---------------------------------------------------------
    if isinstance(payload, list):

        for item in payload:

            # Create <item> element
            entry = ET.SubElement(root, "item")

            # Add item fields
            for key, value in item.items():

                child = ET.SubElement(entry, key)

                child.text = str(value)

    # ---------------------------------------------------------
    # Handle dictionary payloads
    # ---------------------------------------------------------
    elif isinstance(payload, dict):

        for key, value in payload.items():

            child = ET.SubElement(root, key)

            child.text = str(value)

    # Convert XML tree into bytes
    return ET.tostring(root)


def serialize(payload, media_type: str) -> bytes:
    """
    Serialize response payload into requested format.

    Supported output formats:
        - JSON
        - XML
        - YAML

    Args:
        payload:
            Python data structure to serialize

        media_type:
            Requested HTTP media type

    Returns:
        Serialized bytes ready for HTTP response
    """

    # ---------------------------------------------------------
    # JSON serialization
    # ---------------------------------------------------------
    if media_type == "application/json":

        return json.dumps(payload).encode()

    # ---------------------------------------------------------
    # XML serialization
    # ---------------------------------------------------------
    if media_type == "application/xml":

        return to_xml(payload)

    # ---------------------------------------------------------
    # YAML serialization
    # ---------------------------------------------------------
    if media_type == "application/yaml":

        return yaml.dump(payload).encode()

    # ---------------------------------------------------------
    # Default fallback format
    # ---------------------------------------------------------
    return json.dumps(payload).encode()