"""MariaDB 管理员凭据管理。

面板不使用 root 账号为站点创建数据库：首次启动/建站时自动创建专用管理员
账号（默认 ``sanguo_admin``），生成随机密码并保存到 shared_databases 表。
这样 MariaDB 页面展示的凭据就是真实可用的账号，站点数据库也彼此隔离。
"""
import configparser
import os
import random
import string

import mysql.connector

ADMIN_USER = "sanguo_admin"
MY_CNF = "/root/.my.cnf"


def random_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.SystemRandom().choice(alphabet) for _ in range(length))


def _read_my_cnf():
    """读取 install.sh 写入的 /root/.my.cnf（root 密码来源）。"""
    creds = {"user": "root", "password": "", "socket": ""}
    try:
        parser = configparser.ConfigParser()
        parser.read(MY_CNF)
        if parser.has_section("client"):
            creds["user"] = parser.get("client", "user", fallback="root")
            creds["password"] = parser.get("client", "password", fallback="")
            creds["socket"] = parser.get("client", "socket", fallback="")
    except Exception:
        pass
    return creds


def _connect(host: str, port: int, user: str, password: str):
    return mysql.connector.connect(
        host=host, port=int(port or 3306),
        user=user, password=password or "", connect_timeout=5,
    )


def _socket_path() -> str:
    """找到 MariaDB 的本地 socket（root 通过 socket 才拥有完整权限）。"""
    cnf = _read_my_cnf()
    candidates = [
        getattr(cnf, "socket", None),
        "/run/mysqld/mysqld.sock",
        "/var/run/mysqld/mysqld.sock",
        "/var/lib/mysql/mysql.sock",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return ""


def _connect_socket(user: str, password: str, socket_path: str):
    return mysql.connector.connect(
        unix_socket=socket_path, user=user, password=password or "", connect_timeout=5
    )


def ensure_admin_account(shared_db) -> tuple:
    """确保存在可用的专用管理员账号，返回 ``(user, password)``，失败返回 ``(None, None)``。

    ``shared_db`` 为 SharedDatabase ORM 对象。函数会就地修改其 db_user /
    db_password（调用方负责 commit），并返回可直接用于建站的值。
    """
    host = shared_db.db_host or "localhost"
    port = shared_db.db_port or 3306
    current_user = shared_db.db_user or "root"
    current_pass = shared_db.db_password or ""

    # 已配置非 root 账号且可连接：直接复用
    if current_user != "root" and current_pass:
        try:
            conn = _connect(host, port, current_user, current_pass)
            conn.close()
            return current_user, current_pass
        except Exception:
            pass

    # 用 root 通过 unix socket 连接（TCP 的 root@'%' 通常没有 CREATE USER 权限）
    cnf = _read_my_cnf()
    sock = _socket_path()
    conn = None
    attempts = []
    if sock:
        attempts.append(("socket", cnf["user"] or "root", cnf["password"]))
        attempts.append(("socket", "root", cnf["password"]))
    attempts += [
        ("tcp", cnf["user"] or "root", cnf["password"]),
        ("tcp", "root", cnf["password"]),
    ]
    for kind, user, password in attempts:
        try:
            conn = (
                _connect_socket(user, password, sock)
                if kind == "socket"
                else _connect(host, port, user, password)
            )
            break
        except Exception:
            continue
    if conn is None:
        return None, None

    password = random_password()
    # skip-name-resolve 环境下 TCP 客户端（127.0.0.1）匹配 '%'，本地 socket 匹配 'localhost'
    hosts = ("%", "localhost")
    try:
        cur = conn.cursor()
        for host_name in hosts:
            cur.execute(
                f"CREATE USER IF NOT EXISTS '{ADMIN_USER}'@'{host_name}' IDENTIFIED BY '{password}'"
            )
            cur.execute(
                f"ALTER USER '{ADMIN_USER}'@'{host_name}' IDENTIFIED BY '{password}'"
            )
            cur.execute(
                f"GRANT ALL PRIVILEGES ON *.* TO '{ADMIN_USER}'@'{host_name}' WITH GRANT OPTION"
            )
        cur.execute("FLUSH PRIVILEGES")
        cur.close()
        conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return None, None

    shared_db.db_user = ADMIN_USER
    shared_db.db_password = password
    return ADMIN_USER, password
