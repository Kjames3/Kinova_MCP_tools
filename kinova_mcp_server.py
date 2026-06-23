import os
import subprocess
import json
import shlex
import sys
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

@mcp.tool()
def remote_ssh_exec(
    command: str,
    host: str = "kinova@10.12.140.145",
    timeout: int = 60,
) -> str:
    """
    Execute a command on the remote Kinova desktop via SSH.
    """
    try:
        result = subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "StrictHostKeyChecking=accept-new",
                host,
                command,
            ],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            return result.stdout
        return f"SSH exit {result.returncode}\nstderr:\n{result.stderr}"
    except Exception as e:
        return f"SSH exception: {e}"

@mcp.tool()
def inspect_installed_packages(
    context: str = "local",
    include_ros: bool = True,
    include_python: bool = True,
    include_system: bool = True,
    host: str = "kinova@10.12.140.145",
) -> str:
    """
    Inspect installed packages locally or on a remote host.

    Arguments:
      - context: 'local' or 'remote'
      - include_ros: include ROS 1 and ROS 2 package listings
      - include_python: include Python packages
      - include_system: include OS-level packages
      - host: remote SSH host when context is 'remote'
    """
    if context not in {"local", "remote"}:
        return "Invalid context. Use 'local' or 'remote'."

    section_commands = []
    if include_system:
        section_commands.append("echo '=== SYSTEM PACKAGES ==='")
        section_commands.append(
            "if command -v dpkg >/dev/null 2>&1; then \
                dpkg-query -W -f='${Package} ${Version}\\n' | sort; \
             elif command -v rpm >/dev/null 2>&1; then \
                rpm -qa | sort; \
             else \
                echo 'No supported system package manager found'; \
             fi"
        )
    if include_python:
        section_commands.append("echo '\n=== PYTHON PACKAGES ==='")
        python_cmd = "python3" if context == "remote" else shlex.quote(sys.executable)
        section_commands.append(f"{python_cmd} -m pip list --format=columns || true")
    if include_ros:
        section_commands.append("echo '\n=== ROS 1 PACKAGES ==='")
        section_commands.append(
            "if command -v rospack >/dev/null 2>&1; then rospack list | sort; else echo 'rospack not available'; fi"
        )
        section_commands.append("echo '\n=== ROS 2 PACKAGES ==='")
        section_commands.append(
            "if command -v ros2 >/dev/null 2>&1; then ros2 pkg list | sort; else echo 'ros2 CLI not available'; fi"
        )

    if not section_commands:
        return "No package categories requested."

    full_command = " && ".join(section_commands)
    if context == "remote":
        return remote_ssh_exec(full_command, host)

    try:
        result = subprocess.run(full_command, shell=True, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return result.stdout
        return f"Local inspect exit {result.returncode}\nstderr:\n{result.stderr}"
    except Exception as e:
        return f"Local inspect exception: {e}"

@mcp.tool()
def install_packages_ssh(
    packages: str,
    manager: str = "apt",
    host: str = "kinova@10.12.140.145",
    use_sudo: bool = True,
    timeout: int = 300,
) -> str:
    """
    Install packages on the remote host via SSH.

    Arguments:
      - packages: space-separated list of package names to install
      - manager: 'apt' or 'pip'
      - host: remote SSH host
      - use_sudo: whether to run installation with sudo (for apt)
      - timeout: SSH command timeout in seconds
    """
    if not packages.strip():
        return "No packages specified."

    package_args = " ".join(shlex.quote(token) for token in shlex.split(packages))
    if manager == "apt":
        sudo_prefix = "sudo " if use_sudo else ""
        remote_command = f"{sudo_prefix}apt-get update -y && {sudo_prefix}apt-get install -y {package_args}"
    elif manager == "pip":
        remote_command = f"python3 -m pip install {package_args}"
    else:
        return "Unsupported manager. Use 'apt' or 'pip'."

    return remote_ssh_exec(remote_command, host, timeout=timeout)

@mcp.tool()
def scp_upload(local_path: str, remote_path: str, host: str = "kinova@10.12.140.145") -> str:
    """
    Copy a local file or directory to the remote Kinova machine.
    """
    try:
        result = subprocess.run(
            [
                "scp",
                "-o",
                "BatchMode=yes",
                "-r",
                local_path,
                f"{host}:{remote_path}",
            ],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            return f"Uploaded {local_path} to {host}:{remote_path}"
        return f"SCP upload exit {result.returncode}\nstderr:\n{result.stderr}"
    except Exception as e:
        return f"SCP upload exception: {e}"

@mcp.tool()
def scp_download(remote_path: str, local_path: str, host: str = "kinova@10.12.140.145") -> str:
    """
    Copy a file or directory from the remote Kinova machine to the local host.
    """
    try:
        result = subprocess.run(
            [
                "scp",
                "-o",
                "BatchMode=yes",
                "-r",
                f"{host}:{remote_path}",
                local_path,
            ],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            return f"Downloaded {host}:{remote_path} to {local_path}"
        return f"SCP download exit {result.returncode}\nstderr:\n{result.stderr}"
    except Exception as e:
        return f"SCP download exception: {e}"

@mcp.tool()
def rsync_to_remote(local_path: str, remote_path: str, host: str = "kinova@10.12.140.145") -> str:
    """
    Sync a local path to the remote Kinova machine using rsync.
    """
    try:
        result = subprocess.run(
            [
                "rsync",
                "-avz",
                "-e",
                "ssh -o StrictHostKeyChecking=no -o BatchMode=yes",
                local_path,
                f"{host}:{remote_path}",
            ],
            capture_output=True,
            text=True,
            timeout=180
        )
        if result.returncode == 0:
            return result.stdout or f"Rsync to {host}:{remote_path} completed successfully."
        return f"Rsync upload exit {result.returncode}\nstderr:\n{result.stderr}"
    except Exception as e:
        return f"Rsync upload exception: {e}"

@mcp.tool()
def rsync_from_remote(remote_path: str, local_path: str, host: str = "kinova@10.12.140.145") -> str:
    """
    Sync a remote path from the Kinova machine to the local host using rsync.
    """
    try:
        result = subprocess.run(
            [
                "rsync",
                "-avz",
                "-e",
                "ssh -o BatchMode=yes",
                f"{host}:{remote_path}",
                local_path,
            ],
            capture_output=True,
            text=True,
            timeout=180
        )
        if result.returncode == 0:
            return result.stdout or f"Rsync from {host}:{remote_path} completed successfully."
        return f"Rsync download exit {result.returncode}\nstderr:\n{result.stderr}"
    except Exception as e:
        return f"Rsync download exception: {e}"

@mcp.tool()
def check_remote_usage_status(host: str = "kinova@10.12.140.145") -> str:
    """
    Check whether another user is actively using the arm or cameras on the remote Kinova desktop.
    """
    remote_command = r"""
set -e

echo '=== ACTIVE USERS ==='
who || true

echo
echo '=== SSH SESSIONS ==='
ps -eo user,pid,cmd | grep -E 'ssh|sshd' | grep -v grep || true

echo
echo '=== ROS 2 CAMERA/ARM ACTIVITY ==='
if command -v ros2 >/dev/null 2>&1; then
  ros2 node list 2>/dev/null || echo 'ros2 node list unavailable'
  echo '---'
  ros2 topic list 2>/dev/null | grep -E 'camera|image|depth|joint|arm|kinova' || echo 'No ROS camera/arm topics found'
else
  echo 'ros2 CLI not available on remote host'
fi

echo
echo '=== CAMERA DEVICE USAGE ==='
for dev in /dev/video*; do
  if [ -e "$dev" ]; then
    echo "Device: $dev"
    if command -v lsof >/dev/null 2>&1; then
      lsof "$dev" 2>/dev/null || echo '  no process holding device'
    elif command -v fuser >/dev/null 2>&1; then
      fuser -v "$dev" 2>/dev/null || echo '  no process holding device'
    else
      echo '  neither lsof nor fuser available'
    fi
  fi
 done
"""
    return remote_ssh_exec(remote_command, host)

if __name__ == "__main__":
    # Initialize and run the server using standard stdio transport for MCP
    mcp.run()
