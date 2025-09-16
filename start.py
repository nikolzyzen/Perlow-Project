"""SMS Survey System - Setup & Start Script"""

import os
import sys
import subprocess

def setup_environment():
    """Set up virtual environment and dependencies"""
    print("Setting up environment...")
    
    # Create virtual environment
    if not os.path.exists('venv'):
        print("Creating virtual environment...")
        try:
            subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
            print("Virtual environment created")
        except subprocess.CalledProcessError:
            print("Failed to create virtual environment")
            sys.exit(1)
    else:
        print("Virtual environment already exists")
    
    # Install dependencies
    print("Installing dependencies...")
    venv_python = os.path.join('venv', 'bin', 'python')
    venv_pip = os.path.join('venv', 'bin', 'pip')
    
    try:
        if os.path.exists(venv_pip):
            subprocess.run([venv_pip, 'install', '-r', 'requirements.txt'], check=True)
        else:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        print("Dependencies installed")
    except subprocess.CalledProcessError:
        print("Failed to install dependencies")
        sys.exit(1)

def check_environment():
    """Check if environment is ready"""
    # Check if virtual environment exists
    if not os.path.exists('venv'):
        print("Virtual environment not found!")
        setup_environment()
        return
    
    # Check if requirements are installed
    venv_python = os.path.join('venv', 'bin', 'python')
    if os.path.exists(venv_python):
        try:
            result = subprocess.run([venv_python, '-c', 'import flask'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("Dependencies OK")
            else:
                print("Missing dependencies!")
                setup_environment()
        except Exception:
            print("Missing dependencies!")
            setup_environment()
    else:
        print("Virtual environment not found!")
        setup_environment()

def main():
    print("SMS Survey System - Setup & Start")
    print("=" * 40)
    
    # Check and setup environment if needed
    check_environment()
    
    # Clean up any existing processes on port 5001
    cleanup_port()
    
    # Set environment variables for mock SMS
    os.environ['USE_MOCK_SMS'] = 'true'
    os.environ['FLASK_ENV'] = 'development'
    os.environ['SECRET_KEY'] = 'dev-secret-key'
    os.environ['PORT'] = '5001'
    os.environ['DATABASE_URL'] = 'sqlite:///survey.db'
    os.environ['BASE_URL'] = 'http://localhost:5001'
    
    print("Starting SMS Survey System...")
    print("Admin Dashboard: http://localhost:5001/admin")
    print("API Stats: http://localhost:5001/api/stats")
    print("Press Ctrl+C to stop")
    print("=" * 40)
    
    # Use virtual environment Python
    venv_python = os.path.join('venv', 'bin', 'python')
    try:
        if os.path.exists(venv_python):
            subprocess.run([venv_python, 'sms_survey.py'])
        else:
            subprocess.run([sys.executable, 'sms_survey.py'])
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

def cleanup_port():
    """Clean up any processes using port 5001"""
    try:
        print("Cleaning up port 5001...")
        subprocess.run(['fuser', '-k', '5001/tcp'], 
                      capture_output=True, text=True, timeout=5)
        print("Port 5001 available")
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        print("Port 5001 available")

if __name__ == "__main__":
    main()
