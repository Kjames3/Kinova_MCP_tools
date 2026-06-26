import os
import signal
import shutil
import subprocess
import tempfile
import json
import re
import shlex
import sys
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Create an MCP server for Kinova Gen3
mcp = FastMCP("Kinova MCP Tools")
_ros2_launch_processes: dict[str, subprocess.Popen] = {}

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

@mcp.tool()
def ros2_launch_manage(
    package: str,
    launch_file: str,
    action: str = "start",
    extra_args: str = "",
    workspace_path: str = ".",
) -> str:
    """
    Start or stop a ROS 2 launch file and track the process.

    Arguments:
      - package: ROS 2 package name containing the launch file.
      - launch_file: Launch file name.
      - action: "start" or "stop".
      - extra_args: extra arguments to pass to ros2 launch.
      - workspace_path: workspace root for relative launch paths.
    """
    try:
        workspace = _resolve_workspace_path(workspace_path)
    except ValueError as exc:
        return str(exc)

    key = f"{package}:{launch_file}"
    if action == "start":
        if key in _ros2_launch_processes:
            proc = _ros2_launch_processes[key]
            if proc.poll() is None:
                return f"Launch already running: {key} (pid {proc.pid})"
            del _ros2_launch_processes[key]

        cmd = ["ros2", "launch", package, launch_file]
        if extra_args.strip():
            cmd.extend(shlex.split(extra_args))

        try:
            stdout_file = tempfile.TemporaryFile(mode="w+b")
            stderr_file = tempfile.TemporaryFile(mode="w+b")
            proc = subprocess.Popen(
                cmd,
                cwd=workspace,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=True,
            )
            _ros2_launch_processes[key] = proc
            return f"Started launch {key} with PID {proc.pid}."
        except Exception as exc:
            return f"Failed to start launch {key}: {exc}"
    elif action == "stop":
        proc = _ros2_launch_processes.get(key)
        if proc and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except Exception:
                pass
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    pass
                proc.wait()
            del _ros2_launch_processes[key]
            return f"Stopped launch {key}."

        # Fallback to pkill if the tracked process is missing.
        try:
            safe_pattern = re.escape(f"ros2 launch {package} {launch_file}")
            result = subprocess.run(
                ["pkill", "-f", safe_pattern],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return f"Stopped launch {key} via pkill."
            return f"No running launch process found for {key}."
        except Exception as exc:
            return f"Error stopping launch {key}: {exc}"
    return "Invalid action. Use 'start' or 'stop'."

@mcp.tool()
def workspace_source_status(workspace_path: str = ".") -> str:
    """
    Check whether a ROS 2 workspace is sourced correctly.
    """
    try:
        workspace = _resolve_workspace_path(workspace_path)
    except ValueError as exc:
        return str(exc)

    setup_path = os.path.join(workspace, "install", "setup.bash")
    if not os.path.isfile(setup_path):
        return f"Workspace setup file not found: {setup_path}"

    bash_script = (
        "source \"$SETUP_PATH\" >/dev/null 2>&1 && python3 - <<'PY'\n"
        "import os, json\n"
        "print(json.dumps({\"AMENT_PREFIX_PATH\": os.getenv(\"AMENT_PREFIX_PATH\"), \"PYTHONPATH\": os.getenv(\"PYTHONPATH\"), \"COLCON_PREFIX_PATH\": os.getenv(\"COLCON_PREFIX_PATH\"), \"ROS_PACKAGE_PATH\": os.getenv(\"ROS_PACKAGE_PATH\")}))\n"
        "PY"
    )
    try:
        result = subprocess.run(
            ["bash", "-c", bash_script],
            env={**os.environ, "SETUP_PATH": setup_path},
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return f"Workspace source check failed: {result.stderr.strip()}"
        env_json = json.loads(result.stdout.strip())
        lines = [f"Workspace sourced from {setup_path}"]
        for name, value in env_json.items():
            lines.append(f"{name}: {value or '<not set>'}")
        return "\n".join(lines)
    except Exception as exc:
        return f"Workspace source status error: {exc}"

@mcp.tool()
def colcon_build_status(workspace_path: str = ".") -> str:
    """
    Summarize the latest colcon build log for warnings and errors.
    """
    try:
        workspace = _resolve_workspace_path(workspace_path)
    except ValueError as exc:
        return str(exc)

    log_file = _find_colcon_log_file(workspace)
    if not log_file:
        return "No colcon log file found in this workspace."

    try:
        tail_text, truncated = _tail_file_path(log_file, 1000)
        lines = tail_text.splitlines()
        errors = [line for line in lines if re.search(r"\b(error|failed?)\b", line, re.I)]
        warnings = [line for line in lines if re.search(r"\bwarning\b", line, re.I)]
        summary = [f"Latest log file: {os.path.relpath(log_file, workspace)}"]
        if truncated:
            summary.append("--- tail of latest log (last 1000 lines) ---")
        summary.append(f"Errors: {len(errors)}")
        summary.append(f"Warnings: {len(warnings)}")
        if errors:
            summary.append("Last error lines:")
            summary.extend(errors[-10:])
        elif warnings:
            summary.append("Last warning lines:")
            summary.extend(warnings[-10:])
        else:
            summary.append("No error or warning patterns found in the latest log tail.")
        return "\n".join(summary)
    except Exception as exc:
        return f"Error summarizing colcon build log: {exc}"

@mcp.tool()
def fetch_ros2_nodes_and_topics() -> str:
    """
    Return active ROS 2 nodes, topics, and services.
    """
    if not shutil.which("ros2"):
        return "ros2 CLI not available."

    commands = [
        ["ros2", "node", "list"],
        ["ros2", "topic", "list"],
        ["ros2", "service", "list"],
    ]
    output = []
    for cmd in commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            label = cmd[1] if len(cmd) > 1 else "ros2"
            output.append(f"=== {' '.join(cmd)} ===")
            if result.returncode != 0:
                stderr = result.stderr.strip() or "<no stderr>"
                output.append(f"Command failed (exit {result.returncode}): {stderr}")
            else:
                output.append(result.stdout.strip() or "<none>")
        except Exception as exc:
            output.append(f"Error running {' '.join(cmd)}: {exc}")
    return "\n".join(output)

@mcp.tool()
def robot_health_summary() -> str:
    """
    Collect a summary of ROS 2 robot health and diagnostics.
    """
    if not shutil.which("ros2"):
        return "ros2 CLI not available."

    try:
        node_result = subprocess.run(
            ["ros2", "node", "list"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        topic_result = subprocess.run(
            ["ros2", "topic", "list"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception as exc:
        return f"Failed to query ROS 2 state: {exc}"

    if node_result.returncode != 0:
        node_section = f"ros2 node list failed (exit {node_result.returncode}): {node_result.stderr.strip() or '<no stderr>'}"
    else:
        node_section = node_result.stdout.strip() or "<none>"

    if topic_result.returncode != 0:
        topic_section = f"ros2 topic list failed (exit {topic_result.returncode}): {topic_result.stderr.strip() or '<no stderr>'}"
    else:
        topic_section = topic_result.stdout.strip() or "<none>"

    diagnostics_output = "<diagnostics topic not found>"
    if topic_result.returncode == 0:
        topics = {line.strip() for line in topic_result.stdout.splitlines() if line.strip()}
        if "/diagnostics" in topics:
            try:
                diag_result = subprocess.run(
                    ["ros2", "topic", "echo", "/diagnostics", "--once"],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
            if diag_result.returncode != 0:
                diagnostics_output = f"/diagnostics echo failed (exit {diag_result.returncode}): {diag_result.stderr.strip() or '<no stderr>'}"
            else:
                diagnostics_output = diag_result.stdout.strip()[:2000] or "<diagnostics topic empty>"
        except Exception as exc:
            diagnostics_output = f"<failed to read /diagnostics: {exc}>"

    return (
        "ROS 2 Robot Health Summary:\n"
        f"Nodes:\n{node_section}\n"
        f"Topics:\n{topic_section}\n"
        f"Diagnostics sample:\n{diagnostics_output}"
    )

@mcp.tool()
def camera_snapshot(
    output_path: str = "/tmp/kinova_camera_snapshot.jpg",
    device: str = "/dev/video0",
) -> str:
    """
    Capture a single image from the first available camera device.
    """
    if not shutil.which("ffmpeg"):
        return "ffmpeg is not installed."

    if not os.path.exists(device):
        devices = [dev for dev in ["/dev/video0", "/dev/video1"] if os.path.exists(dev)]
        if not devices:
            return "No /dev/video device nodes found."
        device = devices[0]

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "v4l2",
                "-video_size",
                "640x480",
                "-i",
                device,
                "-frames:v",
                "1",
                output_path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return f"Snapshot saved to {output_path}"
        return f"ffmpeg failed: {result.stderr.strip()}"
    except Exception as exc:
        return f"Failed to capture camera snapshot: {exc}"

@mcp.tool()
def remote_log_search(
    keyword: str,
    path: str = ".",
    host: str = "",
    max_matches: int = 50,
) -> str:
    """
    Search local or remote logs for a keyword.
    """
    try:
        max_matches = int(max_matches)
    except (TypeError, ValueError):
        max_matches = 50
    max_matches = max(1, min(max_matches, 200))

    if host:
        quoted_path = shlex.quote(path)
        quoted_keyword = shlex.quote(keyword)
        search_cmd = (
            f"grep -RIn --exclude-dir=.git --max-count={max_matches} {quoted_keyword} {quoted_path}; "
            "rc=$?; if [ $rc -eq 1 ]; then echo '__NO_MATCHES__'; exit 0; fi; exit $rc"
        )
        remote_output = remote_ssh_exec(search_cmd, host)
        if remote_output.strip() == "__NO_MATCHES__":
            return f"No matches for {keyword} in {path}."
        return remote_output

    if not os.path.isdir(path):
        return f"Search path does not exist: {path}"

    try:
        result = subprocess.run(
            ["grep", "-RIn", "--exclude-dir=.git", f"--max-count={max_matches}", keyword, path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode not in (0, 1):
            stderr = result.stderr.strip() or "<no stderr>"
            return f"grep failed (exit {result.returncode}): {stderr}"
        return result.stdout.strip() or f"No matches for {keyword} in {path}."
    except Exception as exc:
        return f"Failed searching logs: {exc}"

@mcp.tool()
def sync_workspace(workspace_path: str = ".", include_diff: bool = False) -> str:
    """
    Return git workspace status and optional diff summary.
    """
    try:
        workspace = _resolve_workspace_path(workspace_path)
    except ValueError as exc:
        return str(exc)

    if not os.path.isdir(os.path.join(workspace, ".git")):
        return "Not a git repository."

    status = []
    try:
        status_result = subprocess.run(
            ["git", "status", "--short"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=20,
        )
        status.append("=== git status --short ===")
        if status_result.returncode != 0:
            status.append(f"git status failed (exit {status_result.returncode}): {status_result.stderr.strip()}")
        else:
            status.append(status_result.stdout.strip() or "Clean working tree.")
        if include_diff:
            diff_result = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=20,
            )
            status.append("=== git diff --stat ===")
            if diff_result.returncode != 0:
                status.append(f"git diff failed (exit {diff_result.returncode}): {diff_result.stderr.strip()}")
            else:
                status.append(diff_result.stdout.strip() or "No diff changes.")
        return "\n".join(status)
    except Exception as exc:
        return f"Workspace sync failed: {exc}"

@mcp.tool()
def system_resource_report() -> str:
    """
    Return a brief system resource usage summary.
    """
    parts = []
    try:
        uptime = subprocess.run(
            ["uptime"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        parts.append(f"Uptime: {uptime.stdout.strip()}")
    except Exception as exc:
        parts.append(f"Uptime failed: {exc}")

    try:
        free = subprocess.run(
            ["free", "-h"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        parts.append("=== Memory ===")
        parts.append(free.stdout.strip())
    except Exception as exc:
        parts.append(f"Memory check failed: {exc}")

    try:
        df = subprocess.run(
            ["df", "-h", "."],
            capture_output=True,
            text=True,
            timeout=10,
        )
        parts.append("=== Disk ===")
        parts.append(df.stdout.strip())
    except Exception as exc:
        parts.append(f"Disk check failed: {exc}")

    if shutil.which("nvidia-smi"):
        try:
            nvidia = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            parts.append("=== GPU ===")
            parts.append(nvidia.stdout.strip() or "No GPU usage data.")
        except Exception as exc:
            parts.append(f"GPU check failed: {exc}")

    return "\n".join(parts)

def _resolve_workspace_path(workspace_path: str) -> str:
    workspace_path = workspace_path or "."
    abs_path = os.path.abspath(os.path.expanduser(workspace_path))
    if not os.path.isdir(abs_path):
        raise ValueError(f"Workspace path does not exist or is not a directory: {abs_path}")
    return abs_path

def _find_last_colcon_build_time(workspace_path: str) -> str:
    candidates = []
    for name in ["log/latest_build", "build", "install"]:
        path = os.path.join(workspace_path, name)
        if os.path.exists(path):
            candidates.append(path)
    if not candidates:
        return "No colcon build artifacts found in this workspace."

    latest = max(candidates, key=lambda p: os.path.getmtime(p))
    timestamp = datetime.fromtimestamp(os.path.getmtime(latest))
    return f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} (artifact: {os.path.relpath(latest, workspace_path)})"

def _find_colcon_log_file(workspace_path: str) -> str | None:
    log_dir = os.path.join(workspace_path, "log")
    if not os.path.isdir(log_dir):
        return None

    candidates = []
    for root, _, files in os.walk(log_dir):
        for file_name in files:
            if file_name.endswith(".log"):
                candidates.append(os.path.join(root, file_name))
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def _tail_file_path(file_path: str, max_lines: int) -> tuple[str, bool]:
    if max_lines <= 0:
        return "", False

    block_size = 8192
    with open(file_path, "rb") as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        if file_size == 0:
            return "", False

        data = bytearray()
        lines_found = 0
        pos = file_size
        while pos > 0 and lines_found <= max_lines:
            read_size = min(block_size, pos)
            pos -= read_size
            f.seek(pos)
            chunk = f.read(read_size)
            data[:0] = chunk
            lines_found += chunk.count(b"\n")

    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    if len(lines) <= max_lines:
        return text, False
    return "".join(lines[-max_lines:]), True


def _tail_file_obj(file_obj, max_lines: int) -> str:
    if max_lines <= 0:
        return ""

    block_size = 8192
    file_obj.seek(0, os.SEEK_END)
    pos = file_obj.tell()
    if pos == 0:
        return ""

    data = bytearray()
    lines_found = 0
    while pos > 0 and lines_found <= max_lines:
        read_size = min(block_size, pos)
        pos -= read_size
        file_obj.seek(pos)
        chunk = file_obj.read(read_size)
        data[:0] = chunk
        lines_found += chunk.count(b"\n")

    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    if len(lines) <= max_lines:
        return text
    return "".join(lines[-max_lines:])


def _read_latest_colcon_log(workspace_path: str, max_lines: int = 200) -> str:
    log_file = _find_colcon_log_file(workspace_path)
    if not log_file:
        return "No colcon log file found in this workspace."

    if max_lines <= 0:
        return (
            f"Latest log file: {os.path.relpath(log_file, workspace_path)}\n"
            f"--- no log lines requested (max_lines={max_lines}) ---"
        )

    try:
        tail_text, truncated = _tail_file_path(log_file, max_lines)
    except Exception as exc:
        return f"Error reading latest colcon log {log_file}: {exc}"

    if truncated:
        return (
            f"Latest log file: {os.path.relpath(log_file, workspace_path)}\n"
            f"--- last {max_lines} lines ---\n"
            f"{tail_text}"
        )

    return (
        f"Latest log file: {os.path.relpath(log_file, workspace_path)}\n"
        f"--- full contents ---\n"
        f"{tail_text}"
    )


def _find_active_colcon_processes() -> list[str]:
    try:
        result = subprocess.run(
            ["ps", "-eo", "pid,cmd"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        processes = []
        for line in result.stdout.splitlines():
            lower_line = line.lower()
            if "colcon" in lower_line:
                processes.append(line.strip())
        return processes
    except Exception:
        return []

@mcp.tool()
def colcon_status(workspace_path: str = ".") -> str:
    """
    Check the status of a colcon build in the given workspace.
    Returns whether a colcon build process is active and the timestamp of the last build.
    """
    try:
        workspace = _resolve_workspace_path(workspace_path)
    except ValueError as exc:
        return str(exc)

    active_processes = _find_active_colcon_processes()
    status_lines = []
    if active_processes:
        status_lines.append("Active colcon processes detected:")
        status_lines.extend(active_processes)
    else:
        status_lines.append("No active colcon build process detected.")

    status_lines.append(f"Last build time: {_find_last_colcon_build_time(workspace)}")
    log_file = _find_colcon_log_file(workspace)
    if log_file:
        status_lines.append(f"Latest colcon log file: {os.path.relpath(log_file, workspace)}")
    return "\n".join(status_lines)

@mcp.tool()
def colcon_last_build_time(workspace_path: str = ".") -> str:
    """
    Return the timestamp of the last colcon build artifacts found in the workspace.
    """
    try:
        workspace = _resolve_workspace_path(workspace_path)
    except ValueError as exc:
        return str(exc)
    return _find_last_colcon_build_time(workspace)

@mcp.tool()
def colcon_latest_log(workspace_path: str = ".", max_lines: int = 200) -> str:
    """
    Return the latest colcon log file contents from the workspace.

    Arguments:
      - workspace_path: path to the ROS 2 workspace.
      - max_lines: limit returned content to the last N log lines.
    """
    try:
        workspace = _resolve_workspace_path(workspace_path)
    except ValueError as exc:
        return str(exc)
    return _read_latest_colcon_log(workspace, max_lines)

@mcp.tool()
def colcon_build(
    workspace_path: str = ".",
    packages: str = "",
    extra_args: str = "",
    timeout: int = 1800,
) -> str:
    """
    Run colcon build in the specified workspace.

    Arguments:
      - workspace_path: path to the ROS 2 workspace.
      - packages: space-separated package names to pass as --packages-select.
      - extra_args: additional colcon CLI arguments.
      - timeout: command timeout in seconds.
    """
    try:
        workspace = _resolve_workspace_path(workspace_path)
    except ValueError as exc:
        return str(exc)

    if not shutil.which("colcon"):
        return "colcon is not available on PATH. Install colcon or adjust PATH for this server process."

    cmd = ["colcon", "build"]
    try:
        package_list = shlex.split(packages) if packages.strip() else []
        extra_args_list = shlex.split(extra_args) if extra_args.strip() else []
        if package_list:
            cmd.extend(["--packages-select", *package_list])
        if extra_args_list:
            cmd.extend(extra_args_list)

        with tempfile.TemporaryFile(mode="w+b") as stdout_file, tempfile.TemporaryFile(mode="w+b") as stderr_file:
            proc = subprocess.Popen(
                cmd,
                cwd=workspace,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=True,
            )
            try:
                proc.wait(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except Exception:
                    pass
                try:
                    proc.wait(5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except Exception:
                        pass
                    proc.wait()
                timed_out = True

            stdout_file.flush()
            stderr_file.flush()
            stdout_file.seek(0)
            stderr_file.seek(0)
            stdout_tail = _tail_file_obj(stdout_file, 200)
            stderr_tail = _tail_file_obj(stderr_file, 200)

        output = []
        output.append(f"Running: {' '.join(shlex.quote(c) for c in cmd)}")
        output.append(f"Workspace: {workspace}")
        output.append("--- stdout ---")
        output.append(stdout_tail or "<no stdout>")
        output.append("--- stderr ---")
        output.append(stderr_tail or "<no stderr>")
        if timed_out:
            output.append(f"Exit code: timed out after {timeout} seconds")
        else:
            output.append(f"Exit code: {proc.returncode}")
        return "\n".join(output)
    except Exception as exc:
        return f"Exception while running colcon build: {exc}"

@mcp.tool()
def colcon_test(
    workspace_path: str = ".",
    packages: str = "",
    extra_args: str = "",
    timeout: int = 1800,
) -> str:
    """
    Run colcon test in the specified workspace.

    Arguments:
      - workspace_path: path to the ROS 2 workspace.
      - packages: space-separated package names to pass as --packages-select.
      - extra_args: additional colcon CLI arguments.
      - timeout: command timeout in seconds.
    """
    try:
        workspace = _resolve_workspace_path(workspace_path)
    except ValueError as exc:
        return str(exc)

    if not shutil.which("colcon"):
        return "colcon is not available on PATH. Install colcon or adjust PATH for this server process."

    cmd = ["colcon", "test"]
    try:
        package_list = shlex.split(packages) if packages.strip() else []
        extra_args_list = shlex.split(extra_args) if extra_args.strip() else []
        if package_list:
            cmd.extend(["--packages-select", *package_list])
        if extra_args_list:
            cmd.extend(extra_args_list)

        with tempfile.TemporaryFile(mode="w+b") as stdout_file, tempfile.TemporaryFile(mode="w+b") as stderr_file:
            proc = subprocess.Popen(
                cmd,
                cwd=workspace,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=True,
            )
            try:
                proc.wait(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except Exception:
                    pass
                try:
                    proc.wait(5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except Exception:
                        pass
                    proc.wait()
                timed_out = True

            stdout_file.flush()
            stderr_file.flush()
            stdout_file.seek(0)
            stderr_file.seek(0)
            stdout_tail = _tail_file_obj(stdout_file, 200)
            stderr_tail = _tail_file_obj(stderr_file, 200)

        output = []
        output.append(f"Running: {' '.join(shlex.quote(c) for c in cmd)}")
        output.append(f"Workspace: {workspace}")
        output.append("--- stdout ---")
        output.append(stdout_tail or "<no stdout>")
        output.append("--- stderr ---")
        output.append(stderr_tail or "<no stderr>")
        if timed_out:
            output.append(f"Exit code: timed out after {timeout} seconds")
        else:
            output.append(f"Exit code: {proc.returncode}")
        return "\n".join(output)
    except Exception as exc:
        return f"Exception while running colcon test: {exc}"

if __name__ == "__main__":
    # Initialize and run the server using standard stdio transport for MCP
    mcp.run()
