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

    def is_port_in_use(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((self.host, self.port)) == 0

    def start(self):
        if self.is_port_in_use():
            print(f"--- PMA PHP Server: Port {self.port} already in use, assuming it's running ---")
            return True

        # Try to find php executable
        php_bin = "php"
        if os.name == 'nt':
            # On Windows, try to find in common paths if not in PATH
            # But usually it should be in PATH
            pass
        else:
            # On Linux, try common paths
            for path in ["/usr/bin/php", "/usr/local/bin/php"]:
                if os.path.exists(path):
                    php_bin = path
                    break

        print(f"--- PMA PHP Server: Starting at {self.host}:{self.port} in {self.pma_dir} ---")
        
        # Use -S for built-in server
        cmd = [php_bin, "-S", f"{self.host}:{self.port}", "-t", self.pma_dir]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.pma_dir,
                # Use shell=True on Windows to avoid issues with some PHP installs
                shell=(os.name == 'nt')
            )
            
            # Wait a moment to see if it crashed immediately
            time.sleep(1)
            if self.process.poll() is not None:
                _, stderr = self.process.communicate()
                print(f"--- PMA PHP Server Error: {stderr.decode()} ---")
                return False
            
            print(f"--- PMA PHP Server: Started successfully (PID: {self.process.pid}) ---")
            return True
        except Exception as e:
            print(f"--- PMA PHP Server: Failed to start: {str(e)} ---")
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
        pma_path = os.path.join(os.getcwd(), "phpmyadmin")
        if os.path.exists(pma_path):
            pma_manager = PMAServer(pma_path)
    return pma_manager
