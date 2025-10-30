# 🚀 Deployment Guide - Railway

This guide will help you deploy Odoo with WhatsApp integration to Railway.

---

## ⚠️ IMPORTANT: Before Pushing to GitHub

### Files That Should NOT Be Pushed:
- ❌ `odoo.conf` (contains credentials)
- ❌ `docker-compose.yml` (contains credentials)
- ❌ `addons/` (enterprise addons - proprietary)
- ❌ `.env` files (if any)

### Files That ARE Safe to Push:
- ✅ `odoo.conf.example` (template without credentials)
- ✅ `docker-compose.example.yml` (template without credentials)
- ✅ `.env.example` (template without credentials)
- ✅ All custom modules (`cl_contact_*`, `queue_job`, etc.)
- ✅ `Dockerfile`, `SETUP.md`, etc.

The `.gitignore` has been updated to protect sensitive files automatically.

---

## 📋 Prerequisites

1. **GitHub Account** (for deploying from GitHub to Railway)
2. **Railway Account** (sign up at https://railway.app)
3. **WhatsApp Business API** credentials:
   - Phone Number ID
   - Business Account ID
   - API Token
   - Webhook Verify Token

---

## 🔧 Step 1: Prepare GitHub Repository

### Option A: Add GitHub as Remote (Dual Remote)

```bash
# Add GitHub as additional remote
git remote add github https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Verify remotes
git remote -v

# You should see:
# origin    https://gitlab.com/... (GitLab - vendor)
# github    https://github.com/... (GitHub - for Railway)
```

### Option B: Create Separate Repository

```bash
# Clone to new folder
cd ~/Documents/engineering/
git clone colearn-dev colearn-railway
cd colearn-railway

# Change remote to GitHub
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
```

---

## 📤 Step 2: Push to GitHub

```bash
# Stage all safe files
git add .

# Commit
git commit -m "feat: prepare for Railway deployment"

# Push to GitHub
git push github development  # If using dual remote
# OR
git push origin development  # If using separate repo
```

### Verify Sensitive Files Are Ignored

```bash
# This should show that odoo.conf, docker-compose.yml, addons/ are ignored
git status --ignored
```

---

## 🚂 Step 3: Deploy to Railway

### 3.1 Create Railway Project

1. Go to https://railway.app
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Authorize Railway to access your GitHub
5. Select your repository

### 3.2 Add PostgreSQL Database

1. Click **"+ New"** in your project
2. Select **"Database" → "PostgreSQL"**
3. Railway will automatically create a PostgreSQL instance
4. Note the connection details (will be available as `DATABASE_URL`)

### 3.3 Configure Environment Variables

In Railway dashboard, go to your Odoo service → **Variables** tab:

**Required Variables:**

```bash
# Database (auto-provided by Railway if you added PostgreSQL)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Odoo Configuration
ODOO_ADMIN_PASSWORD=your-strong-master-password-here
ODOO_DB_NAME=odoo_production

# WhatsApp API
WHATSAPP_API_TOKEN=your-whatsapp-api-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
WHATSAPP_BUSINESS_ACCOUNT_ID=your-business-account-id
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your-random-secret-token

# Server Configuration
PORT=8069
PROXY_MODE=True
```

**Optional Variables (for Metabase integration):**

```bash
METABASE_API_URL=https://metabase.your-domain.com
METABASE_USERNAME=your-username
METABASE_PASSWORD=your-password
```

### 3.4 Create Production Dockerfile

Railway needs a production-ready Dockerfile. Create `Dockerfile.railway`:

```dockerfile
# Use official Odoo 18.0 image
FROM odoo:18.0

USER root

# Install additional dependencies
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    phonenumbers \
    geoip2

# Create directories
RUN mkdir -p /mnt/custom-addons

# Copy custom modules
COPY . /mnt/custom-addons/

# Fix permissions
RUN chown -R odoo:odoo /mnt/custom-addons

USER odoo

# Expose ports
EXPOSE 8069 8072

# Start command (will use environment variables)
CMD ["odoo", \
     "--addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/custom-addons", \
     "--db_host=${DB_HOST}", \
     "--db_port=${DB_PORT}", \
     "--db_user=${DB_USER}", \
     "--db_password=${DB_PASSWORD}", \
     "--http-port=8069", \
     "--proxy-mode", \
     "--without-demo=all"]
```

### 3.5 Deploy!

Railway will automatically:
1. Detect your `Dockerfile`
2. Build the image
3. Deploy the container
4. Assign a public URL (e.g., `your-app.railway.app`)

---

## 🔗 Step 4: Configure WhatsApp Webhook

Once deployed, get your Railway public URL (e.g., `https://your-app.railway.app`)

### 4.1 Set Webhook URL in Meta Developer Console

1. Go to https://developers.facebook.com
2. Select your WhatsApp app
3. Go to **WhatsApp → Configuration → Webhook**
4. Set webhook URL:
   ```
   https://your-app.railway.app/whatsapp/webhook
   ```
5. Set verify token (same as `WHATSAPP_WEBHOOK_VERIFY_TOKEN`)
6. Subscribe to webhook fields:
   - `messages`
   - `message_status`

### 4.2 Test Webhook

Send a test message to your WhatsApp Business number. Check Railway logs:

```bash
# View logs in Railway dashboard or CLI
railway logs
```

---

## 📊 Step 5: Monitor & Troubleshoot

### View Logs

In Railway dashboard:
- Click on your service
- Go to **"Deployments"** tab
- Click on latest deployment
- View **"Logs"** tab

### Common Issues

**Issue: Database connection failed**
- Solution: Check `DATABASE_URL` environment variable
- Ensure PostgreSQL service is running

**Issue: Webhook not receiving messages**
- Solution: Verify webhook URL in Meta console
- Check `WHATSAPP_WEBHOOK_VERIFY_TOKEN` matches
- View Railway logs for errors

**Issue: Module not found**
- Solution: Rebuild and redeploy
- Ensure all custom modules are pushed to GitHub

---

## 💰 Cost Estimation

Railway pricing (as of 2024):
- **Free Tier**: $5 credit/month (good for testing)
- **Hobby Plan**: $5/month base + usage
- **Estimated cost**: ~$10-20/month

PostgreSQL usage:
- Included in plan
- ~$5-10/month depending on size

**Total: ~$15-30/month**

---

## 🔄 Update Deployment

When you make code changes:

```bash
# Commit changes
git add .
git commit -m "feat: your changes"

# Push to GitHub
git push github development

# Railway will automatically rebuild and redeploy!
```

---

## 📚 Resources

- Railway Docs: https://docs.railway.app
- Odoo Deployment: https://www.odoo.com/documentation/18.0/administration/on_premise/deploy.html
- WhatsApp Business API: https://developers.facebook.com/docs/whatsapp

---

## ⚡ Quick Commands

```bash
# View Railway logs
railway logs --follow

# SSH into Railway container
railway shell

# Restart service
railway restart

# Check status
railway status
```

---

**Happy deploying! 🎉**
