#!/usr/bin/env python3
"""
Simple startup script for SMS Survey System
"""

import os
import sys
import subprocess

def main():
    print("🚀 SMS Survey System - Simple Start")
    print("=" * 40)
    
    # Check if virtual environment exists
    if not os.path.exists('venv'):
        print("❌ Virtual environment not found!")
        print("Please run: python -m venv venv")
        sys.exit(1)
    
    # Check if requirements are installed in virtual environment
    venv_python = os.path.join('venv', 'bin', 'python')
    if os.path.exists(venv_python):
        try:
            result = subprocess.run([venv_python, '-c', 'import flask'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Dependencies OK")
            else:
                print("❌ Missing dependencies!")
                print("Please run: source venv/bin/activate && pip install -r requirements.txt")
                sys.exit(1)
        except Exception:
            print("❌ Missing dependencies!")
            print("Please run: source venv/bin/activate && pip install -r requirements.txt")
            sys.exit(1)
    else:
        print("❌ Virtual environment not found!")
        print("Please run: python setup.py")
        sys.exit(1)
    
    # Set environment variables for mock SMS
    os.environ['USE_MOCK_SMS'] = 'true'
    os.environ['FLASK_ENV'] = 'development'
    os.environ['SECRET_KEY'] = 'dev-secret-key'
    os.environ['PORT'] = '5001'
    os.environ['DATABASE_URL'] = 'sqlite:///survey.db'
    os.environ['BASE_URL'] = 'http://localhost:5001'
    
    print("🌐 Starting server on http://localhost:5001")
    print("📱 Admin Dashboard: http://localhost:5001/admin")
    print("🔌 API Stats: http://localhost:5001/api/stats")
    print("Press Ctrl+C to stop")
    print("=" * 40)
    
    # Use virtual environment Python
    venv_python = os.path.join('venv', 'bin', 'python')
    if os.path.exists(venv_python):
        subprocess.run([venv_python, 'sms_survey.py'])
    else:
        subprocess.run([sys.executable, 'sms_survey.py'])

if __name__ == "__main__":
    main()
