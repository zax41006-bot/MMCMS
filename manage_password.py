"""
密碼管理工具 - 命令行版本
用於直接在伺服器上修改資料庫中的密碼

使用方法:
  python3 manage_password.py set <新密碼>    # 直接設定新密碼
  python3 manage_password.py info            # 查看帳號資訊
  python3 manage_password.py logs            # 查看最近登入記錄
"""

import sys
import os
import sqlite3
import bcrypt
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "mmc.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def set_password(new_password):
    """直接設定新密碼（無需舊密碼）"""
    if len(new_password) < 8:
        print("❌ 錯誤：密碼長度至少需要 8 個字符")
        return

    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
    conn = get_db()
    conn.execute(
        "UPDATE users SET password = ? WHERE username = 'admin'",
        (hashed.decode("utf-8"),)
    )
    conn.commit()
    conn.close()
    print(f"✅ 密碼已成功更新！")
    print(f"   新密碼：{new_password}")
    print(f"   雜湊值：{hashed.decode('utf-8')[:30]}...")


def show_info():
    """顯示帳號資訊"""
    conn = get_db()
    rows = conn.execute("SELECT id, username, role, created_at FROM users").fetchall()
    print("\n=== 帳號列表 ===")
    for row in rows:
        print(f"  ID: {row['id']} | 帳號: {row['username']} | 角色: {row['role']} | 建立時間: {row['created_at']}")
    conn.close()


def show_logs(limit=20):
    """顯示最近登入記錄"""
    conn = get_db()
    rows = conn.execute(
        "SELECT username, ip, success, created_at FROM login_log ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    print(f"\n=== 最近 {limit} 筆登入記錄 ===")
    for row in rows:
        status = "✅ 成功" if row["success"] else "❌ 失敗"
        print(f"  {row['created_at']} | {status} | IP: {row['ip']}")
    conn.close()


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print("❌ 資料庫不存在，請先啟動 app.py 初始化資料庫")
        sys.exit(1)

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "set":
        if len(sys.argv) < 3:
            print("❌ 請提供新密碼：python3 manage_password.py set <新密碼>")
        else:
            set_password(sys.argv[2])

    elif cmd == "info":
        show_info()

    elif cmd == "logs":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        show_logs(limit)

    else:
        print(f"❌ 未知命令：{cmd}")
        print(__doc__)
