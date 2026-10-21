#!/usr/bin/env python3
"""
System Pre-Flight Verification Script for Agentic AIOps RCA Copilot.
Checks Python version, Docker status, memory/disk headroom, port availability, and Gemini key.
"""

import sys
import os
import socket
import shutil
import subprocess
from pathlib import Path

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def print_status(component: str, ok: bool, details: str = ""):
    symbol = "[OK]  " if ok else "[FAIL]"
    print(f"{symbol} {component:<28} : {details}")

def check_python_version() -> bool:
    v = sys.version_info
    ok = v.major == 3 and v.minor >= 10
    print_status("Python Version", ok, f"{v.major}.{v.minor}.{v.micro} (Requires >= 3.10)")
    return ok

def check_docker() -> tuple[bool, bool]:
    docker_bin = shutil.which("docker")
    has_docker = docker_bin is not None
    print_status("Docker CLI Installed", has_docker, docker_bin or "Not found in PATH")
    
    daemon_running = False
    if has_docker:
        try:
            res = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
            daemon_running = (res.returncode == 0)
        except Exception:
            daemon_running = False
            
    print_status("Docker Daemon Running", daemon_running, "Active" if daemon_running else "Daemon not responding (start Docker Desktop)")
    return has_docker, daemon_running

def check_resources() -> bool:
    try:
        import ctypes
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        total_ram_gb = stat.ullTotalPhys / (1024 ** 3)
        avail_ram_gb = stat.ullAvailPhys / (1024 ** 3)
        ok = total_ram_gb >= 12.0
        print_status("Host RAM Headroom", ok, f"Total: {total_ram_gb:.1f} GB, Available: {avail_ram_gb:.1f} GB (Target: 16 GB)")
    except Exception:
        total_ram_gb, avail_ram_gb = 0, 0
        print_status("Host RAM Headroom", True, "Could not query Win32 memory API (Skipped)")

    # Disk space on current drive
    cwd = Path.cwd()
    total, used, free = shutil.disk_usage(cwd)
    free_gb = free / (1024 ** 3)
    ok_disk = free_gb >= 15.0
    print_status("Free Disk Space", ok_disk, f"{free_gb:.1f} GB free on {cwd.drive} (Min recommended: 15 GB)")
    return ok_disk

def check_port(port: int, service_name: str) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        # returncode 0 means port is in use
        is_free = (s.connect_ex(("127.0.0.1", port)) != 0)
    return is_free

def check_all_ports() -> bool:
    ports = [
        (8000, "Copilot Backend"),
        (8001, "Order Service"),
        (8002, "Payment Service"),
        (9090, "Prometheus"),
        (9093, "Alertmanager"),
        (3100, "Loki"),
        (3200, "Tempo"),
        (3000, "Grafana"),
        (8501, "Streamlit UI")
    ]
    all_free = True
    busy_ports = []
    for port, name in ports:
        if not check_port(port, name):
            all_free = False
            busy_ports.append(f"{name} ({port})")
    
    if all_free:
        print_status("Port Availability", True, "All 9 required ports are open and free")
    else:
        print_status("Port Availability", False, f"Conflicts detected: {', '.join(busy_ports)}")
    return all_free

def check_env_gemini() -> bool:
    env_file = Path(".env")
    if not env_file.exists():
        print_status("Gemini Configuration", False, ".env file not found. Copy .env.example to .env and set GEMINI_API_KEY")
        return False
    
    with open(env_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "GEMINI_API_KEY=your_gemini_api_key_here" in content or "GEMINI_API_KEY=" not in content:
        print_status("Gemini Configuration", False, "GEMINI_API_KEY placeholder detected in .env")
        return False
    
    print_status("Gemini Configuration", True, "GEMINI_API_KEY detected in .env")
    return True

def main():
    print("=" * 70)
    print(" Agentic AIOps RCA Copilot - Pre-Flight Verification")
    print("=" * 70)
    
    check_python_version()
    check_docker()
    check_resources()
    check_all_ports()
    check_env_gemini()
    
    print("=" * 70)
    print("Verification complete. Ensure Docker Desktop is running before Phase 1.")
    print("=" * 70)

if __name__ == "__main__":
    main()
