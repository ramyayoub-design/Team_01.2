"""
combining both scirpt so it eport Speckle Object Data to JSON using GraphQL 
and listen to real time updates using Speckle Subscriptions.
"""

import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from gql import gql, Client
from gql.transport.websockets import WebsocketsTransport
from main import get_client

load_dotenv()

# PROJECT_ID = "128262a20c"
# OBJECT_ID = "1fc04b932daa9f4c6e5759c805a953f7"

YOUR_TOKEN = os.environ.get("SPECKLE_TOKEN")
PROJECT_ID = "128262a20c"
OBJECT_ID = "47f3fc068baf83fc1053939b2893aed1"


def export_object_data(speckle_client, version_info: dict = None):
    """Fetch object data and save to timestamped JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    result = speckle_client.httpclient.execute(
        object_query,
        variable_values={"projectId": PROJECT_ID, "objectId": OBJECT_ID}
    )

    if result is None:
        print(f"❌ Query returned None. Check PROJECT_ID ({PROJECT_ID}) and OBJECT_ID ({OBJECT_ID})")
        return

    project = result.get("project")
    if project is None:
        print(f"❌ Project not found: {PROJECT_ID}")
        print(f"   Full response: {result}")
        return

    obj = project.get("object")
    if obj is None:
        print(f"❌ Object not found: {OBJECT_ID}")
        print(f"   Full response: {result}")
        return

    output = {
        "exportedAt": datetime.now().isoformat(),
        "projectId": PROJECT_ID,
        "objectId": OBJECT_ID,
        "versionInfo": version_info,
        "data": obj.get("data")
    }
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, f"object_data_{timestamp}.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"✓ Exported to {output_file}")

object_query = gql("""
    query GetObjectDataJSON($objectId: String!, $projectId: String!) {
        project(id: $projectId) {
            object(id: $objectId) {
                id
                speckleType
                data
            }
        }
    }
""")

subscription_query = gql("""
    subscription ProjectVersionsUpdated($projectId: String!) {
        projectVersionsUpdated(id: $projectId) {
            id
            modelId
            type
            version {
                id
                message
                createdAt
            }
        }
    }
""")

# Separate query to fetch full version details (sourceApplication, authorUser)
# since the subscription payload doesn't include these fields
version_details_query = gql("""
    query GetVersionDetails($projectId: String!, $versionId: String!) {
        project(id: $projectId) {
            version(id: $versionId) {
                id
                message
                createdAt
                sourceApplication
                authorUser {
                    name
                    id
                }
            }
        }
    }
""")





async def subscribe_to_project_updates():
    """
    Subscribe to project version updates using WebSocket
    """
    # Create WebSocket transport with authentication
    transport = WebsocketsTransport(
        url="wss://app.speckle.systems/graphql",
        init_payload={
            "Authorization": f"Bearer {YOUR_TOKEN}"
        }
    )
    
    # Create a GraphQL client
    client = Client(
        transport=transport,
        fetch_schema_from_transport=False,
    )
    
    try:
        async with client as session:
            print(f"🔌 Connected to Speckle WebSocket")
            print(f"📡 Listening for updates on project: {PROJECT_ID}")
            print("Press Ctrl+C to stop\n")
            
            try:
                # Subscribe to the query
                async for result in session.subscribe(
                    subscription_query,
                    variable_values={"projectId": PROJECT_ID}
                ):
                    print("=" * 50)
                    print("📦 New Update Received!")
                    print("=" * 50)
                    
                    data = result.get("projectVersionsUpdated")
                    if data:
                        print(f"ID: {data.get('id')}")
                        print(f"Model ID: {data.get('modelId')}")
                        print(f"Type: {data.get('type')}")

                        version = data.get('version')
                        if version:
                            version_id = version.get('id')
                            print(f"\nVersion Details (from subscription):")
                            print(f"  - Version ID: {version_id}")
                            print(f"  - Message: {version.get('message')}")
                            print(f"  - Created At: {version.get('createdAt')}")

                            # Fetch full version details via HTTP query
                            speckle_client = get_client()
                            try:
                                detail_result = speckle_client.httpclient.execute(
                                    version_details_query,
                                    variable_values={"projectId": PROJECT_ID, "versionId": version_id}
                                )
                                full_version = detail_result.get("project", {}).get("version", {})
                                authorUser = full_version.get('authorUser') or {}

                                print(f"\nExtra Details (from follow-up query):")
                                print(f"  - Source Application: {full_version.get('sourceApplication')}")
                                print(f"  - Author: {authorUser.get('name')} (id: {authorUser.get('id')})")

                                version_info = {
                                    "versionId": version_id,
                                    "message": version.get('message'),
                                    "createdAt": version.get('createdAt'),
                                    "sourceApplication": full_version.get('sourceApplication'),
                                    "authorName": authorUser.get('name'),
                                    "authorId": authorUser.get('id'),
                                }
                            except Exception as e:
                                print(f"  ⚠ Could not fetch version details: {e}")
                                version_info = {
                                    "versionId": version_id,
                                    "message": version.get('message'),
                                    "createdAt": version.get('createdAt'),
                                }

                            export_object_data(speckle_client, version_info=version_info)

                        print("\n")
                    
            except asyncio.CancelledError:
                print("\n\n👋 Subscription cancelled")
                raise
            except KeyboardInterrupt:
                print("\n\n👋 Subscription stopped by user")
                raise
            
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        # Ensure transport is properly closed
        await transport.close()
        print("🔌 Connection closed properly")


if __name__ == "__main__":
    asyncio.run(subscribe_to_project_updates())