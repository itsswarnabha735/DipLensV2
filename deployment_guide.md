# Deployment Guide for DipLens v2

This guide outlines the steps to host the DipLens v2 application on a Linux server (Ubuntu 22.04 LTS recommended).

## 1. Server Prerequisites

*   **OS**: Ubuntu 22.04 LTS
*   **Resources**: Minimum 2GB RAM (4GB recommended for build processes), 1-2 vCPUs.
*   **Access**: SSH access to the server.
*   **Domain**: A domain name pointing to your server's IP (optional but recommended for SSL).

## 2. Initial Server Setup

Update the system and install essential tools:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git nginx build-essential
```

### Install Node.js (v20 LTS)
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### Install Python (3.10+) and pip
Ubuntu 22.04 comes with Python 3.10. Install `pip` and `venv`:
```bash
sudo apt install -y python3-pip python3-venv
```

### Install PM2 (Process Manager)
We will use PM2 to manage the Next.js frontend process.
```bash
sudo npm install -g pm2
```

## 3. Project Setup

Clone your repository to the server (usually in `/var/www` or `~/apps`).

```bash
mkdir -p ~/apps
cd ~/apps
git clone <YOUR_REPO_URL> diplens-v2
cd diplens-v2
```

## 4. Backend Deployment (FastAPI)

Navigate to the backend directory:
```bash
cd backend
```

### Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
pip install gunicorn  # Required for production deployment
```

### Environment Variables
Create a `.env` file in the `backend/` directory:
```bash
nano .env
```
Add your secrets (API keys, DB paths, etc.):
```ini
# Example
DATABASE_URL=sqlite:///./alerts.db
# Add other keys from your local .env
```

### Create a Systemd Service
Instead of running manually, create a service to keep the backend running.

```bash
sudo nano /etc/systemd/system/diplens-backend.service
```

Paste the following (adjust paths and user):

```ini
[Unit]
Description=Gunicorn instance to serve DipLens Backend
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/apps/diplens-v2/backend
Environment="PATH=/home/ubuntu/apps/diplens-v2/backend/venv/bin"
ExecStart=/home/ubuntu/apps/diplens-v2/backend/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 127.0.0.1:8000

[Install]
WantedBy=multi-user.target
```

Start and enable the service:
```bash
sudo systemctl start diplens-backend
sudo systemctl enable diplens-backend
```

## 5. Frontend Deployment (Next.js)

Navigate back to the root directory:
```bash
cd ~/apps/diplens-v2
```

### Install Dependencies and Build
```bash
npm install
npm run build
```

### Start with PM2
```bash
pm2 start npm --name "diplens-frontend" -- start
pm2 save
pm2 startup
```
(Run the command output by `pm2 startup` to freeze the process list on reboot).

## 6. Nginx Configuration (Reverse Proxy)

Configure Nginx to route traffic:
- Root `/` -> Frontend (Port 3000)
- API `/api` -> Backend (Port 8000)

Create a new site config:
```bash
sudo nano /etc/nginx/sites-available/diplens
```

Add the configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com OR your-server-ip;

    # Frontend (Next.js)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend (FastAPI) - Assuming your API routes start with /api or you want to map a subpath
    # If your FastAPI routes are like /api/v1/..., this works.
    # If they are root-level (like /docs), you might need a subdomain (api.yourdomain.com) or specific location blocks.
    
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Proxy /docs and /openapi.json for Swagger UI if needed
    location /docs {
        proxy_pass http://127.0.0.1:8000;
    }
    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/diplens /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 7. SSL Setup (HTTPS)

If you have a domain, secure it with Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 8. Maintenance

- **Logs**:
  - Backend: `journalctl -u diplens-backend -f`
  - Frontend: `pm2 logs diplens-frontend`
  - Nginx: `/var/log/nginx/error.log`

- **Updates**:
  1. `git pull`
  2. Backend: `pip install -r requirements.txt` && `sudo systemctl restart diplens-backend`
  3. Frontend: `npm install` && `npm run build` && `pm2 restart diplens-frontend`
