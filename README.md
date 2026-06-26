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

## Using the colcon tools from Claude

- Start the MCP server from the workspace root or pass an absolute `workspace_path` when calling tools.
- Ensure the Python environment running the server has both `mcp` and `colcon` installed and available on `PATH`.
- Recommended tool calls:
  - `colcon_status(workspace_path="/home/kamren/Kinova_MCP_tools")`
  - `colcon_build(workspace_path="/home/kamren/Kinova_MCP_tools")`
  - `colcon_test(workspace_path="/home/kamren/Kinova_MCP_tools")`
  - `colcon_latest_log(workspace_path="/home/kamren/Kinova_MCP_tools", max_lines=200)`

These tools work through Claude as long as the MCP server is reachable and the configured process has access to the workspace and `colcon` binary.

## Available Tools (Current Stubs)

The `kinova_mcp_server.py` provides the following tools. You will need to fill in the actual `subprocess` or `rclpy` logic for some of them.
- `get_robot_state`: Fetches ROS 2 `/joint_states` via CLI.
- `manage_ros_launch`: Start/stop launch files.
- `capture_workspace_image`: Pulls an image from the cameras.
- `run_dry_insertion_test`: Tests insertion logic.
- `manage_isaac_sim`: Starts Isaac Sim.
- `fetch_kinova_diagnostics`: Reads logs from the Kinova controller.
- `clear_robot_faults`: Clears protective stops.
- `remote_ssh_exec`: Run a shell command on the remote Kinova desktop at `kinova@10.12.140.145`.
- `inspect_installed_packages`: Inspect installed packages locally or remotely, including system packages, Python packages, ROS 1 packages, and ROS 2 packages.
- `install_packages_ssh`: Install packages remotely via SSH using `apt` or `pip`.
- `scp_upload`: Copy a local file or directory to the remote host.
- `scp_download`: Copy a file or directory from the remote host to local storage.
- `rsync_to_remote`: Sync a local path to the remote host.
- `rsync_from_remote`: Sync a remote path from the remote host to local storage.
- `check_remote_usage_status`: Check current remote users, SSH sessions, ROS node/topic activity, and camera device usage.
- `colcon_status`: Check whether `colcon` is currently running and report the last build time and latest log file.
- `colcon_last_build_time`: Return the timestamp of the latest colcon build artifacts.
- `colcon_build`: Run `colcon build` in the workspace, optionally selecting packages and passing extra arguments.
- `colcon_test`: Run `colcon test` in the workspace, optionally selecting packages and passing extra arguments.
- `colcon_latest_log`: Return the contents of the latest colcon log file, limited to the last N lines.
- `ros2_launch_manage`: Start or stop a ROS 2 launch and track the process for clean shutdown.
- `workspace_source_status`: Check if the workspace install/setup.bash is present and environment variables are set after sourcing.
- `colcon_build_status`: Summarize the latest colcon build log for errors and warnings.
- `fetch_ros2_nodes_and_topics`: List active ROS 2 nodes, topics, and services.
- `robot_health_summary`: Return a brief robot health summary using ROS 2 diagnostics and node/topic state.
- `camera_snapshot`: Capture a single camera frame to a local image file.
- `remote_log_search`: Search local or remote logs for a keyword.
- `sync_workspace`: Show git status and optional diff summary for the workspace.
- `system_resource_report`: Report uptime, memory, disk, and optional GPU usage.

## Remote access notes

These tools rely on the local machine having SSH access to the Kinova desktop. For best results:

- Configure `~/.ssh/config` with an alias like:
  ```text
  Host real-1
    HostName <DEKSTOP_IP>
    User kinova
    IdentityFile ~/.ssh/id_rsa
  ```
- Use SSH key-based auth so the MCP server can connect without interactive password prompts.

## Customizing

Open `kinova_mcp_server.py` and modify the implementations under the `@mcp.tool()` decorators. You can replace the `[Stub]` returns with actual `subprocess.run` calls, `subprocess.Popen` for long-running nodes, or utilize the `kortex_api` directly.
