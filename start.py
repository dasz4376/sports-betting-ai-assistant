"""
Start both backend and frontend servers with one command
Usage: py start.py
"""
import subprocess
import sys
import os
import time

def start_servers():
    print("=" * 60)
    print("  NFL BETTING AI - STARTING SERVERS")
    print("=" * 60)
    print()
    
    # Get paths
    backend_path = os.path.join(os.getcwd(), "backend")
    frontend_path = os.path.join(os.getcwd(), "frontend")
    
    try:
        # Start backend
        print("🔷 Starting Backend Server...")
        backend_process = subprocess.Popen(
            ["py", "start_api_only.py"],
            cwd=backend_path,
            shell=True
        )
        print(f"   Backend started (PID: {backend_process.pid})")
        
        # Wait a bit for backend to initialize
        time.sleep(2)
        
        # Start frontend
        print()
        print("🔷 Starting Frontend Server...")
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_path,
            shell=True
        )
        print(f"   Frontend started (PID: {frontend_process.pid})")
        
        print()
        print("=" * 60)
        print("  ✅ SERVERS RUNNING!")
        print("=" * 60)
        print()
        print("  Backend:  http://localhost:8000")
        print("  Frontend: http://localhost:5173")
        print()
        print("  Press Ctrl+C to stop all servers")
        print("=" * 60)
        print()
        
        # Keep script running and wait for processes
        try:
            backend_process.wait()
            frontend_process.wait()
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping servers...")
            backend_process.terminate()
            frontend_process.terminate()
            print("✅ All servers stopped!")
            
    except Exception as e:
        print(f"❌ Error starting servers: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_servers()

