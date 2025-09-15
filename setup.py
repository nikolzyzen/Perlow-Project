#!/usr/bin/env python3
"""
Simple setup script for SMS Survey System
"""

import os
import subprocess
import sys

def main():
    print("🚀 SMS Survey System - Simple Setup")
    print("=" * 40)
    
    # Create virtual environment
    if not os.path.exists('venv'):
        print("📦 Creating virtual environment...")
        subprocess.run([sys.executable, '-m', 'venv', 'venv'])
        print("✅ Virtual environment created")
    else:
        print("✅ Virtual environment already exists")
    
    # Install dependencies
    print("📦 Installing dependencies...")
    venv_python = os.path.join('venv', 'bin', 'python')
    if os.path.exists(venv_python):
        subprocess.run([venv_python, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    else:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    
    print("✅ Dependencies installed")
    print("\n🎉 Setup complete!")
    print("\nTo start the system:")
    print("  python start.py")
    print("\nOr manually:")
    print("  source venv/bin/activate")
    print("  python sms_survey.py")
    print("\nThen visit: http://localhost:5001/admin")

if __name__ == "__main__":
    main()
