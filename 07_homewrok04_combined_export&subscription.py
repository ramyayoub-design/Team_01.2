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


YOUR_TOKEN = os.environ.get("SPECKLE_TOKEN")
PROJECT_ID = "128262a20c"
OBJECT_ID = "d93c59904f275b13dd1eb0d3c2472c5e"


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





async def subscribe_and_export():
    """Listen for updates and auto-export on changes."""
    speckle_client = get_client()
    print(f"✓ Authenticated with Speckle")
    
    # Initial export
    print("📦 Running initial export...")
    export_object_data(speckle_client)
    
    transport = WebsocketsTransport(
        url="wss://app.speckle.systems/graphql",
        init_payload={"Authorization": f"Bearer {YOUR_TOKEN}"}
    )
    
    client = Client(transport=transport, fetch_schema_from_transport=False)
    
    try:
        async with client as session:
            print(f"\n🔌 Connected - listening for updates on project: {PROJECT_ID}")
            print("Press Ctrl+C to stop\n")
            
            async for result in session.subscribe(
                subscription_query,
                variable_values={"projectId": PROJECT_ID}
            ):
                data = result.get("projectVersionsUpdated")
                if data:
                    print(f"\n📡 Update detected: {data.get('type')} on model {data.get('modelId')}")
                    
                    version_info = {
                        "id": data.get("version", {}).get("id"),
                        "message": data.get("version", {}).get("message"),
                        "createdAt": data.get("version", {}).get("createdAt")
                    }
                    
                    export_object_data(speckle_client, version_info)
                    
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n👋 Stopped")
    finally:
        await transport.close()


if __name__ == "__main__":
    asyncio.run(subscribe_and_export())