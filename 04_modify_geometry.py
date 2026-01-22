"""
04 - Modify Geometry in a Speckle Model

This script demonstrates how to find an object by applicationId,
duplicate it with an offset, and commit a new version.

Use the "two blocks" model. Copy the applicationId of the blocks's floor B.
Use this model: https://app.speckle.systems/projects/YOUR_PROJECT_ID/models/YOUR_MODEL_ID
"""

import copy
from main import get_client
from specklepy.transports.server import ServerTransport
from specklepy.api import operations
from specklepy.objects.base import Base


# TODO: Replace with your project and model IDs
PROJECT_ID = "YOUR_PROJECT_ID"
MODEL_ID = "YOUR_MODEL_ID"

# TODO: Replace with the applicationId of an object to duplicate
TARGET_APPLICATION_ID = "YOUR_APPLICATION_ID"

# Offset for the duplicated object (move to the right = positive X)
# Note: The model uses millimeters, so 50 meters = 50000 mm
OFFSET_X = 50000.0


def find_object_by_application_id(obj, target_id: str):
    """
    Recursively search for an object with the given applicationId.
    """
    if not isinstance(obj, Base):
        return None
    
    app_id = getattr(obj, "applicationId", None)
    if app_id == target_id:
        return obj
    
    # Search in child elements
    elements = getattr(obj, "@elements", None) or getattr(obj, "elements", [])
    for element in elements or []:
        found = find_object_by_application_id(element, target_id)
        if found:
            return found
    
    return None


def deep_copy_and_offset(obj, offset_x: float):
    """
    Create a deep copy of a Speckle object and offset its geometry in X direction.
    """
    # Serialize to dict and deserialize to create a copy
    from specklepy.serialization.base_object_serializer import BaseObjectSerializer
    
    # Create a simple deep copy using Base's serialization
    new_obj = Base()
    
    # Copy all properties
    for key in obj.get_member_names():
        value = getattr(obj, key, None)
        if value is not None:
            try:
                setattr(new_obj, key, copy.deepcopy(value))
            except:
                setattr(new_obj, key, value)
    
    # Clear the id so a new one is generated
    new_obj.id = None
    
    # Generate a new applicationId for the copy
    import uuid
    new_obj.applicationId = str(uuid.uuid4())
    
    # Offset geometry - check for common geometry patterns
    offset_geometry(new_obj, offset_x)
    
    return new_obj


def offset_geometry(obj, offset_x: float):
    """
    Offset geometry in the X direction for various geometry types.
    """
    # Handle displayValue (common in Revit objects)
    display_value = getattr(obj, "displayValue", None) or getattr(obj, "@displayValue", None)
    if display_value:
        if isinstance(display_value, list):
            for mesh in display_value:
                offset_mesh_vertices(mesh, offset_x)
        else:
            offset_mesh_vertices(display_value, offset_x)
    
    # Handle direct vertices (for Mesh objects)
    if hasattr(obj, "vertices") and obj.vertices:
        offset_mesh_vertices(obj, offset_x)
    
    # Handle base point / location
    if hasattr(obj, "basePoint"):
        bp = obj.basePoint
        if hasattr(bp, "x"):
            bp.x += offset_x
    
    if hasattr(obj, "location"):
        loc = obj.location
        if hasattr(loc, "x"):
            loc.x += offset_x


def offset_mesh_vertices(mesh, offset_x: float):
    """
    Offset mesh vertices in the X direction.
    Vertices are stored as flat list: [x1, y1, z1, x2, y2, z2, ...]
    """
    if hasattr(mesh, "vertices") and mesh.vertices:
        new_vertices = []
        for i in range(0, len(mesh.vertices), 3):
            new_vertices.append(mesh.vertices[i] + offset_x)  # x + offset
            new_vertices.append(mesh.vertices[i + 1])          # y
            new_vertices.append(mesh.vertices[i + 2])          # z
        mesh.vertices = new_vertices


def main():
    # Authenticate
    client = get_client()
    
    # Get the latest version
    versions = client.version.get_versions(MODEL_ID, PROJECT_ID, limit=1)
    if not versions.items:
        print("No versions found.")
        return
    
    latest_version = versions.items[0]
    print(f"✓ Fetching version: {latest_version.id}")
    
    # Receive the full data tree
    transport = ServerTransport(client=client, stream_id=PROJECT_ID)
    data = operations.receive(latest_version.referenced_object, transport)
    
    # Find the target object
    print(f"\n--- Duplicate object {TARGET_APPLICATION_ID} ---")
    target_obj = find_object_by_application_id(data, TARGET_APPLICATION_ID)
    
    if not target_obj:
        print(f"✗ Could not find object with applicationId: {TARGET_APPLICATION_ID}")
        return
    
    print(f"✓ Found object: {getattr(target_obj, 'name', 'Unnamed')}")
    print(f"  Type: {getattr(target_obj, 'speckle_type', 'Unknown')}")
    
    # Create a copy with offset
    copied_obj = deep_copy_and_offset(target_obj, OFFSET_X)
    copied_obj.name = f"{getattr(target_obj, 'name', 'Object')}_Copy"
    print(f"✓ Created copy with X offset of {OFFSET_X}")
    
    # Add the copy to the elements
    elements = getattr(data, "@elements", None)
    if elements is not None:
        elements.append(copied_obj)
    else:
        elements = getattr(data, "elements", None)
        if elements is not None:
            elements.append(copied_obj)
        else:
            data["@elements"] = [copied_obj]
    
    print(f"✓ Added copy to model elements")
    
    # Send the modified data back
    object_id = operations.send(data, [transport])
    print(f"✓ Sent object: {object_id}")
    
    # Create a new version
    from specklepy.core.api.inputs.version_inputs import CreateVersionInput
    
    version = client.version.create(CreateVersionInput(
        projectId=PROJECT_ID,
        modelId=MODEL_ID,
        objectId=object_id,
        message=f"Duplicated object {TARGET_APPLICATION_ID} with X offset {OFFSET_X}"
    ))
    
    print(f"✓ Created version: {version.id}")


if __name__ == "__main__":
    main()
