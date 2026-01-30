"""
06 - Export Model Objects to JSON

This script demonstrates how to query all objects from a Speckle model
using GraphQL and export them with their properties to a JSON file.

Use this model: https://app.speckle.systems/projects/YOUR_PROJECT_ID/models/YOUR_MODEL_ID
"""

import json
import os
from main import get_client
from specklepy.transports.server import ServerTransport
from specklepy.api import operations
from specklepy.objects.base import Base


# TODO: Replace with your project and model IDs
PROJECT_ID = "128262a20c"
MODEL_ID = "0bfddb7ab6"


def query_objects_graphql(client, project_id: str, version_id: str) -> dict:
    """
    Query project and version info using Speckle's GraphQL API.
    """
    from gql import gql
    
    query = gql("""
    query GetProjectWithVersions($projectId: String!, $versionId: String!) {
        project(id: $projectId) {
            id
            name
            version(id: $versionId) {
                id
                message
                createdAt
                referencedObject
            }
        }
    }
    """)
    
    variables = {
        "projectId": project_id,
        "versionId": version_id
    }
    
    # Execute GraphQL query using the client's GQL session
    result = client.httpclient.execute(query, variable_values=variables)
    return result


def collect_all_objects(obj, collected=None, depth=0) -> list:
    """
    Recursively collect all objects and their properties from the Speckle data tree.
    """
    if collected is None:
        collected = []
    
    if not isinstance(obj, Base):
        return collected
    
    # Convert object to dictionary
    obj_dict = {
        "id": getattr(obj, "id", None),
        "speckle_type": getattr(obj, "speckle_type", None),
        "applicationId": getattr(obj, "applicationId", None),
        "name": getattr(obj, "name", None),
        "depth": depth,
        "properties": {}
    }
    
    # Collect all properties
    for key in obj.get_member_names():
        if key.startswith("_"):
            continue
        value = getattr(obj, key, None)
        if value is not None and not isinstance(value, Base) and not isinstance(value, list):
            obj_dict["properties"][key] = value
        elif isinstance(value, list) and len(value) > 0 and not isinstance(value[0], Base):
            obj_dict["properties"][key] = value
    
    collected.append(obj_dict)
    
    # Recursively process child objects
    elements = getattr(obj, "@elements", None) or getattr(obj, "elements", [])
    for element in elements or []:
        collect_all_objects(element, collected, depth + 1)
    
    return collected


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
    
    # Query project info via GraphQL
    try:
        graphql_result = query_objects_graphql(client, PROJECT_ID, latest_version.id)
        print(f"✓ GraphQL query executed successfully")
    except Exception as e:
        print(f"⚠ GraphQL query failed: {e}")
        graphql_result = None
    
    # Receive the full data tree
    transport = ServerTransport(client=client, stream_id=PROJECT_ID)
    data = operations.receive(latest_version.referenced_object, transport)
    
    # Collect all objects with their properties
    all_objects = collect_all_objects(data)
    print(f"✓ Collected {len(all_objects)} objects from the model")
    
    # Create output dictionary
    output = {
        "project_id": PROJECT_ID,
        "model_id": MODEL_ID,
        "version_id": latest_version.id,
        "version_message": latest_version.message,
        "graphql_info": graphql_result,
        "objects": all_objects
    }
    
    # Save to JSON file (in the same directory as this script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "model_objects.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"✓ Saved all objects to {output_file}")


if __name__ == "__main__":
    main()