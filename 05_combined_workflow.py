"""
05 - Combined Workflow: Fetch, Modify Geometry, Add Properties, and Send to Team_01.2

This script demonstrates the complete workflow:
1. Fetch model from source
2. Restructure hierarchy:
   - Rename root document to "Specklepy"
   - Rename "Layer 01" to "Old_modules"
3. Add Designer properties (inside properties sub-object) to Module 01 and Module 03 in Old_modules
4. Copy Module 01 (as BrepX) with Z offset, rename to BrepX, and place in new "New_modules" Layer
5. Add Designer property (inside properties sub-object) to the new BrepX in New_modules
6. Send to Team_01.2 model

Source: https://app.speckle.systems/projects/128262a20c/models/a1014e4b32
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
DESIGNER_MODULE_02 = "Ramy Ayoub"  # For the new copied module (Module 02)


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
    Create a deep copy of a Speckle object, preserving its type (e.g., BrepX).
    """
    # Get the original speckle_type to preserve it
    original_type = getattr(obj, "speckle_type", None)

    # Create new object of the same type
    # Use the class of the original object to maintain BrepX, Mesh, etc.
    new_obj = obj.__class__()

    # If it has speckle_type, preserve it
    if original_type:
        new_obj.speckle_type = original_type

    # Copy all properties
    for key in obj.get_member_names():
        # Skip id as we want a new one generated
        if key == "id":
            continue

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


def find_layer_by_name(obj, layer_name: str):
    """
    Find a layer/collection by name in the elements.
    """
    if not isinstance(obj, Base):
        return None

    # Check if this object itself has the name
    obj_name = getattr(obj, "name", None)
    if obj_name == layer_name:
        return obj

    # Search in child elements
    elements = getattr(obj, "@elements", None) or getattr(obj, "elements", [])
    for element in elements or []:
        if isinstance(element, Base):
            elem_name = getattr(element, "name", None)
            if elem_name == layer_name:
                return element
            # Recursively search
            found = find_layer_by_name(element, layer_name)
            if found:
                return found

    return None


def create_layer(name: str, geometry_objects: list):
    """
    Create a new Base collection that directly contains geometry objects.
    This matches the structure of Old_modules (Base type without collectionType property).
    """
    # Create a Base object and configure it as a Layer/Collection
    layer = Base()

    # Set the speckle_type to identify it as a Collection
    layer.speckle_type = "Speckle.Core.Models.Collection"

    # Don't set collectionType at all to display as "Base" instead of "Layer"
    # (omitting the collectionType property makes it display as "Base")

    # Set the layer name
    layer.name = name

    # Generate a unique applicationId
    layer.applicationId = str(uuid.uuid4())

    # Add geometry objects directly to elements (not @elements)
    layer["elements"] = geometry_objects

    return layer


def set_designer_property(obj, designer_name: str):
    """
    Set the Designer property inside the 'properties' sub-object of a module.
    Creates the properties object if it doesn't exist.
    """
    # Check if properties exists
    properties = getattr(obj, "properties", None)

    if properties is None:
        # Create a new properties object
        properties = Base()
        obj["properties"] = properties

    # Set the Designer field inside properties
    properties["Designer"] = designer_name


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

    # Rename root document and set Tower properties
    old_root_name = getattr(data, "name", "unnamed")
    data.name = "Specklepy"
    data["collectionType"] = "Tower"
    data["Tower"] = "Team-01.2"
    print(f"✓ Renamed root: '{old_root_name}' → 'Specklepy'")
    print(f"  Set collectionType: Tower, Tower: Team-01.2")


    print("\n" + "=" * 60)
    print("STEP 2: Restructure layers and add Designer properties")
    print("=" * 60)

    # Find and rename Layer 01 to Old_modules
    layer_01 = find_layer_by_name(data, "Layer 01")
    if layer_01:
        layer_01.name = "Old_modules"
        # Remove the collectionType property entirely to display as "Base" instead of "Layer"
        if hasattr(layer_01, "collectionType"):
            delattr(layer_01, "collectionType")
        print(f"✓ Renamed layer: 'Layer 01' → 'Old_modules'")
        print(f"  Removed collectionType (displays as 'Base')")
    else:
        print(f"⚠ Warning: Could not find 'Layer 01' to rename")

    # Find Module 01
    module_01 = find_object_by_application_id(data, MODULE_01_APP_ID)
    if not module_01:
        print(f"✗ Could not find Module 01 with applicationId: {MODULE_01_APP_ID}")
        return

    module_01_name = getattr(module_01, "name", "Module_01")
    print(f"✓ Found Module 01: {module_01_name}")
    set_designer_property(module_01, DESIGNER_MODULE_01)
    print(f"  Added property: properties.Designer = {DESIGNER_MODULE_01}")

    # Find Module 03
    module_03 = find_object_by_application_id(data, MODULE_03_APP_ID)
    if not module_03:
        print(f"✗ Could not find Module 03 with applicationId: {MODULE_03_APP_ID}")
        return

    module_03_name = getattr(module_03, "name", "Module_03")
    print(f"✓ Found Module 03: {module_03_name}")
    set_designer_property(module_03, DESIGNER_MODULE_03)
    print(f"  Added property: properties.Designer = {DESIGNER_MODULE_03}")



    print("\n" + "=" * 60)
    print("STEP 3: Copy Module 01 as BrepX with Z offset in New_modules Layer")
    print("=" * 60)

    # Create a copy of Module 01 (preserving BrepX type)
    new_module = deep_copy_object(module_01)
    new_module.name = "BrepX"  # Match naming convention in Old_modules

    # Add Designer property inside properties sub-object
    set_designer_property(new_module, DESIGNER_MODULE_02)
    new_module.properties["Module"] = "02"

    # Apply Z offset to the geometry
    offset_geometry_z(new_module, Z_OFFSET)

    print(f"✓ Created BrepX (copy of {module_01_name})")
    print(f"  Type: {getattr(new_module, 'speckle_type', 'Unknown')}")
    print(f"  Z Offset: {Z_OFFSET} mm ({Z_OFFSET/1000} meters)")
    print(f"  Added properties: Designer = {DESIGNER_MODULE_02}, Module = 02")

    # Create a new Layer "New_modules" and add the BrepX directly to it
    # This matches the structure of Old_modules (Layer > BrepX)
    new_modules_layer = create_layer("New_modules", [new_module])
    print(f"✓ Created 'New_modules' Layer with BrepX geometry")

    # Add the layer to the root elements
    elements = getattr(data, "@elements", None)
    if elements is not None:
        elements.append(new_modules_layer)
    else:
        elements = getattr(data, "elements", None)
        if elements is not None:
            elements.append(new_modules_layer)
        else:
            data["@elements"] = [new_modules_layer]

    print(f"✓ Added 'New_modules' Layer to model")


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
        message=f"Restructured model: Renamed root to Specklepy, Old_modules Layer with Module 01 & 03, created New_modules Layer with BrepX (Z offset {Z_OFFSET}mm), added Designer properties to all BrepX geometries"
    ))

    print(f"✓ Created version in Team_01.2: {version.id}")
    print(f"\n✓ Workflow complete!")
    print(f"  View result: https://app.speckle.systems/projects/{DEST_PROJECT_ID}/models/{DEST_MODEL_ID}")


if __name__ == "__main__":
    main()
