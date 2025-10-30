# Odoo Development Environment Setup

## ✅ Status Saat Ini

- [x] Odoo Enterprise downloaded
- [x] Enterprise modules (helpdesk & whatsapp) tersedia
- [x] Symlink ke addons sudah dibuat
- [x] Development script (`odoo-dev.sh`) sudah dibuat
- [ ] PostgreSQL perlu diinstall
- [ ] Python dependencies perlu diinstall

---

## 🚀 Quick Start Guide

### Step 1: Install PostgreSQL

#### Opsi A: Menggunakan Homebrew (Recommended)
```bash
# Install Homebrew jika belum ada
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install PostgreSQL
brew install postgresql@16

# Start PostgreSQL service
brew services start postgresql@16

# Create Odoo database user
createuser -s odoo
```

#### Opsi B: Download dari postgresql.org
1. Download dari: https://www.postgresql.org/download/macosx/
2. Install dan follow wizard
3. Create user `odoo` dengan superuser privileges

### Step 2: Install Python Dependencies

```bash
cd ~/Documents/engineering/odoo-18.0+e.20251009

# Install dependencies (might take 5-10 minutes)
pip3 install -r requirements.txt
```

**Note:** Beberapa package mungkin perlu system dependencies (libxml2, libxslt, dll). Jika ada error:

```bash
# Install system dependencies via Homebrew
brew install libxml2 libxslt
```

### Step 3: Initialize Odoo Database

```bash
cd ~/Documents/engineering/colearn-dev

# Initialize database with base modules
./odoo-dev.sh --init base --stop-after-init

# Install helpdesk & whatsapp
./odoo-dev.sh -i helpdesk,whatsapp --stop-after-init
```

### Step 4: Run Odoo

```bash
# Start Odoo server
./odoo-dev.sh

# Access: http://localhost:8069
# Default DB: testdb
```

---

## 🔧 Development Commands

### Start Odoo Server
```bash
./odoo-dev.sh
```

### Install/Update Modules
```bash
# Install custom modules
./odoo-dev.sh -i cl_helpdesk_whatsapp,cl_helpdesk_sla,cl_helpdesk_access

# Update modules
./odoo-dev.sh -u cl_helpdesk_whatsapp

# Install + Update multiple
./odoo-dev.sh -i module1 -u module2,module3
```

### Development Mode Options
```bash
# Already enabled in odoo-dev.sh:
# --dev=all : Auto-reload on file changes, detailed logs
```

### Use Different Database
```bash
# Set environment variable
export ODOO_DB=mydb
./odoo-dev.sh

# Or inline
ODOO_DB=mydb ./odoo-dev.sh
```

---

## 📁 Project Structure

```
Documents/engineering/
├── colearn-dev/              # Custom modules (this repo)
│   ├── addons/              # → Symlink to Odoo addons
│   ├── cl_contact_base/
│   ├── cl_helpdesk_access/
│   ├── cl_helpdesk_sla/
│   ├── cl_helpdesk_whatsapp/
│   ├── queue_job/
│   ├── odoo-dev.sh          # Development wrapper script
│   └── SETUP.md             # This file
│
└── odoo-18.0+e.20251009/    # Odoo Enterprise
    ├── odoo/
    │   └── addons/
    │       ├── helpdesk/    # Enterprise module
    │       ├── whatsapp/    # Enterprise module
    │       └── ... (1300+ modules)
    └── requirements.txt
```

---

## 🐛 Troubleshooting

### Error: `ModuleNotFoundError: No module named 'psycopg2'`
```bash
pip3 install psycopg2-binary
```

### Error: `FATAL:  role "odoo" does not exist`
```bash
createuser -s odoo
```

### Error: `could not connect to server`
```bash
# Check if PostgreSQL is running
brew services list | grep postgresql

# Start if not running
brew services start postgresql@16
```

### Error: Dependencies installation failed
```bash
# Install system dependencies
brew install libpq libxml2 libxslt openssl

# Retry pip install
pip3 install -r ~/Documents/engineering/odoo-18.0+e.20251009/requirements.txt
```

### Module tidak muncul di Odoo
1. Pastikan module sudah di addons path
2. Aktifkan Developer Mode: Settings → Activate Developer Mode
3. Update Apps List: Apps → Update Apps List
4. Search module name

---

## 📚 Useful Links

- Odoo Documentation: https://www.odoo.com/documentation/18.0/
- Odoo Developer Docs: https://www.odoo.com/documentation/18.0/developer.html
- PostgreSQL Docs: https://www.postgresql.org/docs/

---

## ⚡ Next Steps

1. Install PostgreSQL
2. Install Python dependencies
3. Initialize database
4. Start development!

Selamat coding! 🚀
