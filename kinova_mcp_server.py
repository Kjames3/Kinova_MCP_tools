import os
import subprocess
import json
from mcp.server.fastmcp import FastMCP

# Create an MCP server for Kinova Gen3
mcp = FastMCP("Kinova MCP Tools")

@mcp.tool()
def get_robot_state() -> str:
    """
    Retrieves the current joint states of the robot using standard ROS 2 CLI.
    This fetches the latest message from the /joint_states topic.
    """
    try:
        result = subprocess.run(
            ['ros2', 'topic', 'echo', '/joint_states', '--once'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error fetching state: {result.stderr}"
    except Exception as e:
        return f"Exception occurred while calling ros2 CLI: {str(e)}"

@mcp.tool()
def manage_ros_launch(launch_file: str, action: str) -> str:
    """
    Manage ROS 2 launch files.
    Arguments:
      - launch_file: The name of the launch file (e.g. 'gen3_complete_system.launch.py')
      - action: 'start' or 'stop'
    """
    if action == "start":
        return f"[Stub] Would execute: ros2 launch kortex_bringup {launch_file}. Modify server to use subprocess.Popen."
    elif action == "stop":
        return f"[Stub] Would terminate the process running {launch_file}."
    return "Invalid action. Use 'start' or 'stop'."

@mcp.tool()
def capture_workspace_image() -> str:
    """
    Capture an image from the workspace cameras (e.g., from combine_cameras.py).
    Returns the file path of the captured image so the AI agent can read it.
    """
    return "[Stub] Image capture not yet implemented. Would normally subscribe to /camera/color/image_raw and save to disk."

@mcp.tool()
def run_dry_insertion_test() -> str:
    """
    Run the insertion test script (insert_to_container.py) to validate trajectories.
    """
    return "[Stub] Would run: python3 /home/kamren/workspace/ros2_kortex_ws/src/Kinova_surgical_arm_UCR/surgical_arm_bringup/scripts/insert_to_container.py"

@mcp.tool()
def manage_isaac_sim(action: str) -> str:
    """
    Start or stop the Isaac Sim Gen3 environment (isaac_sim_gen3.py).
    Arguments:
      - action: 'start' or 'stop'
    """
    return f"[Stub] Would {action} Isaac Sim script."

@mcp.tool()
def fetch_kinova_diagnostics() -> str:
    """
    Fetch diagnostics from the Kinova controller via Kortex API or REST API.
    """
    return "[Stub] Diagnostics fetch not implemented. Requires Kinova API credentials."

@mcp.tool()
def clear_robot_faults() -> str:
    """
    Clear hardware or protective faults on the Kinova arm.
    """
    return "[Stub] Fault clearing not implemented. Use Kortex API."

if __name__ == "__main__":
    # Initialize and run the server using standard stdio transport for MCP
    mcp.run()
