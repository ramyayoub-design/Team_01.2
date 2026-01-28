"""
03 - Add Properties to Objects in a Speckle Model

This script demonstrates how to receive objects from Speckle,
add custom properties, and send them back as a new version.

Use this model: https://app.speckle.systems/projects/YOUR_PROJECT_ID/models/YOUR_MODEL_ID
"""

from main import get_client
from specklepy.transports.server import ServerTransport
from specklepy.api import operations
from specklepy.objects.base import Base


# TODO: Replace with your project, model, and version IDs
PROJECT_ID = "128262a20c"
MODEL_ID = "27fb92e1bf"
VERSION_ID = "b1eab1533b"

def main():
    # Authenticate
    client = get_client()

    # Get the specific version
    version = client.version.get(VERSION_ID, PROJECT_ID)
    print(f"✓ Fetching version: {version.id}")

    # Receive the data
    transport = ServerTransport(client=client, stream_id=PROJECT_ID)
    data = operations.receive(version.referenced_object, transport)

    # Add custom properties to the root object
    data["custom_property"] = "Hello from specklepy!"
    data["analysis_date"] = "2026-01-18"
    data["processed_by"] = "Tower Teachers Script"

    # Or add properties to child elements
    elements = getattr(data, "@elements", None) or getattr(data, "elements", [])
    for i, element in enumerate(elements or []):
        if isinstance(element, Base):
            element["element_index"] = i
            element["custom_tag"] = f"Element_{i:03d}"

    print(f"✓ Added properties to {len(elements) if elements else 0} elements")

    # Send the modified data back to Speckle
    object_id = operations.send(data, [transport])
    print(f"✓ Sent object: {object_id}")

    # Create a new version with the modified data
    from specklepy.core.api.inputs.version_inputs import CreateVersionInput

    version = client.version.create(CreateVersionInput(
        projectId=PROJECT_ID,
        modelId=MODEL_ID,
        objectId=object_id,
        message="Added custom properties via specklepy2"
    ))

    print(f"✓ Created version: {version.id}")


if __name__ == "__main__":
    main()




