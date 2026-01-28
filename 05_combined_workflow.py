"""
05 - Combined Workflow: Fetch, Modify Geometry, Add Properties, and Send to Team_01.2

This script demonstrates the complete workflow:
1. Fetch model from source
2. Modify geometry (copy Module 01 with Z offset)
3. Add Designer properties to old and new modules
4. Send to Team_01.2 model

Source: https://app.speckle.systems/projects/128262a20c/models/27fb92e1bf
Destination: https://app.speckle.systems/projects/128262a20c/models/0bfddb7ab6
"""

import copy
import uuid
from main import get_client
from specklepy.transports.server import ServerTransport
from specklepy.api import operations
from specklepy.objects.base import Base
from specklepy.core.api.inputs.version_inputs import CreateVersionInput


# Source model (where we fetch the original data)
SOURCE_PROJECT_ID = "128262a20c"
SOURCE_MODEL_ID = "a1014e4b32"
VERSION_ID = "6fcf730fc6"

# Destination model (Team_01.2 - where we send the modified data)
DEST_PROJECT_ID = "128262a20c"
DEST_MODEL_ID = "0bfddb7ab6"

# Module applicationIds
MODULE_01_APP_ID = "17cc627f-f5df-44d2-908e-1cdaf96fe76c"  # Old block - Designer: Student_1
MODULE_03_APP_ID = "50cae94b-00de-47e9-8e2d-15a748240fc0"  # Old block - Designer: Student_2

# TODO: Set your desired Z offset for the new module (in millimeters)
# Example: 10000 = 10 meters, 20000 = 20 meters
Z_OFFSET = 16000.0  # <-- CHANGE THIS VALUE

# Designer names (update these with actual student names)
DESIGNER_MODULE_01 = "Hani Karime"
DESIGNER_MODULE_03 = "Charles Abi Chahine"
DESIGNER_NEW_MODULE = "Ramy Ayoub"


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


def deep_copy_object(obj):
    """
    Create a deep copy of a Speckle object.
    """
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
    new_obj.applicationId = str(uuid.uuid4())

    return new_obj


def offset_geometry_z(obj, offset_z: float):
    """
    Offset geometry in the Z direction for various geometry types.
    """
    # Handle displayValue (common in Revit objects)
    display_value = getattr(obj, "displayValue", None) or getattr(obj, "@displayValue", None)
    if display_value:
        if isinstance(display_value, list):
            for mesh in display_value:
                offset_mesh_vertices_z(mesh, offset_z)
        else:
            offset_mesh_vertices_z(display_value, offset_z)

    # Handle direct vertices (for Mesh objects)
    if hasattr(obj, "vertices") and obj.vertices:
        offset_mesh_vertices_z(obj, offset_z)

    # Handle base point / location
    if hasattr(obj, "basePoint"):
        bp = obj.basePoint
        if hasattr(bp, "z"):
            bp.z += offset_z

    if hasattr(obj, "location"):
        loc = obj.location
        if hasattr(loc, "z"):
            loc.z += offset_z


def offset_mesh_vertices_z(mesh, offset_z: float):
    """
    Offset mesh vertices in the Z direction.
    Vertices are stored as flat list: [x1, y1, z1, x2, y2, z2, ...]
    """
    if hasattr(mesh, "vertices") and mesh.vertices:
        new_vertices = []
        for i in range(0, len(mesh.vertices), 3):
            new_vertices.append(mesh.vertices[i])          # x
            new_vertices.append(mesh.vertices[i + 1])      # y
            new_vertices.append(mesh.vertices[i + 2] + offset_z)  # z + offset
        mesh.vertices = new_vertices


def main():
    # Authenticate
    client = get_client()

    print("=" * 60)
    print("STEP 1: Fetch source model")
    print("=" * 60)

    # Get the latest version from source
    versions = client.version.get_versions(SOURCE_MODEL_ID, SOURCE_PROJECT_ID, limit=1)
    if not versions.items:
        print("✗ No versions found in source model.")
        return

    latest_version = versions.items[0]
    print(f"✓ Fetching version: {latest_version.id}")
    print(f"  Message: {latest_version.message}")

    # Receive the full data tree
    transport = ServerTransport(client=client, stream_id=SOURCE_PROJECT_ID)
    data = operations.receive(latest_version.referenced_object, transport)
    print(f"✓ Received data from source model")


    print("\n" + "=" * 60)
    print("STEP 2: Find and tag old modules with Designer property")
    print("=" * 60)

    # Find Module 01
    module_01 = find_object_by_application_id(data, MODULE_01_APP_ID)
    if not module_01:
        print(f"✗ Could not find Module 01 with applicationId: {MODULE_01_APP_ID}")
        return

    module_01_name = getattr(module_01, "name", "Module_01")
    print(f"✓ Found Module 01: {module_01_name}")
    module_01["Designer"] = DESIGNER_MODULE_01
    print(f"  Added property: Designer = {DESIGNER_MODULE_01}")

    # Find Module 03
    module_03 = find_object_by_application_id(data, MODULE_03_APP_ID)
    if not module_03:
        print(f"✗ Could not find Module 03 with applicationId: {MODULE_03_APP_ID}")
        return

    module_03_name = getattr(module_03, "name", "Module_03")
    print(f"✓ Found Module 03: {module_03_name}")
    module_03["Designer"] = DESIGNER_MODULE_03
    print(f"  Added property: Designer = {DESIGNER_MODULE_03}")


    print("\n" + "=" * 60)
    print("STEP 3: Copy Module 01 and create New_Module with Z offset")
    print("=" * 60)

    # Create a copy of Module 01
    new_module = deep_copy_object(module_01)
    new_module.name = "New_Module"
    new_module["Designer"] = DESIGNER_NEW_MODULE

    # Apply Z offset to the geometry
    offset_geometry_z(new_module, Z_OFFSET)

    print(f"✓ Created New_Module (copy of {module_01_name})")
    print(f"  Z Offset: {Z_OFFSET} mm ({Z_OFFSET/1000} meters)")
    print(f"  Added property: Designer = {DESIGNER_NEW_MODULE}")

    # Add the new module to the elements
    elements = getattr(data, "@elements", None)
    if elements is not None:
        elements.append(new_module)
    else:
        elements = getattr(data, "elements", None)
        if elements is not None:
            elements.append(new_module)
        else:
            data["@elements"] = [new_module]

    print(f"✓ Added New_Module to model elements")


    print("\n" + "=" * 60)
    print("STEP 4: Send modified data to Team_01.2")
    print("=" * 60)

    # Send to destination (Team_01.2)
    dest_transport = ServerTransport(client=client, stream_id=DEST_PROJECT_ID)
    object_id = operations.send(data, [dest_transport])
    print(f"✓ Sent object: {object_id}")

    # Create a new version in Team_01.2
    version = client.version.create(CreateVersionInput(
        projectId=DEST_PROJECT_ID,
        modelId=DEST_MODEL_ID,
        objectId=object_id,
        message=f"Added Designer properties and created New_Module with Z offset {Z_OFFSET}mm"
    ))

    print(f"✓ Created version in Team_01.2: {version.id}")
    print(f"\n✓ Workflow complete!")
    print(f"  View result: https://app.speckle.systems/projects/{DEST_PROJECT_ID}/models/{DEST_MODEL_ID}")


if __name__ == "__main__":
    main()
