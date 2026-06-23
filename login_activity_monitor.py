#!/usr/bin/env python3
import argparse
import os
import re
import shlex
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

DEFAULT_LOG_PATH = Path("/var/log/kinova_session_report.log")


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
        login_time = " ".join(parts[2:5])
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
    for line in lines:
        match = re.match(r"^(\d+)\s+(\S+)\s+(.*)$", line)
        if match:
            pid, comm, args = match.groups()
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
        processes = run_command("pgrep -af 'ros2|kortex|python.*camera|python.*arm' || true")
        if processes:
            status.append("Potential arm/camera-related processes:")
            status.extend(processes.splitlines())
    if not status:
        status.append("No arm or camera-specific ROS/process usage detected.")
    return status


def get_availability_report():
    camera_status = get_camera_usage()
    arm_status = get_robot_arm_usage()
    camera_in_use = any("lsof" not in line and "/dev/video" in line for line in camera_status)
    arm_in_use = any("ros2" in line or "kortex" in line or "arm" in line for line in arm_status)
    return {
        "camera": "in use" if camera_in_use else "available",
        "robot_arm": "in use" if arm_in_use else "available",
        "camera_details": camera_status,
        "robot_arm_details": arm_status,
    }


def format_session_report(sessions, availability):
    lines = []
    lines.append(f"Kinova session report generated: {datetime.now().isoformat()}")
    lines.append("\n=== Logged-in sessions ===")
    if not sessions:
        lines.append("No users are currently logged in.")
    else:
        for session in sessions:
            lines.append(
                f"User: {session['user']}  tty: {session['tty']}  login: {session['login_time']}  host: {session.get('host', '-')}")
            if session.get("pid"):
                processes = get_user_processes(session["user"])
                if processes:
                    lines.append("  Running processes:")
                    for proc in processes[:10]:
                        lines.append(f"    [{proc['pid']}] {proc['command']} {proc['args']}")
                else:
                    lines.append("  No visible processes for this user.")
    lines.append("\n=== Resource availability ===")
    lines.append(f"Camera: {availability['camera']}")
    lines.extend(f"  {entry}" for entry in availability["camera_details"]) 
    lines.append(f"Robot arm: {availability['robot_arm']}")
    lines.extend(f"  {entry}" for entry in availability["robot_arm_details"]) 
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
