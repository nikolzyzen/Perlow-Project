#!/usr/bin/env python3
"""
One-command setup and start for SMS Survey System
"""

import os
import subprocess
import sys
import time

def main():
    print("🚀 SMS Survey System - Quick Start")
    print("=" * 40)
    
    # Step 1: Setup if needed
    if not os.path.exists('venv'):
        print("📦 Setting up virtual environment...")
        subprocess.run([sys.executable, '-m', 'venv', 'venv'])
        print("✅ Virtual environment created")
    
    # Step 2: Install dependencies
    print("📦 Installing dependencies...")
    venv_python = os.path.join('venv', 'bin', 'python')
    if os.path.exists(venv_python):
        subprocess.run([venv_python, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    else:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    print("✅ Dependencies installed")
    
    # Step 3: Kill any existing processes on port 5001
    print("🧹 Cleaning up port 5001...")
    subprocess.run(['lsof', '-ti:5001'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['lsof', '-ti:5001'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = subprocess.run(['lsof', '-ti:5001'], capture_output=True, text=True)
    if result.stdout.strip():
        subprocess.run(['kill', '-9'] + result.stdout.strip().split('\n'))
        print("✅ Port 5001 cleared")
    else:
        print("✅ Port 5001 available")
    
    # Step 4: Start the application
    print("🌐 Starting SMS Survey System...")
    print("📱 Admin Dashboard: http://localhost:5001/admin")
    print("🔌 API Stats: http://localhost:5001/api/stats")
    print("Press Ctrl+C to stop")
    print("=" * 40)
    
    # Set environment variables
    os.environ['USE_MOCK_SMS'] = 'true'
    os.environ['FLASK_ENV'] = 'development'
    os.environ['SECRET_KEY'] = 'dev-secret-key'
    os.environ['PORT'] = '5001'
    os.environ['DATABASE_URL'] = 'sqlite:///survey.db'
    os.environ['BASE_URL'] = 'http://localhost:5001'
    
    # Start the application
    if os.path.exists(venv_python):
        subprocess.run([venv_python, 'sms_survey.py'])
    else:
        subprocess.run([sys.executable, 'sms_survey.py'])

if __name__ == "__main__":
    main()
