# ☁️ Vanta Cloud

**Your files. Your space. Completely private.**

Vanta Cloud is a private, self-hosted cloud storage web application built with **FastAPI**.

It is designed for personal and family use, allowing files to be stored and managed from a clean web interface while the actual data remains on your own computer.

---

## ✨ Features

- 🔐 Secure login system
- 👤 Admin and Member accounts
- 📁 Upload and manage files
- 🔎 Search files
- 👁️ File previews
- ⬇️ File downloads
- ✏️ Rename files
- 🗑️ Trash and restore system
- 🔥 Permanent deletion
- ⏳ Automatic Trash retention
- 📜 Admin Activity Log
- 🎨 Dark, Light and System themes
- 👥 Per-user theme preferences
- ⚙️ Admin settings panel
- 🛡️ CSRF protection
- 🔒 Password hashing with Argon2
- 📱 Responsive desktop and mobile interface
- 🌐 LAN access support
- ☁️ Optional Cloudflare Tunnel access

---

## 🧱 Tech Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Uvicorn
- Jinja2

### Frontend

- HTML
- CSS
- JavaScript

### Security

- Argon2 password hashing
- Signed sessions
- CSRF protection
- Role-based permissions
- Protected file routes

---

## 📂 Storage

Vanta Cloud keeps the application and stored files separate.

By default, uploaded files are stored in:

```text
C:\FamilyCloudStorage
