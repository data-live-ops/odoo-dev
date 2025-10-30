# 🚂 Railway Setup Checklist

Quick guide untuk fix database connection dan deploy Odoo + WhatsApp ke Railway.

---

## ✅ CHECKLIST STEP-BY-STEP

### **1. Add PostgreSQL Database** ✓

Di Railway Dashboard:
- [ok] Klik **"+ New"** atau **"+ Add Service"**
- [ok] Pilih **"Database" → "Add PostgreSQL"**
- [ok] Tunggu PostgreSQL provisioning selesai
- [ok] Verify: Anda sekarang punya 2 services (web + postgres)

---

### **2. Configure Environment Variables**

Di Railway Dashboard → **Service Odoo Anda** → Tab **"Variables"**:

#### **A. Database Variables (Auto dari PostgreSQL)**

Railway auto-provide variables ini setelah add PostgreSQL. Tambahkan ke Odoo service:

```bash
# Reference PostgreSQL service variables
PGHOST=${{Postgres.PGHOST}}
PGPORT=${{Postgres.PGPORT}}
PGUSER=${{Postgres.PGUSER}}
PGPASSWORD=${{Postgres.PGPASSWORD}}
PGDATABASE=${{Postgres.PGDATABASE}}
```

Atau pakai DATABASE_URL (lebih simple):

```bash
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

#### **B. Odoo Configuration (Manual input)**

```bash
# Database name untuk Odoo
DB_NAME=odoo_production

# Master password Odoo (GANTI INI!)
ADMIN_PASSWD=your-super-strong-password-here-123!@#

# Server settings
HTTP_PORT=8069
PROXY_MODE=True
WORKERS=2
MAX_CRON_THREADS=2

# Timeout settings (untuk sync Metabase yang lama)
LIMIT_TIME_CPU=600
LIMIT_TIME_REAL=1200

# Disable demo data
WITHOUT_DEMO=all
```

#### **C. WhatsApp Configuration (Optional, untuk nanti)**

```bash
# WhatsApp Business API
WHATSAPP_API_TOKEN=your-whatsapp-api-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
WHATSAPP_BUSINESS_ACCOUNT_ID=your-business-account-id
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your-random-secret-token-123
```

**Checklist:**
- [ ] DATABASE_URL sudah diset (reference ke Postgres service)
- [ ] DB_NAME sudah diset
- [ ] ADMIN_PASSWD sudah diganti (jangan pakai "admin"!)
- [ ] HTTP_PORT = 8069
- [ ] PROXY_MODE = True

---

### **3. Push Code Changes**

File-file baru yang sudah dibuat:
- `Dockerfile.railway` - Production Dockerfile
- `docker-entrypoint-railway.sh` - Startup script
- `railway.toml` - Railway config
- `.dockerignore` - Updated

**Commit & Push:**

```bash
# Stage all files
git add .

# Commit
git commit -m "feat: configure Railway deployment with PostgreSQL

- Add Dockerfile.railway with environment variable support
- Add docker-entrypoint-railway.sh for dynamic database config
- Add railway.toml configuration
- Update .dockerignore to exclude unnecessary files
"

# Push ke GitHub (Railway akan auto-deploy)
git push github your-branch-name
```

**Checklist:**
- [ ] File `Dockerfile.railway` sudah di commit
- [ ] File `docker-entrypoint-railway.sh` sudah di commit
- [ ] File `railway.toml` sudah di commit
- [ ] Sudah push ke GitHub

---

### **4. Verify Deployment**

Setelah push, Railway akan otomatis rebuild dan redeploy.

**Di Railway Dashboard:**
- [ ] Klik service Odoo Anda
- [ ] Tab **"Deployments"** → lihat progress
- [ ] Tunggu status **"Success"** (hijau)
- [ ] Klik **"View Logs"**

**Expected Logs (Success):**

```
🚀 Starting Odoo on Railway...
📊 Database: xxxxx.railway.internal:5432/railway
📦 Custom Addons Path: /mnt/custom-addons
...
odoo.service.server: HTTP service (werkzeug) running on 0.0.0.0:8069
```

**Jika masih error:**
- [ ] Check environment variables sudah benar semua
- [ ] Check DATABASE_URL reference ke Postgres service
- [ ] Check logs untuk error message spesifik

---

### **5. Access Odoo**

Setelah deployment success:

**Get URL:**
- [ ] Di Railway Dashboard → Service Odoo → Tab **"Settings"**
- [ ] Scroll ke **"Networking"**
- [ ] Copy **"Public Domain"** (e.g., `xxx-production-xxxx.up.railway.app`)

**Access:**
- [ ] Buka browser: `https://your-railway-url.railway.app`
- [ ] Anda akan lihat **Odoo Database Manager**

---

### **6. Initialize Odoo Database**

**Di halaman Database Manager:**

1. **Master Password:**
   - Input: Password yang Anda set di `ADMIN_PASSWD` env variable

2. **Database Name:**
   - Input: `odoo_production` (sesuai env `DB_NAME`)

3. **Email:**
   - Input: Email admin Anda

4. **Password:**
   - Input: Password untuk admin user Odoo

5. **Phone Number:** (optional)

6. **Language:** Indonesian / English

7. **Country:** Indonesia

8. **Demo Data:** Uncheck (jangan install demo data)

9. Klik **"Create Database"**

**Checklist:**
- [ ] Database created successfully
- [ ] Login dengan email & password yang dibuat
- [ ] Masuk ke Odoo dashboard

---

### **7. Install Modules**

Di Odoo (setelah login):

1. **Aktifkan Developer Mode:**
   - Settings → Activate Developer Mode

2. **Update Apps List:**
   - Apps menu → Update Apps List → Update

3. **Install Required Modules:**

**Base Modules:**
- [ ] `helpdesk` - Helpdesk module (Enterprise)
- [ ] `whatsapp` - WhatsApp integration (Enterprise)
- [ ] `contacts` - Contacts module

**Custom Modules:**
- [ ] `queue_job` - Background job queue
- [ ] `cl_contact_base` - CoLearn contact base
- [ ] `cl_helpdesk_access` - Helpdesk access control
- [ ] `cl_helpdesk_sla` - Helpdesk SLA
- [ ] `cl_helpdesk_whatsapp` - WhatsApp auto-ticket creation
- [ ] `cl_contact_metabase` - Metabase integration (optional)

**Cara Install:**
- Apps → Remove "Apps" filter
- Search module name
- Click "Install"

---

### **8. Configure WhatsApp Integration**

**A. Setup WhatsApp Account di Odoo:**

1. Go to **Settings → WhatsApp → WhatsApp Business Accounts**
2. Create new WhatsApp account:
   - Name: Your business name
   - Phone Number ID: (dari Meta Developer Console)
   - Business Account ID: (dari Meta Developer Console)
   - Access Token: (dari Meta Developer Console)

**B. Get Railway Webhook URL:**

Your webhook URL will be:
```
https://your-railway-url.railway.app/whatsapp/webhook
```

**C. Configure Webhook di Meta Developer Console:**

1. Go to https://developers.facebook.com
2. Select your WhatsApp App
3. Go to **WhatsApp → Configuration → Webhook**
4. Set:
   - **Callback URL:** `https://your-railway-url.railway.app/whatsapp/webhook`
   - **Verify Token:** (set di env var `WHATSAPP_WEBHOOK_VERIFY_TOKEN`)
5. Subscribe to fields:
   - `messages`
   - `message_status`
6. Click **"Verify and Save"**

**Checklist:**
- [ ] WhatsApp account created di Odoo
- [ ] Webhook URL configured di Meta
- [ ] Webhook verified (status: ✓)
- [ ] Test send message → ticket auto-created

---

### **9. Test Everything**

**Test 1: WhatsApp → Helpdesk Ticket**
- [ ] Send message ke WhatsApp Business number
- [ ] Check di Odoo → Helpdesk → Tickets
- [ ] Ticket auto-created? ✓

**Test 2: Send Reply dari Odoo**
- [ ] Buka ticket
- [ ] Reply via WhatsApp button
- [ ] Customer receive message? ✓

**Test 3: Metabase Sync (Optional)**
- [ ] Settings → Metabase Settings
- [ ] Test Connection
- [ ] Manually run sync
- [ ] Check logs untuk errors

---

## 🔍 TROUBLESHOOTING

### Issue: "Database connection failure"

**Solution:**
```bash
# Check environment variables
Railway Dashboard → Service Odoo → Variables

# Must have:
DATABASE_URL=${{Postgres.DATABASE_URL}}  # atau
PGHOST=${{Postgres.PGHOST}}              # individual vars
```

### Issue: "Module not found"

**Solution:**
- Ensure module pushed ke GitHub
- Rebuild: Railway Dashboard → Deployments → "Redeploy"
- Check logs: Module loaded atau ada error?

### Issue: "Webhook verification failed"

**Solution:**
- Check `WHATSAPP_WEBHOOK_VERIFY_TOKEN` env var
- Must match dengan token di Meta Developer Console
- Webhook URL harus HTTPS (Railway auto-provide)

### Issue: "502 Bad Gateway"

**Solution:**
- Odoo masih starting up (tunggu 2-3 menit)
- Check logs untuk errors
- Ensure database initialized

### Issue: "Timeout errors"

**Solution:**
```bash
# Increase timeout di env vars:
LIMIT_TIME_CPU=900
LIMIT_TIME_REAL=1800
```

---

## 📊 MONITORING

### View Logs

```bash
# Di Railway Dashboard
Service → Deployments → Latest → View Logs
```

### Monitor Database

```bash
# Di Railway Dashboard
Postgres service → Metrics
# Check: CPU, Memory, Connections
```

### Check Health

```
https://your-railway-url.railway.app/web/health
```

Should return: `{"status": "pass"}`

---

## 💰 COST ESTIMATION

**Railway Pricing (as of 2024):**

| Service | Cost |
|---------|------|
| Free Trial | $5 credit/month |
| Hobby Plan | $5/month + usage |
| Odoo Service | ~$5-10/month (512MB-1GB RAM) |
| PostgreSQL | ~$5-10/month (500MB-1GB storage) |
| **Total** | **~$10-20/month** |

**Tips untuk hemat:**
- Disable modules yang tidak terpakai
- Set workers = 2 (jangan lebih)
- Monitor RAM usage di Railway Metrics

---

## 📚 NEXT STEPS

Setelah semua setup:

- [ ] Setup daily backup database
- [ ] Configure custom domain (optional)
- [ ] Setup monitoring/alerts (optional)
- [ ] Document API endpoints untuk team
- [ ] Train team untuk pakai WhatsApp integration

---

**Need help?** Check Railway Discord atau documentation:
- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway

---

**Happy deploying! 🚀**
