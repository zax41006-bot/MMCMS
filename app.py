"""
澳門氣象警報管理平臺 - 後端 API
Flask + SQLite + bcrypt 密碼驗證
"""

import os
import sqlite3
import secrets
import bcrypt
from flask import (
    Flask, request, jsonify, session,
    send_from_directory, redirect, url_for
)
from flask_session import Session
from datetime import timedelta

# ─── 應用初始化 ──────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="static")

# Session 配置（伺服器端 session，不暴露於客戶端）
app.config["SECRET_KEY"] = secrets.token_hex(32)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(os.path.dirname(__file__), "flask_session")
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
Session(app)

# ─── 資料庫路徑 ──────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "mmc.db")


def get_db():
    """取得 SQLite 連線"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化資料庫，建立 users 表並插入預設管理員帳號"""
    conn = get_db()
    cur = conn.cursor()

    # 建立 users 表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    NOT NULL UNIQUE,
            password TEXT    NOT NULL,
            role     TEXT    NOT NULL DEFAULT 'user',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 建立 login_log 表（可選，用於審計）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS login_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT,
            ip         TEXT,
            success    INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 若 admin 帳號不存在，插入預設帳號（密碼：moweather2021）
    cur.execute("SELECT id FROM users WHERE username = 'admin'")
    if cur.fetchone() is None:
        default_password = "moweather2021"
        hashed = bcrypt.hashpw(default_password.encode("utf-8"), bcrypt.gensalt())
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", hashed.decode("utf-8"), "admin")
        )
        print(f"[INIT] 已建立預設管理員帳號 admin，密碼：{default_password}")
        print("[WARN] 請盡快透過 /api/change-password 修改密碼！")

    conn.commit()
    conn.close()


# ─── API 路由 ─────────────────────────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def api_login():
    """
    密碼驗證 API
    Request JSON: { "password": "xxx" }
    Response JSON: { "success": true/false, "message": "..." }
    """
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")

    if not password:
        return jsonify({"success": False, "message": "請輸入密碼"}), 400

    conn = get_db()
    # 此平臺使用單一共用密碼（admin 帳號），可擴展為多用戶
    cur = conn.execute("SELECT password FROM users WHERE username = 'admin'")
    row = cur.fetchone()
    conn.close()

    if row is None:
        return jsonify({"success": False, "message": "系統錯誤，請聯絡管理員"}), 500

    stored_hash = row["password"].encode("utf-8")
    ip = request.remote_addr

    if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
        session["authenticated"] = True
        session["username"] = "admin"
        # 記錄成功登入
        _log_login("admin", ip, success=1)
        return jsonify({"success": True, "message": "登入成功"})
    else:
        # 記錄失敗嘗試
        _log_login("admin", ip, success=0)
        return jsonify({"success": False, "message": "密碼錯誤，請重新輸入！"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    """登出 API"""
    session.clear()
    return jsonify({"success": True, "message": "已登出"})


@app.route("/api/check-auth", methods=["GET"])
def api_check_auth():
    """檢查目前 session 是否已驗證"""
    if session.get("authenticated"):
        return jsonify({"authenticated": True})
    return jsonify({"authenticated": False}), 401


@app.route("/api/change-password", methods=["POST"])
def api_change_password():
    """
    修改密碼 API（需已登入）
    Request JSON: { "old_password": "xxx", "new_password": "yyy" }
    """
    if not session.get("authenticated"):
        return jsonify({"success": False, "message": "未授權，請先登入"}), 403

    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not old_password or not new_password:
        return jsonify({"success": False, "message": "請填寫舊密碼和新密碼"}), 400

    if len(new_password) < 8:
        return jsonify({"success": False, "message": "新密碼長度至少需要 8 個字符"}), 400

    conn = get_db()
    cur = conn.execute("SELECT password FROM users WHERE username = 'admin'")
    row = cur.fetchone()

    if row is None:
        conn.close()
        return jsonify({"success": False, "message": "系統錯誤"}), 500

    stored_hash = row["password"].encode("utf-8")

    if not bcrypt.checkpw(old_password.encode("utf-8"), stored_hash):
        conn.close()
        return jsonify({"success": False, "message": "舊密碼不正確"}), 401

    new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
    conn.execute(
        "UPDATE users SET password = ? WHERE username = 'admin'",
        (new_hash.decode("utf-8"),)
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "密碼已成功修改"})


# ─── 靜態檔案服務 ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """提供主頁面"""
    return send_from_directory("static", "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


# ─── 工具函數 ─────────────────────────────────────────────────────────────────

def _log_login(username, ip, success):
    """記錄登入嘗試到資料庫"""
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO login_log (username, ip, success) VALUES (?, ?, ?)",
            (username, ip, success)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


# ─── 啟動 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
    init_db()
    print("=" * 50)
    print("  澳門氣象警報管理平臺 後端服務")
    print("  訪問地址: http://localhost:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False)
