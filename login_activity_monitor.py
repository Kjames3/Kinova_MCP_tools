#!/usr/bin/env python3
import argparse
import os
import re
import shlex
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

DEFAULT_LOG_PATH = Path("/opt/kinova/logs/kinova_session_report.log")


def run_command(command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "<command timed out>"
    except Exception as exc:
        return f"<command failed: {exc}>"


def parse_who_output(output):
    sessions = []
    for line in output.splitlines():
        parts = re.split(r"\s+", line)
        if len(parts) < 5:
            continue
        user = parts[0]
        tty = parts[1]
        login_time = " ".join(parts[2:4])
        
        try:
            login_dt = datetime.strptime(login_time, "%Y-%m-%d %H:%M")
            duration = datetime.now() - login_dt
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            if hours > 0:
                duration_str = f"{hours}h {minutes}m"
            else:
                duration_str = f"{minutes}m"
        except Exception:
            duration_str = "?"

        pid = None
        host = None
        if len(parts) >= 6:
            pid = parts[5]
        if len(parts) >= 7:
            host = parts[6].strip("()")
        sessions.append({
            "user": user,
            "tty": tty,
            "login_time": login_time,
            "duration": duration_str,
            "pid": pid,
            "host": host,
        })
    return sessions


def get_logged_in_sessions():
    output = run_command("who -u")
    return parse_who_output(output)


def get_user_processes(user):
    output = run_command(f"ps -u {shlex.quote(user)} -o pid=,comm=,args=")
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    processes = []
    
    ignore_comms = {
        "systemd", "(sd-pam)", "pipewire", "pipewire-media-", "pulseaudio",
        "user-session-he", "sshd", "dbus-daemon", "xdg-document-po", 
        "xdg-permission-", "bash", "sh", "tmux", "zsh", "sudo", "su", "snapd"
    }
    
    for line in lines:
        match = re.match(r"^(\d+)\s+(\S+)\s+(.*)$", line)
        if match:
            pid, comm, args = match.groups()
            if comm not in ignore_comms and "systemd" not in comm and "tracker" not in comm and "gnome" not in comm:
                processes.append({"pid": pid, "command": comm, "args": args})
    return processes


def get_camera_usage():
    cameras = []
    if Path("/dev/video0").exists() or Path("/dev/video1").exists():
        if shutil.which("lsof"):
            output = run_command("lsof /dev/video* 2>/dev/null | awk '{print $1, $2, $3, $9}'")
            cameras = [line for line in output.splitlines() if line.strip()]
        elif shutil.which("fuser"):
            output = run_command("fuser -v /dev/video* 2>/dev/null")
            cameras = [line for line in output.splitlines() if line.strip()]
        else:
            cameras = ["lsof/fuser not available to inspect /dev/video*"]
    else:
        cameras = ["No /dev/video device nodes detected"]
    return cameras


def get_robot_arm_usage():
    status = []
    if shutil.which("ros2"):
        topic_output = run_command("ros2 topic list 2>/dev/null | grep -E 'joint|arm|camera|kinova' || true")
        if topic_output:
            status.append("ROS 2 topics that may indicate arm/camera usage:")
            status.extend(topic_output.splitlines())
    if shutil.which("pgrep"):
        processes = run_command("pgrep -af 'kortex|python.*camera|python.*arm' 2>/dev/null | grep -v 'pgrep -af' || true")
        filtered = [line for line in processes.splitlines() if line.strip() and 'pgrep -af' not in line and 'grep -v' not in line]
        if filtered:
            status.append("Potential arm/camera-related processes:")
            status.extend(filtered)
    if not status:
        status.append("No arm or camera-specific ROS/process usage detected.")
    return status


def get_availability_report():
    camera_status = get_camera_usage()
    arm_status = get_robot_arm_usage()
    camera_in_use = any("lsof" not in line and "/dev/video" in line for line in camera_status)
    arm_in_use = any(
        re.search(r"(?i)(?:^|[^A-Za-z0-9_/.-])(?:kortex|python.*camera|python.*arm|joint(?:[_/].*|$)|camera(?:[_/].*|$)|kinova(?:[_/].*|$))(?:$|[^A-Za-z0-9_/.-])", line)
        for line in arm_status
        if not line.startswith("ROS 2 topics") and not line.startswith("Potential")
    )
    return {
        "camera": "in use" if camera_in_use else "available",
        "robot_arm": "in use" if arm_in_use else "available",
        "camera_details": camera_status,
        "robot_arm_details": arm_status,
    }


def format_session_report(sessions, availability):
    import socket
    
    def resolve_hostname(ip_or_host):
        if not ip_or_host or ip_or_host == '-':
            return '-'
        try:
            # Try to resolve if it's an IP, otherwise return as is
            hostname = socket.gethostbyaddr(ip_or_host)[0]
            # Optionally split off domain for brevity
            return hostname.split('.')[0]
        except Exception:
            return ip_or_host

    lines = []
    lines.append(f"Kinova Session Report: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 90)
    lines.append(f"{'USER':<8} | {'TTY':<5} | {'LOGIN TIME':<16} | {'TIME LOGGED':<11} | {'HOST':<14} | {'ACTIVE SCRIPTS'}")
    lines.append("-" * 90)
    
    if not sessions:
        lines.append("No users are currently logged in.")
    else:
        for session in sessions:
            user = session['user'][:8]
            tty = session['tty'][:5]
            login_time = session['login_time'][:16]
            duration = session.get('duration', '?')[:11]
            
            raw_host = session.get('host', '-')
            resolved_host = resolve_hostname(raw_host)[:14]
            
            processes = get_user_processes(session["user"])
            if not processes:
                lines.append(f"{user:<8} | {tty:<5} | {login_time:<16} | {duration:<11} | {resolved_host:<14} | None")
            else:
                for i, proc in enumerate(processes[:5]):
                    proc_cmd = (proc['command'] + " " + proc['args']).replace(" /opt/ros/humble/bin/", "")
                    proc_cmd = proc_cmd[:24] + ".." if len(proc_cmd) > 26 else proc_cmd
                    
                    if i == 0:
                        lines.append(f"{user:<8} | {tty:<5} | {login_time:<16} | {duration:<11} | {resolved_host:<14} | {proc_cmd}")
                    else:
                        lines.append(f"{'':<8} | {'':<5} | {'':<16} | {'':<11} | {'':<14} | {proc_cmd}")

    lines.append("=" * 90)
    lines.append(f"RESOURCE AVAILABILITY:")
    lines.append(f"  Camera:    {availability['camera'].upper()}")
    lines.append(f"  Robot Arm: {availability['robot_arm'].upper()}")
    
    if availability['robot_arm'] == "in use" and availability['robot_arm_details']:
        lines.append("\n  Active Robot Processes:")
        for entry in availability['robot_arm_details']:
            if entry.startswith("ROS 2") or entry.startswith("Potential"):
                continue
            clean_entry = entry.replace("/usr/bin/python3 /opt/ros/humble/bin/", "")
            clean_entry = clean_entry.replace("/home/kinova/ros2_kortex_ws/install/", "")
            lines.append(f"    - {clean_entry[:90]}")
            
    return "\n".join(lines)


def write_report(output_path, report_text):
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_text + "\n", encoding="utf-8")
        return f"Report written to {output_path}"
    except Exception as exc:
        return f"Failed to write report: {exc}"


def main():
    parser = argparse.ArgumentParser(description="Kinova login and resource activity monitor.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_LOG_PATH),
        help="Path to write the report file.",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print the report to stdout as well as writing it.",
    )
    args = parser.parse_args()

    sessions = get_logged_in_sessions()
    availability = get_availability_report()
    report = format_session_report(sessions, availability)

    result = write_report(args.output, report)
    if args.print:
        print(report)
    print(result)


if __name__ == "__main__":
    import shutil

    main()
