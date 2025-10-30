# Odoo Docker Development Environment

## 🎉 Setup Complete!

Your Odoo Docker environment is now ready for development!

---

## 🚀 Quick Start

### Start Docker Environment
```bash
cd ~/Documents/engineering/colearn-dev
docker-compose up -d
```

### Access Odoo
- **URL:** http://localhost:8069
- **Database:** odoo_docker
- **Username:** admin
- **Password:** admin

### Stop Docker Environment
```bash
docker-compose down
```

### Restart After Code Changes
```bash
docker-compose restart odoo
```

---

## 📋 Common Commands

### View Logs
```bash
# All logs
docker-compose logs -f

# Odoo logs only
docker-compose logs -f odoo

# Last 50 lines
docker-compose logs --tail=50 odoo
```

### Install Modules
```bash
# Install module via command line
docker-compose exec odoo odoo -d odoo_docker -i helpdesk,whatsapp --stop-after-init

# Then restart
docker-compose restart odoo
```

### Database Management
```bash
# Backup database
docker-compose exec db pg_dump -U odoo odoo_docker > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T db psql -U odoo odoo_docker
```

### Access Container Shell
```bash
# Odoo container
docker-compose exec odoo bash

# Database container
docker-compose exec db bash
```

---

## 📁 Project Structure

```
colearn-dev/
├── docker-compose.yml      # Docker services configuration
├── Dockerfile             # Custom Odoo image
├── odoo.conf             # Odoo configuration
├── .dockerignore         # Docker build ignore
├── DOCKER-SETUP.md       # This file
│
├── addons/               # Symlink to enterprise addons
├── cl_contact_base/      # Custom module (mounted)
├── cl_helpdesk_access/   # Custom module (mounted)
├── cl_helpdesk_sla/      # Custom module (mounted)
├── cl_helpdesk_whatsapp/ # Custom module (mounted)
└── queue_job/            # Custom module (mounted)
```

---

## 🔧 Development Workflow

### 1. Edit Code
Edit your custom modules directly in the colearn-dev folder. Docker will mount them automatically.

### 2. See Changes
The `--dev=all` flag is enabled, so changes will auto-reload (for most cases).

### 3. Manual Reload
If auto-reload doesn't work:
```bash
docker-compose restart odoo
```

### 4. Update Module
After significant changes:
```bash
docker-compose exec odoo odoo -d odoo_docker -u cl_helpdesk_whatsapp --stop-after-init
docker-compose restart odoo
```

---

## 📦 Install Modules

### Enterprise Modules (helpdesk, whatsapp)
```bash
docker-compose exec odoo odoo -d odoo_docker -i helpdesk,whatsapp --stop-after-init
docker-compose restart odoo
```

### Custom Modules
```bash
docker-compose exec odoo odoo -d odoo_docker -i cl_contact_base,queue_job,cl_helpdesk_access,cl_helpdesk_sla,cl_helpdesk_whatsapp --stop-after-init
docker-compose restart odoo
```

---

## 🐛 Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs odoo

# Check if ports are in use
lsof -i :8069
lsof -i :5433

# Rebuild if needed
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Database issues
```bash
# Reset database (WARNING: destroys data!)
docker-compose down -v
docker-compose up -d
```

### Permission errors
```bash
# Fix permissions
docker-compose exec odoo chown -R odoo:odoo /var/lib/odoo
```

---

## ⚡ Performance Tips

1. **Use volumes:** Docker volumes are faster than bind mounts
2. **Limit workers:** Set to 0 for development (already configured)
3. **Enable dev mode:** Already enabled with `--dev=all`
4. **Watch logs:** Monitor for slow queries or errors

---

## 🔄 Switching Between Manual and Docker

### Use Docker (Default)
```bash
cd ~/Documents/engineering/colearn-dev
docker-compose up -d
# Access: http://localhost:8069
```

### Use Manual Setup
```bash
# Stop Docker first
cd ~/Documents/engineering/colearn-dev
docker-compose down

# Start manual
./odoo-dev.sh
# Access: http://localhost:8069
```

**Note:** Both use different databases, so data won't sync.

---

## 📚 Resources

- Odoo Documentation: https://www.odoo.com/documentation/18.0/
- Docker Compose: https://docs.docker.com/compose/
- PostgreSQL: https://www.postgresql.org/docs/

---

Happy coding! 🚀
