import subprocess
import os
import time
import socket
import signal
import threading

class PMAServer:
    def __init__(self, pma_dir: str, host: str = "127.0.0.1", port: int = 8001):
        self.pma_dir = pma_dir
        self.host = host
        self.port = port
        self.process = None
        self._stop_event = threading.Event()
        self.last_error = None

    def is_port_in_use(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((self.host, self.port)) == 0

    def start(self):
        self.last_error = None
        if self.is_port_in_use():
            print(f"--- PMA PHP Server: Port {self.port} already in use, assuming it's running ---")
            return True

        # Try to find php executable
        from backend.utils.php_utils import find_php_executable
        php_bin = find_php_executable()

        if not php_bin:
            self.last_error = "PHP executable not found. Please install PHP and add it to PATH, or install it via the panel's PHP management."
            print(f"--- PMA PHP Server Error: {self.last_error} ---")
            return False

        print(f"--- PMA PHP Server: Starting at {self.host}:{self.port} in {self.pma_dir} using {php_bin} ---")

        # Use -S for built-in server
        # Force session name and storage path via auto_prepend_file
        # This is the most reliable way to override phpMyAdmin's internal session management
        # Use forward slashes for PHP ini settings even on Windows
        pre_config = os.path.join(self.pma_dir, 'pre-config.php').replace('\\', '/')
        sessions_dir = os.path.join(self.pma_dir, 'sessions').replace('\\', '/')
        if not os.path.exists(sessions_dir):
            try:
                os.makedirs(sessions_dir, exist_ok=True)
            except:
                pass

        cmd = [
            php_bin, 
            "-S", f"{self.host}:{self.port}", 
            "-t", self.pma_dir,
            "-d", f"auto_prepend_file=\"{pre_config}\"",
            "-d", "session.name=SanguoPMA",
            "-d", f"session.save_path=\"{sessions_dir}\""
        ]
        
        # Create logs directory if it doesn't exist
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(backend_dir)
        log_dir = os.path.join(project_root, "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        pma_log_path = os.path.join(log_dir, "pma.log")
        pma_log = open(pma_log_path, "w", encoding="utf-8")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=pma_log,
                stderr=pma_log,
                cwd=self.pma_dir,
                # Use shell=True on Windows to avoid issues with some PHP installs
                shell=(os.name == 'nt')
            )
            
            # Wait a moment to see if it crashed immediately
            time.sleep(1)
            if self.process.poll() is not None:
                self.last_error = "PHP Server failed to start immediately. Check if PHP is installed and port 8001 is free."
                print(f"--- PMA PHP Server Error: {self.last_error} ---")
                return False
            
            print(f"--- PMA PHP Server: Started successfully (PID: {self.process.pid}) ---")
            return True
        except Exception as e:
            self.last_error = f"Failed to start PHP process: {str(e)}"
            print(f"--- PMA PHP Server Error: {self.last_error} ---")
            return False

    def stop(self):
        if self.process:
            print(f"--- PMA PHP Server: Stopping (PID: {self.process.pid}) ---")
            if os.name == 'nt':
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.process.pid)])
            else:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process = None

pma_manager = None

def get_pma_manager():
    global pma_manager
    if pma_manager is None:
        # Get the directory where backend is located
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pma_path = os.path.join(backend_dir, "phpmyadmin")
        if os.path.exists(pma_path):
            pma_manager = PMAServer(pma_path)
        else:
            # Also check if it's in the current working directory for fallback
            pma_path_cwd = os.path.join(os.getcwd(), "phpmyadmin")
            if os.path.exists(pma_path_cwd):
                pma_manager = PMAServer(pma_path_cwd)
    return pma_manager
