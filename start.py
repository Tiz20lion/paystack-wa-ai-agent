#!/usr/bin/env python3
"""
Simple startup script for Paystack CLI App
Handles virtual environment setup, dependency installation, and application startup
Works on both Windows and Linux/Ubuntu
"""

import os
import sys
import platform
import subprocess
import venv
import argparse


def print_status(message):
    """Print status message with emoji."""
    print(f"✅ {message}")


def print_error(message):
    """Print error message with emoji."""
    print(f"❌ {message}")


def print_info(message):
    """Print info message with emoji."""
    print(f"ℹ️ {message}")


def get_python_path():
    """Get the correct Python executable path for the current platform."""
    system = platform.system().lower()
    
    if system == "windows":
        return os.path.join("venv", "Scripts", "python.exe")
    else:  # Linux/Ubuntu and other Unix-like systems
        return os.path.join("venv", "bin", "python")


def get_pip_path():
    """Get the correct pip executable path for the current platform."""
    system = platform.system().lower()
    
    if system == "windows":
        return os.path.join("venv", "Scripts", "pip.exe")
    else:  # Linux/Ubuntu and other Unix-like systems
        return os.path.join("venv", "bin", "pip")


def check_or_create_venv():
    """Check if virtual environment exists, create if it doesn't."""
    if os.path.exists("venv"):
        print_status("Virtual environment found")
        return True
    
    print_info("Creating virtual environment...")
    try:
        venv.create("venv", with_pip=True)
        print_status("Virtual environment created successfully")
        return True
    except Exception as e:
        print_error(f"Failed to create virtual environment: {e}")
        return False


def check_or_install_requirements():
    """Check if requirements are installed, install if they're not."""
    python_path = get_python_path()
    pip_path = get_pip_path()
    
    # Check if key dependencies are installed
    try:
        result = subprocess.run(
            [python_path, "-c", "import fastapi, uvicorn, pydantic_settings"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_status("Requirements already installed")
            return True
    except:
        pass
    
    # Install requirements
    if not os.path.exists("requirements.txt"):
        print_error("requirements.txt not found")
        return False
    
    print_info("Installing requirements...")
    try:
        # Upgrade pip first using python -m pip method
        subprocess.run([python_path, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        
        # Install requirements
        subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
        
        print_status("Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install requirements: {e}")
        return False


def setup_env_file():
    """Create .env file from example.env if it doesn't exist."""
    if not os.path.exists(".env"):
        if os.path.exists("example.env"):
            print_info("Creating .env from example.env...")
            try:
                with open("example.env", "r") as src:
                    content = src.read()
                with open(".env", "w") as dst:
                    dst.write(content)
                print_status(".env file created")
                print_info("⚠️  IMPORTANT: Edit .env file with your real Paystack API keys!")
                print_info("   - Get your keys from: https://dashboard.paystack.com/settings/developer")
                print_info("   - Set PAYSTACK_SECRET_KEY and PAYSTACK_PUBLIC_KEY")
            except Exception as e:
                print_error(f"Failed to create .env file: {e}")
        else:
            print_error("example.env not found")
    else:
        print_status(".env file exists")


def free_port_on_linux(port: int):
    """On Linux, try to free the given port so the app can bind (avoid 'Address already in use')."""
    if platform.system().lower() != "linux":
        return
    try:
        subprocess.run(
            ["sh", "-c", f"fuser -k {port}/tcp 2>/dev/null || true"],
            capture_output=True,
            timeout=5,
        )
        import time
        time.sleep(1)
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass


def start_application(mode="api", host="127.0.0.1", port=8000):
    """Start the application."""
    if mode in ("api", "both"):
        free_port_on_linux(port)
    python_path = get_python_path()

    # Build command
    cmd = [python_path, "main.py"]
    
    if mode == "api":
        cmd.append("--api")
    elif mode == "cli":
        cmd.append("--cli")
    elif mode == "both":
        cmd.append("--both")
    elif mode == "check":
        cmd.append("--check")
    
    # Add flag to skip process check since we're starting fresh
    cmd.append("--skip-process-check")
    
    # Set environment variables
    if host != "127.0.0.1":
        os.environ["API_HOST"] = host
    if port != 8000:
        os.environ["API_PORT"] = str(port)
    
    print_info(f"🚀 Starting TizLion AI Banking CLI App in {mode} mode...")
    print_info(f"📍 Platform: {platform.system()} {platform.release()}")
    
    if mode in ["api", "both"]:
        print_info(f"🌐 API will be available at: http://{host}:{port}")
        print_info(f"📚 API Documentation: http://{host}:{port}/docs")
    
    try:
        subprocess.run(cmd, check=True)
        return True
    except KeyboardInterrupt:
        print_info("\n🛑 Application stopped by user")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Application failed with exit code: {e.returncode}")
        return False
    except Exception as e:
        print_error(f"Error starting application: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Simple Paystack CLI App Starter",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--mode", 
        choices=["api", "cli", "both", "check"],
        default="both",
        help="Application mode (default: both - CLI + API)"
    )
    
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="API host address (default: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API port number (default: 8000)"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("🚀 Paystack CLI App - Simple Starter")
    print("=" * 50)
    
    if args.mode == "both":
        print("🎯 Default mode: Both CLI and API will start together")
        print("   - API server runs in background on port", args.port)
        print("   - CLI interface runs in foreground")
        print("   - Use your real Paystack API keys for full functionality")
        print()
    
    # Step 1: Check or create virtual environment
    if not check_or_create_venv():
        sys.exit(1)
    
    # Step 2: Check or install requirements
    if not check_or_install_requirements():
        sys.exit(1)
    
    # Step 3: Setup .env file
    setup_env_file()
    
    # Step 4: Start application
    print("\n" + "=" * 50)
    success = start_application(args.mode, args.host, args.port)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main() 