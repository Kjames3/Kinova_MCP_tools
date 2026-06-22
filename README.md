# Kinova MCP Tools

This directory contains a Model Context Protocol (MCP) server tailored for interacting with the Kinova Gen3 ROS 2 workspace.
It allows AI assistants (like Claude, this IDE, etc.) to securely trigger ROS 2 commands, check robot states, and manage simulation/vision tasks.

## Setup

1. **Create a Virtual Environment (Optional but Recommended)**
   ```bash
   cd ~/Kinova_MCP_Tools
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies**
   Install the MCP Python SDK:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Ensure you are using Python 3.10+)*

## Running the Server Manually

To test if the server boots without issues:
```bash
python kinova_mcp_server.py
```
*(It will run and listen on stdin/stdout as expected by the MCP standard. Press `Ctrl+C` to exit.)*

## Configuring your AI Assistant

To use these tools with an MCP-compatible client (such as Claude Desktop or another editor), you need to add this server to your MCP configuration file (typically `mcp_settings.json` or `claude_desktop_config.json`).

Example configuration:
```json
{
  "mcpServers": {
    "kinova_tools": {
      "command": "/usr/bin/python3",
      "args": [
        "/home/kamren/Kinova_MCP_Tools/kinova_mcp_server.py"
      ],
      "env": {
        "ROS_DOMAIN_ID": "0",
        "PYTHONPATH": "/opt/ros/humble/lib/python3.10/site-packages"
      }
    }
  }
}
```
*Note: Make sure to point the `command` to the python executable where `mcp` is installed, and ensure the necessary ROS 2 environment variables are sourced or provided in the `env` block.*

## Available Tools (Current Stubs)

The `kinova_mcp_server.py` provides the following tools. You will need to fill in the actual `subprocess` or `rclpy` logic for some of them.
- `get_robot_state`: Fetches ROS 2 `/joint_states` via CLI.
- `manage_ros_launch`: Start/stop launch files.
- `capture_workspace_image`: Pulls an image from the cameras.
- `run_dry_insertion_test`: Tests insertion logic.
- `manage_isaac_sim`: Starts Isaac Sim.
- `fetch_kinova_diagnostics`: Reads logs from the Kinova controller.
- `clear_robot_faults`: Clears protective stops.

## Customizing

Open `kinova_mcp_server.py` and modify the implementations under the `@mcp.tool()` decorators. You can replace the `[Stub]` returns with actual `subprocess.run` calls, `subprocess.Popen` for long-running nodes, or utilize the `kortex_api` directly.
