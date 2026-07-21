#!/usr/bin/env python3
"""
Sanguo Panel - 一键启动脚本
同时启动后端 (FastAPI) 和前端 (Vue) 服务
支持 Windows / Linux / macOS
"""

import os
import sys
import subprocess
import time
import signal
import platform
from pathlib import Path
from typing import List, Optional


class Colors:
    """终端颜色输出"""
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

    @classmethod
    def disable(cls):
        """禁用颜色（Windows CMD 不支持时）"""
        cls.CYAN = cls.GREEN = cls.YELLOW = cls.RED = cls.RESET = cls.BOLD = ''


class ProcessManager:
    """进程管理器"""
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.is_running = True

    def add(self, process: subprocess.Popen):
        """添加进程到管理列表"""
        self.processes.append(process)

    def terminate_all(self):
        """终止所有管理的进程"""
        print(f"\n{Colors.YELLOW}正在停止所有服务...{Colors.RESET}")
        self.is_running = False

        for process in self.processes:
            try:
                if process.poll() is None:  # 进程仍在运行
                    # 先尝试友好终止
                    if platform.system() == "Windows":
                        process.terminate()
                    else:
                        process.send_signal(signal.SIGTERM)

                    # 等待最多 3 秒
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        # 强制终止
                        if platform.system() == "Windows":
                            process.kill()
                        else:
                            process.send_signal(signal.SIGKILL)
            except Exception as e:
                print(f"{Colors.RED}终止进程时出错: {e}{Colors.RESET}")

        print(f"{Colors.GREEN}所有服务已停止{Colors.RESET}")


def print_banner():
    """打印启动横幅"""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}========================================
  Sanguo Panel 启动脚本
========================================{Colors.RESET}
"""
    print(banner)


def check_virtual_env(project_root: Path) -> bool:
    """检查虚拟环境是否存在"""
    venv_path = project_root / "venv"
    if not venv_path.exists():
        print(f"{Colors.RED}[错误] 虚拟环境不存在: {venv_path}{Colors.RESET}")
        print(f"{Colors.YELLOW}请先创建虚拟环境:{Colors.RESET}")
        print(f"  python -m venv venv")
        activate_cmd = ".\\venv\\Scripts\\activate" if platform.system() == "Windows" else "source venv/bin/activate"
        print(f"  {activate_cmd}")
        print(f"  pip install -r requirements.txt")
        return False
    return True


def check_nodejs() -> bool:
    """检查 Node.js 是否安装"""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"{Colors.GREEN}[检查] Node.js 环境... OK ({result.stdout.strip()}){Colors.RESET}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    print(f"{Colors.RED}[错误] 未检测到 Node.js，请先安装 Node.js{Colors.RESET}")
    return False


def check_frontend_deps(project_root: Path) -> bool:
    """检查前端依赖是否已安装"""
    frontend_path = project_root / "frontend"
    node_modules_path = frontend_path / "node_modules"

    if not node_modules_path.exists():
        print(f"{Colors.YELLOW}[安装] 正在安装前端依赖...{Colors.RESET}")
        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=frontend_path,
                capture_output=False,
                text=True
            )
            if result.returncode != 0:
                print(f"{Colors.RED}[错误] 前端依赖安装失败{Colors.RESET}")
                return False
        except Exception as e:
            print(f"{Colors.RED}[错误] 前端依赖安装失败: {e}{Colors.RESET}")
            return False
    else:
        print(f"{Colors.GREEN}[检查] 前端依赖... OK{Colors.RESET}")

    return True


def wait_for_service(url: str, name: str, timeout: int = 60) -> bool:
    """等待服务就绪"""
    print(f"{Colors.YELLOW}[等待] 等待{name}就绪...{Colors.RESET}", end="", flush=True)

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            import urllib.request
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    print(f" {Colors.GREEN}OK{Colors.RESET}")
                    return True
        except Exception:
            print(".", end="", flush=True)
            time.sleep(1)

    print(f" {Colors.RED}超时{Colors.RESET}")
    return False


def start_backend(project_root: Path, process_manager: ProcessManager) -> Optional[subprocess.Popen]:
    """启动后端服务"""
    print(f"{Colors.CYAN}[启动] 后端服务 (端口 8000)...{Colors.RESET}")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)
    
    # 创建日志目录
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    backend_log = open(log_dir / "backend.log", "w", encoding="utf-8")

    # 使用当前 Python 解释器（如果在虚拟环境中，会自动使用虚拟环境的 Python）
    # 如果当前不在虚拟环境中，则使用项目根目录的虚拟环境
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        # 当前已在虚拟环境中
        python_path = sys.executable
    else:
        # 不在虚拟环境中，使用项目根目录的虚拟环境
        if platform.system() == "Windows":
            python_path = str(project_root / "venv" / "Scripts" / "python.exe")
        else:
            python_path = str(project_root / "venv" / "bin" / "python")

    try:
        process = subprocess.Popen(
            [
                python_path,
                "-m", "uvicorn",
                "backend.main:app",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--reload",
                "--reload-exclude", "*.db"
            ],
            cwd=project_root,
            env=env,
            stdout=backend_log,
            stderr=backend_log,
            text=True
        )
        process_manager.add(process)
        return process
    except Exception as e:
        print(f"{Colors.RED}[错误] 启动后端失败: {e}{Colors.RESET}")
        return None


def start_frontend(project_root: Path, process_manager: ProcessManager) -> Optional[subprocess.Popen]:
    """启动前端服务"""
    print(f"{Colors.CYAN}[启动] 前端服务 (端口 5173)...{Colors.RESET}")

    frontend_path = project_root / "frontend"
    
    # 创建日志目录
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    frontend_log = open(log_dir / "frontend.log", "w", encoding="utf-8")

    # 在 Windows 上需要使用 shell=True 才能找到 npm
    shell = platform.system() == "Windows"
    
    try:
        process = subprocess.Popen(
            ["npm", "run", "dev", "--", "--host", "0.0.0.0"],
            cwd=frontend_path,
            stdout=frontend_log,
            stderr=frontend_log,
            text=True,
            shell=shell
        )
        process_manager.add(process)
        return process
    except Exception as e:
        print(f"{Colors.RED}[错误] 启动前端失败: {e}{Colors.RESET}")
        return None


def main():
    """主函数"""
    # 禁用颜色输出（如果 Windows CMD 不支持）
    if platform.system() == "Windows" and os.environ.get("TERM") is None:
        Colors.disable()

    print_banner()

    # 获取项目根目录
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)

    # 创建进程管理器
    process_manager = ProcessManager()

    # 设置信号处理（用于优雅退出）
    def signal_handler(signum, frame):
        print(f"\n{Colors.YELLOW}接收到终止信号，正在关闭...{Colors.RESET}")
        process_manager.terminate_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 检查环境
    print(f"{Colors.CYAN}[检查] 项目环境...{Colors.RESET}\n")

    if not check_virtual_env(script_dir):
        sys.exit(1)

    if not check_nodejs():
        sys.exit(1)

    if not check_frontend_deps(script_dir):
        sys.exit(1)

    print(f"\n{Colors.CYAN}========================================{Colors.RESET}")
    print(f"{Colors.CYAN}  正在启动服务...{Colors.RESET}")
    print(f"{Colors.CYAN}========================================{Colors.RESET}\n")

    # 启动后端
    backend_process = start_backend(script_dir, process_manager)
    if not backend_process:
        print(f"{Colors.RED}[错误] 后端服务启动失败{Colors.RESET}")
        process_manager.terminate_all()
        sys.exit(1)

    # 等待后端就绪 (使用 127.0.0.1 避免 IPv6 解析问题)
    if not wait_for_service("http://127.0.0.1:8000/api/v1/system/status", "后端服务", timeout=60):
        print(f"{Colors.YELLOW}[警告] 后端服务可能尚未完全就绪，继续启动前端...{Colors.RESET}")

    # 启动前端
    frontend_process = start_frontend(script_dir, process_manager)
    if not frontend_process:
        print(f"{Colors.RED}[错误] 前端服务启动失败{Colors.RESET}")
        process_manager.terminate_all()
        sys.exit(1)

    # 等待前端就绪 (使用 127.0.0.1 避免 IPv6 解析问题)
    if not wait_for_service("http://127.0.0.1:5173", "前端服务", timeout=60):
        print(f"{Colors.YELLOW}[警告] 前端服务可能尚未完全就绪...{Colors.RESET}")

    # 显示最终状态
    print(f"\n{Colors.GREEN}{Colors.BOLD}========================================{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}  服务启动完成！{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}========================================{Colors.RESET}\n")
    print(f"  {Colors.CYAN}前端界面:{Colors.RESET} http://localhost:5173")
    print(f"  {Colors.CYAN}后端 API:{Colors.RESET} http://localhost:8000")
    print(f"  {Colors.CYAN}API 文档:{Colors.RESET} http://localhost:8000/api-docs\n")
    print(f"  {Colors.YELLOW}按 Ctrl+C 停止所有服务{Colors.RESET}\n")

    # 保持运行并监控进程
    try:
        while process_manager.is_running:
            # 检查后端进程
            if backend_process.poll() is not None:
                print(f"\n{Colors.RED}[警告] 后端服务已停止，详情请查看 logs/backend.log{Colors.RESET}")
                break

            # 检查前端进程
            if frontend_process.poll() is not None:
                print(f"\n{Colors.RED}[警告] 前端服务已停止，详情请查看 logs/frontend.log{Colors.RESET}")
                break

            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}接收到中断信号...{Colors.RESET}")
    finally:
        process_manager.terminate_all()


if __name__ == "__main__":
    main()
