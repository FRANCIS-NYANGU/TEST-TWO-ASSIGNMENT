"""
Content negotiation utilities for the REST API.

This module is responsible for:
    - Reading the HTTP Accept header
    - Selecting the best response media type
    - Serializing response payloads into different formats

Implemented HTTP Feature:
    ✅ Content Negotiation

Supported media types:
    - application/json
    - application/xml
    - application/yaml
    - text/yaml

If no supported format is requested,
the server falls back to JSON.
"""

from __future__ import annotations

# Standard library imports
import json
import xml.etree.ElementTree as ET

# Third-party YAML support
import yaml

# aiohttp request object
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

    This function:
        1. Reads the HTTP Accept header
        2. Parses media types and quality values
        3. Chooses the best supported format

    Example:
        Accept: application/xml;q=0.9, application/json;q=0.8

    Returns:
        Selected media type string
    """

    # ---------------------------------------------------------
    # Read Accept header from client request
    #
    # Default to JSON if header is missing
    # ---------------------------------------------------------
    accept_header = request.headers.get(
        "Accept",
        "application/json",
    )

    # Store parsed media types with quality values
    accepted_types = []

    # ---------------------------------------------------------
    # Split multiple Accept values
    # ---------------------------------------------------------
    for item in accept_header.split(","):

        item = item.strip()

        # Default quality factor
        quality = 1.0

        # -----------------------------------------------------
        # Handle quality values
        #
        # Example:
        #   application/xml;q=0.9
        # -----------------------------------------------------
        if ";q=" in item:

            media_type, q_value = item.split(";q=")

            try:
                quality = float(q_value)

            except ValueError:
                quality = 1.0

        else:
            media_type = item

        accepted_types.append(
            (media_type.strip(), quality)
        )

    # ---------------------------------------------------------
    # Sort by highest quality value
    # ---------------------------------------------------------
    accepted_types.sort(
        key=lambda entry: entry[1],
        reverse=True,
    )

    # ---------------------------------------------------------
    # Find first supported media type
    # ---------------------------------------------------------
    for media_type, _ in accepted_types:

        if media_type in SUPPORTED_TYPES:

            # Normalize YAML content type
            if media_type == "text/yaml":
                return "application/yaml"

            return media_type

    # ---------------------------------------------------------
    # Fallback to JSON
    # ---------------------------------------------------------
    return "application/json"


def to_xml(payload) -> bytes:
    """
    Convert payload into XML format.

    Supports:
        - dict
        - list of dicts

    Returns:
        XML bytes
    """

    # Root XML element
    root = ET.Element("response")

    # ---------------------------------------------------------
    # Handle list payload
    # ---------------------------------------------------------
    if isinstance(payload, list):

        for item in payload:

            entry = ET.SubElement(root, "item")

            for key, value in item.items():

                child = ET.SubElement(entry, key)

                child.text = str(value)

    # ---------------------------------------------------------
    # Handle dictionary payload
    # ---------------------------------------------------------
    elif isinstance(payload, dict):

        for key, value in payload.items():

            child = ET.SubElement(root, key)

            child.text = str(value)

    # Convert XML tree to bytes
    return ET.tostring(root)


def serialize(payload, media_type: str) -> bytes:
    """
    Serialize payload into requested format.

    Supported formats:
        - JSON
        - XML
        - YAML

    Args:
        payload:
            Dictionary or list of dictionaries

        media_type:
            Chosen response media type

    Returns:
        Serialized byte data
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