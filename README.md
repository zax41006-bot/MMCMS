# 澳門氣象警報管理平臺 (MMC) — 後端版本

## 架構說明

| 層次 | 技術 | 說明 |
|------|------|------|
| 前端 | HTML + JavaScript | `static/index.html`，密碼驗證透過 API 呼叫，不再硬編碼 |
| 後端 | Python Flask | `app.py`，提供 REST API，管理 session |
| 資料庫 | SQLite | `mmc.db`，儲存 bcrypt 雜湊後的密碼及登入記錄 |

## 安全改進

- **密碼不再寫在 HTML 代碼中**，任何人查看原始碼都看不到密碼
- 密碼以 **bcrypt 雜湊**儲存於資料庫，即使資料庫洩露也無法還原明文
- 使用**伺服器端 session** 管理登入狀態，session 資料不暴露於客戶端
- 記錄每次登入嘗試（成功/失敗 + IP 地址）於 `login_log` 表

## 安裝與啟動

### 1. 安裝依賴

```bash
pip3 install flask bcrypt flask-session
```

### 2. 啟動伺服器

```bash
cd mmc_weather
python3 app.py
```

首次啟動會自動建立資料庫，並建立預設帳號：
- **預設密碼**：`moweather2021`
- 請盡快透過「修改密碼」功能更改！

### 3. 訪問平臺

瀏覽器打開：`http://localhost:5000`

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| `POST` | `/api/login` | 驗證密碼，建立 session |
| `POST` | `/api/logout` | 登出，清除 session |
| `GET` | `/api/check-auth` | 檢查 session 是否有效 |
| `POST` | `/api/change-password` | 修改密碼（需已登入） |

## 密碼管理工具（命令行）

```bash
# 查看帳號資訊
python3 manage_password.py info

# 直接設定新密碼（緊急用途）
python3 manage_password.py set <新密碼>

# 查看最近登入記錄
python3 manage_password.py logs
python3 manage_password.py logs 50  # 查看最近50筆
```

## 部署到生產環境

建議使用 **Gunicorn + Nginx** 部署：

```bash
pip3 install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

> **注意**：生產環境中，`app.py` 的 `SECRET_KEY` 應改為固定值並妥善保管，
> 否則每次重啟後所有 session 都會失效。

## 檔案結構

```
mmc_weather/
├── app.py                 # Flask 後端主程式
├── manage_password.py     # 密碼管理命令行工具
├── mmc.db                 # SQLite 資料庫（自動建立）
├── flask_session/         # Session 檔案目錄（自動建立）
└── static/
    └── index.html         # 前端頁面
```
