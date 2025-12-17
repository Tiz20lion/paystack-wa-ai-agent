"""Utility script to check for running Python processes."""

import psutil
import sys
from typing import List, Dict
from app.utils.logger import get_logger

logger = get_logger("process_checker")


def find_python_processes() -> List[Dict]:
    """Find all running Python processes."""
    python_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            proc_info = proc.as_dict(attrs=['pid', 'name', 'cmdline'])
            name = proc_info['name'].lower()
            cmdline = proc_info.get('cmdline', [])
            
            # Check if it's a Python process
            if ('python' in name or 
                (cmdline and any('python' in arg.lower() for arg in cmdline))):
                
                # Get more details
                try:
                    cmd_str = ' '.join(cmdline) if cmdline else name
                    python_processes.append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'cmdline': cmd_str,
                        'process': proc
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    return python_processes


def find_app_processes() -> List[Dict]:
    """Find running instances of our application."""
    app_processes = []
    current_pid = psutil.Process().pid
    
    for proc_info in find_python_processes():
        cmdline = proc_info['cmdline']
        pid = proc_info['pid']
        
        # Skip current process
        if pid == current_pid:
            continue
            
        # Check for our app files, but exclude the process that just started (within last 5 seconds)
        if any(file in cmdline for file in ['main.py', 'cli_app.py', 'api_server.py']):
            try:
                # Get process creation time
                proc = psutil.Process(pid)
                import time
                process_age = time.time() - proc.create_time()
                
                # Skip processes that just started (likely the current instance)
                if process_age < 5:  # Less than 5 seconds old
                    logger.info(f"Skipping recently started process {pid} (age: {process_age:.1f}s)")
                    continue
                    
                app_processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # If we can't get process info, include it anyway
                app_processes.append(proc_info)
    
    return app_processes


def kill_process(pid: int) -> bool:
    """Kill a process by PID."""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        
        # Wait for process to terminate
        try:
            proc.wait(timeout=5)
            logger.info(f"Process {pid} terminated successfully")
            return True
        except psutil.TimeoutExpired:
            # Force kill if it doesn't terminate
            proc.kill()
            logger.warning(f"Force killed process {pid}")
            return True
            
    except psutil.NoSuchProcess:
        logger.info(f"Process {pid} no longer exists")
        return True
    except psutil.AccessDenied:
        logger.error(f"Access denied when trying to kill process {pid}")
        return False
    except Exception as e:
        logger.error(f"Error killing process {pid}: {e}")
        return False


def check_and_kill_app_processes(interactive: bool = True) -> bool:
    """Check for running app processes and optionally kill them."""
    app_processes = find_app_processes()
    
    if not app_processes:
        print("✅ No running application processes found.")
        return True
    
    print(f"⚠️  Found {len(app_processes)} running application process(es):")
    print()
    
    for i, proc_info in enumerate(app_processes, 1):
        print(f"{i}. PID {proc_info['pid']}: {proc_info['cmdline']}")
    
    print()
    
    if interactive:
        choice = input("Kill all running app processes? (y/n): ").strip().lower()
        if choice not in ['y', 'yes']:
            print("❌ User chose not to kill processes. Please stop them manually.")
            return False
    
    # Kill all app processes
    success = True
    for proc_info in app_processes:
        pid = proc_info['pid']
        print(f"🔄 Killing process {pid}...")
        
        if kill_process(pid):
            print(f"✅ Process {pid} killed successfully")
        else:
            print(f"❌ Failed to kill process {pid}")
            success = False
    
    # Wait a moment for processes to fully terminate
    import time
    time.sleep(1)
    
    return success


def main():
    """Main function for standalone usage."""
    print("🔍 Checking for running Python processes...")
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        # Show all Python processes
        python_procs = find_python_processes()
        print(f"Found {len(python_procs)} Python processes:")
        for proc_info in python_procs:
            print(f"  PID {proc_info['pid']}: {proc_info['cmdline']}")
    else:
        # Check only app processes
        check_and_kill_app_processes(interactive=True)


if __name__ == "__main__":
    main() 