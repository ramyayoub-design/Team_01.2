"""
01 - Create a Speckle Project

This script demonstrates how to create a new model in an existing Speckle project
with a folder structure using forward slashes in the name.

NOTE: You need the PROJECT_ID of the existing project that contains the
CW26-Sessions/homework/session03 folder structure.
You can find it in the URL: https://app.speckle.systems/projects/PROJECT_ID
"""

from main import get_client
from specklepy.core.api.inputs.model_inputs import CreateModelInput


# TODO: Replace with your project ID
# You can find it in the URL when you open your project in Speckle web:
# https://app.speckle.systems/projects/PROJECT_ID

PROJECT_ID = "128262a20c"

def main():
    # Authenticate
    client = get_client()

    if PROJECT_ID == "your_project_id":
        print("\n⚠ You need to set PROJECT_ID in this script.")
        print("Find it in the Speckle project URL:")
        print("https://app.speckle.systems/projects/YOUR_PROJECT_ID")
        return

    # Create a new model with folder structure
    # The "/" in the name creates folders: homework > session03 > Team_01.2
    model = client.model.create(CreateModelInput(
        project_id=PROJECT_ID,
        name="homework/session03/Team_01.2",
        description="Tower project for team 01.2"
    ))

    print(f"✓ Created model: {model.id}")
    print(f"  Model will appear in folder: homework/session03/Team_01.2")

    # Get the model details
    model_details = client.model.get(model.id, PROJECT_ID)
    print(f"  Model name: {model_details.name}")
    print(f"  Description: {model_details.description}")


if __name__ == "__main__":
    main()



