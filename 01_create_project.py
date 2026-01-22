"""
01 - Create a Speckle Project

This script demonstrates how to create a new project in Speckle
and retrieve its details.

NOTE: Projects must belong to a workspace. You can find your workspace ID
in the Speckle web interface URL:# https://app.speckle.systems/settings/workspaces/macad-iaac/general
"""

from main import get_client
from specklepy.core.api.inputs.project_inputs import WorkspaceProjectCreateInput
from specklepy.core.api.enums import ProjectVisibility


# TODO: Replace with your workspace ID
# You can find it in the URL when you open your workspace in Speckle web:
# https://app.speckle.systems/settings/workspaces/macad-iaac/general

WORKSPACE_ID = "a1cd06bae2"


def main():
    # Authenticate
    client = get_client()

    if WORKSPACE_ID == "your_workspace_id":
        # List available workspaces to help the user
        print("\n⚠ You need to set WORKSPACE_ID. Here are your workspaces:\n")
        workspaces = client.active_user.get_workspaces()
        for ws in workspaces.items:
            print(f"  • {ws.name}: {ws.id}")
        print("\nCopy one of the IDs above and set WORKSPACE_ID in this script.")
        return

    # Create a new project inside the workspace
    project = client.project.create_in_workspace(WorkspaceProjectCreateInput(
        name="CW26-Sessions/homework/session03/Team_01.2",
        description="modify the tower project to create a new project for team 01.2",
        visibility=ProjectVisibility.PRIVATE,
        workspaceId=WORKSPACE_ID
    ))

    print(f"✓ Created project: {project.id}")

    # Get the project details
    project = client.project.get(project.id)
    print(f"  Project name: {project.name}")
    print(f"  Description:  {project.description}")
    print(f"  Visibility:   {project.visibility}")


if __name__ == "__main__":
    main()

