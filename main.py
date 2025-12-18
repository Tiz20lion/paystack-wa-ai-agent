"""Main entry point for Paystack CLI/API application."""

import sys
import os

# For Vercel deployment, just export the FastAPI app
if os.getenv("VERCEL"):
    from api_server import app
    # Vercel will use this app directly
    __all__ = ["app"]
else:
    # For local development, use the CLI/API runner
    import argparse
    import asyncio
    from app.utils.config import settings
    from app.utils.logger import get_logger
    logger = get_logger("main")


def run_cli():
    """Run the CLI application."""
    try:
        from cli_app import main as cli_main
        logger.info("Starting Paystack CLI application")
        cli_main()
    except ImportError as e:
        logger.error(f"Failed to import CLI module: {e}")
        print("Error: Failed to start CLI application")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running CLI: {e}")
        print(f"Error: {e}")
        sys.exit(1)


def run_api(disable_reload=False):
    """Run the API server."""
    try:
        import uvicorn
        import threading
        
        logger.info(f"Starting {settings.app_name} API server")
        print(f"🚀 Starting {settings.app_name} API Server")
        print(f"📍 Running on: http://{settings.api_host}:{settings.api_port}")
        print(f"📚 API Documentation: http://{settings.api_host}:{settings.api_port}/docs")
        print(f"🔄 Debug mode: {settings.debug}")
        
        # Disable reload if running in a thread (not main thread)
        is_main_thread = threading.current_thread() is threading.main_thread()
        use_reload = settings.api_reload and not disable_reload and is_main_thread
        
        if not is_main_thread:
            print("🔄 Hot reload disabled (running in background thread)")
        
        print()
        
        uvicorn.run(
            "api_server:app",  # Use import string for proper reload support
            host=settings.api_host,
            port=settings.api_port,
            reload=use_reload,
            log_level=settings.log_level.lower()
        )
        
    except ImportError as e:
        logger.error(f"Failed to import API modules: {e}")
        print("Error: Failed to start API server. Make sure all dependencies are installed.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running API server: {e}")
        print(f"Error: {e}")
        sys.exit(1)


def run_both():
    """Run both CLI and API (CLI in foreground, API in background)."""
    import threading
    import time
    
    print("🚀 Starting both CLI and API...")
    print(f"📍 API will run on: http://{settings.api_host}:{settings.api_port}")
    print("🖥️  CLI will start in 3 seconds...")
    print()
    
    # Start API server in a separate thread (reload will be auto-disabled)
    api_thread = threading.Thread(target=lambda: run_api(disable_reload=True), daemon=True)
    api_thread.start()
    
    # Wait a bit for API to start
    time.sleep(3)
    
    # Start CLI in main thread
    run_cli()


def check_environment():
    """Check if environment is properly configured."""
    try:
        # Try to access secret key to verify environment
        secret_key = settings.paystack_secret_key
        if not secret_key or secret_key == "sk_test_your_secret_key_here":
            print("⚠️  Warning: Paystack secret key not configured!")
            print("Please edit .env file with your Paystack API keys.")
            print()
            
            if input("Continue anyway? (y/n): ").lower() != 'y':
                sys.exit(0)
        else:
            print("✅ Paystack API keys configured")
            print()
        
        return True
        
    except Exception as e:
        logger.error(f"Environment check failed: {e}")
        print(f"❌ Environment configuration error: {e}")
        print("Please check your .env file and configuration.")
        return False


def check_running_processes():
    """Check for running application processes."""
    try:
        import time
        # Wait a moment to ensure any previous processes have fully started/terminated
        time.sleep(2)
        
        from check_python import check_and_kill_app_processes
        return check_and_kill_app_processes(interactive=True)
    except ImportError:
        logger.warning("Process checker not available")
        return True
    except Exception as e:
        logger.error(f"Error checking processes: {e}")
        print(f"⚠️  Warning: Could not check for running processes: {e}")
        return True


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description=f"{settings.app_name} - Interactive CLI and API for Paystack operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              # Run interactive CLI (default)
  python main.py --cli         # Run CLI explicitly  
  python main.py --api         # Run API server only
  python main.py --both        # Run both CLI and API
  python main.py --check       # Check environment configuration

For more information, visit the documentation.
        """
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--cli", 
        action="store_true",
        help="Run the interactive CLI application (default)"
    )
    group.add_argument(
        "--api", 
        action="store_true",
        help="Run the FastAPI server only"
    )
    group.add_argument(
        "--both", 
        action="store_true",
        help="Run both CLI and API (API in background, CLI in foreground)"
    )
    group.add_argument(
        "--check", 
        action="store_true",
        help="Check environment configuration"
    )
    
    parser.add_argument(
        "--skip-process-check", 
        action="store_true",
        help="Skip checking for running processes (used by startup script)"
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"{settings.app_name} v{settings.app_version}"
    )
    
    args = parser.parse_args()
    
    # Print header
    print("=" * 60)
    print(f"  {settings.app_name} v{settings.app_version}")
    print("  Interactive Paystack CLI and API Application")
    print("=" * 60)
    print()
    
    # Check environment for all modes
    if not check_environment():
        sys.exit(1)
    
    # Handle arguments
    if args.check:
        print("✅ Environment configuration check passed!")
        print(f"📍 API will run on: http://{settings.api_host}:{settings.api_port}")
        print(f"💰 Default currency: {settings.default_currency}")
        print(f"🔐 Secret key configured: {'Yes' if settings.paystack_secret_key else 'No'}")
        print()
        check_running_processes()
        return
    
    elif args.api:
        # Check for running processes before starting API (unless skipped)
        if not args.skip_process_check and not check_running_processes():
            sys.exit(1)
        run_api()
    
    elif args.both:
        # Check for running processes before starting both (unless skipped)
        if not args.skip_process_check and not check_running_processes():
            sys.exit(1)
        run_both()
    
    else:  # Default to CLI or explicit --cli
        # Check for running processes before starting CLI (unless skipped)
        if not args.skip_process_check and not check_running_processes():
            sys.exit(1)
        run_cli()


if __name__ == "__main__":
    # Only run CLI/API runner if not on Vercel
    if not os.getenv("VERCEL"):
        try:
            main()
        except KeyboardInterrupt:
            print("\n👋 Application terminated by user")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            print(f"\n💥 Fatal error: {e}")
            sys.exit(1) 