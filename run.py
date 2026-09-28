#!/usr/bin/env python3
"""
FinOps Cost Analyzer - Startup Script
------------------------------------
This launcher verifies if port 8501 (default Streamlit port) is currently occupied.
If an existing session is found, it terminates the process cleanly (cross-platform on
macOS, Windows, and Linux) before launching 'streamlit run app.py'.

Resilience features:
- Gracefully handles missing `psutil` via native OS tools (lsof / netstat).
- Detects the correct Python interpreter containing 'streamlit' if launched from a bare environment.
"""

import sys
import os
import subprocess
import time
import socket
import signal
import shutil

# Try importing psutil; gracefully fallback to built-in OS tools if not installed
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

DEFAULT_PORT = 8501

def is_port_open(port: int) -> bool:
    """Checks if the given TCP port is actively listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_and_kill_port_owner(port: int = DEFAULT_PORT):
    """
    Finds and terminates any process currently bound to the target TCP port.
    Uses psutil if available, otherwise falls back to native OS utilities (lsof / netstat).
    """
    print(f"🔍 Checking for existing session on port {port}...")
    current_pid = os.getpid()
    killed_pids = []

    # 1. Preferred method: psutil
    if HAS_PSUTIL:
        try:
            connections = psutil.net_connections(kind='inet')
            for conn in connections:
                if conn.laddr and conn.laddr.port == port:
                    pid = conn.pid
                    if pid and pid != current_pid and pid not in killed_pids:
                        try:
                            proc = psutil.Process(pid)
                            proc_name = proc.name()
                            print(f"⚠️ Found active process on port {port}: '{proc_name}' (PID {pid})")
                            print(f"🛑 Terminating existing session...")
                            proc.terminate()
                            proc.wait(timeout=3)
                            killed_pids.append(pid)
                            print(f"✅ Terminated existing session (PID: {pid}).")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                        except psutil.TimeoutExpired:
                            proc.kill()
                            killed_pids.append(pid)
                            print(f"✅ Force-killed existing session (PID: {pid}).")
        except (psutil.AccessDenied, Exception):
            pass

    # 2. Fallback method: Native OS tools (macOS / Linux: lsof; Windows: netstat)
    if not killed_pids and is_port_open(port):
        if sys.platform != "win32":
            # macOS / Linux
            try:
                out = subprocess.check_output(
                    ["lsof", "-ti", f":{port}"], 
                    stderr=subprocess.DEVNULL
                ).decode().strip()
                if out:
                    for line in out.splitlines():
                        pid = int(line.strip())
                        if pid != current_pid and pid not in killed_pids:
                            print(f"⚠️ Terminating process listening on port {port} (PID {pid})...")
                            try:
                                os.kill(pid, signal.SIGTERM)
                                time.sleep(0.5)
                                if is_port_open(port):
                                    os.kill(pid, signal.SIGKILL)
                                killed_pids.append(pid)
                                print(f"✅ Terminated existing session (PID: {pid}).")
                            except ProcessLookupError:
                                pass
                            except Exception as e:
                                print(f"⚠️ Could not terminate PID {pid}: {e}")
            except Exception:
                pass
        else:
            # Windows
            try:
                out = subprocess.check_output(
                    f"netstat -ano | findstr :{port}", 
                    shell=True, 
                    stderr=subprocess.DEVNULL
                ).decode().strip()
                for line in out.splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 5 and parts[1].endswith(f":{port}"):
                        pid = int(parts[-1])
                        if pid != current_pid and pid not in killed_pids:
                            print(f"⚠️ Terminating Windows process on port {port} (PID {pid})...")
                            subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            killed_pids.append(pid)
                            print(f"✅ Terminated existing session (PID: {pid}).")
            except Exception:
                pass

    if not killed_pids:
        print(f"✅ Port {port} is clean. No conflicting sessions found.")
    else:
        time.sleep(0.5)

def resolve_python_interpreter() -> str:
    """
    Ensures the python interpreter has 'streamlit' installed.
    If the current interpreter doesn't have it, searches known environments
    (e.g. active virtual environments, Anaconda, system PATH).
    """
    # 1. Check if current interpreter has streamlit
    try:
        res = subprocess.run(
            [sys.executable, "-c", "import streamlit"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if res.returncode == 0:
            return sys.executable
    except Exception:
        pass

    # 2. Check candidate interpreters
    candidates = [
        "/opt/anaconda3/bin/python3",
        "/opt/anaconda3/bin/python",
        shutil.which("python3"),
        shutil.which("python"),
        "/usr/local/bin/python3",
        "/opt/homebrew/bin/python3"
    ]

    for candidate in candidates:
        if candidate and os.path.exists(candidate) and candidate != sys.executable:
            try:
                res = subprocess.run(
                    [candidate, "-c", "import streamlit"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                if res.returncode == 0:
                    print(f"ℹ️ Current Python ({sys.executable}) lacks 'streamlit'.")
                    print(f"✅ Found working environment: '{candidate}'. Delegating execution...\n")
                    return candidate
            except Exception:
                continue

    return sys.executable

def main():
    port = int(os.environ.get("STREAMLIT_SERVER_PORT", DEFAULT_PORT))
    
    print("=" * 65)
    print("⚡ AWS FinOps Cost Analyzer - Dashboard Launcher")
    print("=" * 65)
    
    # 1. Resolve which Python environment has streamlit installed
    python_bin = resolve_python_interpreter()

    # Verify if chosen python has streamlit
    try:
        res = subprocess.run(
            [python_bin, "-c", "import streamlit"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if res.returncode != 0:
            print(f"\n❌ Error: 'streamlit' is not installed in {python_bin}.")
            print("💡 Please install project dependencies first with:")
            print(f"   {python_bin} -m pip install -r requirements.txt\n")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error checking Python environment: {e}")
        sys.exit(1)

    # 2. Terminate any conflicting process bound to port
    find_and_kill_port_owner(port)
    
    # 3. Launch Streamlit dashboard
    print(f"\n🚀 Starting dashboard via '{python_bin} -m streamlit run app.py'...")
    print(f"🌐 Dashboard URL: http://localhost:{port}\n")
    print("Tip: Press Ctrl+C at any time in this terminal to stop the server.\n" + "-" * 65)

    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    cmd = [
        python_bin,
        "-m",
        "streamlit",
        "run",
        app_path,
        "--server.port",
        str(port)
    ]

    try:
        proc = subprocess.Popen(cmd)
        proc.wait()
    except KeyboardInterrupt:
        print("\n👋 Stopping FinOps Dashboard gracefully...")
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("✅ Dashboard stopped successfully.")
    except Exception as e:
        print(f"❌ Failed to start dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
