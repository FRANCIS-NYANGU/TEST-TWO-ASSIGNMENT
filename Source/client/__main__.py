"""
Entry point for the IoT sensor simulator system.

This module:
    - Loads sensor settings from a YAML configuration file
    - Creates sensor simulator objects
    - Starts all sensors concurrently using asyncio

Run the program with:

    python -m client --config config/sensors.yaml
"""

from __future__ import annotations

# Standard library imports
import argparse
import asyncio

# Third-party library for reading YAML files
import yaml

# Local application import
from client.simulator import SensorSimulator


async def main() -> None:
    """
    Main async function for starting the simulator system.

    Steps performed:
        1. Read command-line arguments
        2. Load YAML configuration
        3. Extract server and sensor settings
        4. Create sensor simulator tasks
        5. Run all sensors concurrently
    """

    # ---------------------------------------------------------
    # Create command-line argument parser
    # ---------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="IoT Sensor Simulator"
    )

    # Add required config file argument
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the sensors YAML configuration file"
    )

    # Parse arguments entered by the user
    args = parser.parse_args()

    # ---------------------------------------------------------
    # Load configuration from YAML file
    # ---------------------------------------------------------
    with open(args.config, "r") as file:

        # Convert YAML content into a Python dictionary
        config = yaml.safe_load(file)

    # ---------------------------------------------------------
    # Read server connection details
    # ---------------------------------------------------------
    server_host = config["server"]["host"]
    server_port = config["server"]["port"]

    # Read list of configured sensors
    sensors = config["sensors"]

    # List that will store all async sensor tasks
    tasks = []

    # ---------------------------------------------------------
    # Create one simulator instance per sensor
    # ---------------------------------------------------------
    for sensor in sensors:

        # Create simulator object using sensor settings
        simulator = SensorSimulator(
            sensor_id=sensor["id"],
            sensor_type=sensor["type"],
            interval_seconds=sensor["interval"],
            host=server_host,
            port=server_port,
        )

        # Start simulator as an asynchronous task
        task = asyncio.create_task(simulator.run())

        # Save task in task list
        tasks.append(task)

    # Display startup information
    print(f"Starting {len(tasks)} sensor(s)...")

    # ---------------------------------------------------------
    # Run all sensor tasks forever
    # ---------------------------------------------------------
    await asyncio.gather(*tasks)


# -------------------------------------------------------------
# Program entry point
# -------------------------------------------------------------
if __name__ == "__main__":

    # Start asyncio event loop
    asyncio.run(main())