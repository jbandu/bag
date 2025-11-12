# 🚂 Railway Deployment Guide

## Why Railway?

Railway is perfect for your AI-powered baggage platform because:
- ✅ **Full Python Support** - No serverless limitations
- ✅ **Built-in Databases** - PostgreSQL, Redis, MongoDB
- ✅ **Great for AI/ML** - LangChain, LangGraph, Claude work perfectly
- ✅ **Auto-scaling** - Handles traffic spikes
- ✅ **Simple Deployment** - Push to GitHub and it deploys
- ✅ **$5/month free tier** - Great for getting started

---

## 🚀 Quick Deployment (Web UI - Easiest!)

### Option 1: Deploy from GitHub (Recommended)

1. **Create Railway Account**
   - Go to https://railway.app
   - Sign up with GitHub
   - You'll get $5 free credit/month

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your GitHub account
   - Select repository: `jbandu/bag`
   - Railway auto-detects Python and uses our configuration files

3. **Add Environment Variables**
   Click "Variables" and add these from your `.env` file:
   ```
   ANTHROPIC_API_KEY=<your-anthropic-api-key-from-.env>
   NEON_DATABASE_URL=<your-neon-database-url-from-.env>
   MODEL_NAME=claude-sonnet-4-20250514
   MODEL_TEMPERATURE=0.1
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   HIGH_RISK_THRESHOLD=0.7
   CRITICAL_RISK_THRESHOLD=0.9
   AUTO_DISPATCH_THRESHOLD=0.8
   ```

   **Important:** Copy the actual values from your local `.env` file!

4. **Deploy!**
   - Railway automatically builds and deploys
   - You'll get a URL like: `https://bag-production.up.railway.app`
   - First deployment takes 2-3 minutes

5. **Test Your API**
   ```bash
   curl https://YOUR-RAILWAY-URL.railway.app/
   curl https://YOUR-RAILWAY-URL.railway.app/health
   curl https://YOUR-RAILWAY-URL.railway.app/docs
   ```

---

## 🛠️ Option 2: Deploy from CLI

### Step 1: Login to Railway

```bash
railway login
```

This opens your browser to authenticate.

### Step 2: Initialize Project

```bash
# In your project directory
railway init
```

Choose:
- "Create a new project" or select existing
- Give it a name: "baggage-operations"

### Step 3: Link to GitHub (Optional)

```bash
railway link
```

### Step 4: Add Environment Variables

**Load from your .env file:**

```bash
# Option 1: Load all variables from .env file
railway variables set --from-env-file .env

# Option 2: Set individual variables (replace with your actual values from .env)
railway variables set ANTHROPIC_API_KEY="<your-api-key-from-.env>"
railway variables set NEON_DATABASE_URL="<your-db-url-from-.env>"
railway variables set ENVIRONMENT="production"
railway variables set LOG_LEVEL="INFO"
railway variables set MODEL_NAME="claude-sonnet-4-20250514"
railway variables set MODEL_TEMPERATURE="0.1"
railway variables set HIGH_RISK_THRESHOLD="0.7"
railway variables set CRITICAL_RISK_THRESHOLD="0.9"
railway variables set AUTO_DISPATCH_THRESHOLD="0.8"
```

**Note:** Copy your actual credentials from the local `.env` file!

### Step 5: Deploy

```bash
railway up
```

Or link to GitHub for auto-deploys:
```bash
railway link
```

### Step 6: View Logs

```bash
railway logs
```

### Step 7: Open Your App

```bash
railway open
```

---

## 📊 Adding Railway PostgreSQL (Optional)

If you want to use Railway's built-in PostgreSQL instead of Neon:

1. **In Railway Dashboard:**
   - Click "New" → "Database" → "Add PostgreSQL"
   - Railway creates it and adds `DATABASE_URL` automatically

2. **Update your code to use DATABASE_URL:**
   ```python
   # In config/settings.py
   database_url: str = Field(default="", env="DATABASE_URL")
   ```

3. **Migrate your data:**
   ```bash
   # Run init script
   railway run python init_database.py

   # Populate data
   railway run python populate_neon_data.py
   ```

---

## 🎯 Adding Railway Redis (Optional)

For high-performance caching:

1. **In Railway Dashboard:**
   - Click "New" → "Database" → "Add Redis"
   - Railway adds `REDIS_URL` automatically

2. **Your code already supports it!**
   It will use the `REDIS_URL` environment variable

---

## 🔍 Monitoring Your Deployment

### View Logs
```bash
railway logs --follow
```

### Check Status
```bash
railway status
```

### View Environment Variables
```bash
railway variables
```

### Open Railway Dashboard
```bash
railway open
```

---

## 🚀 Auto-Deployments from GitHub

**Railway automatically deploys when you push to GitHub!**

1. **In Railway Dashboard:**
   - Go to Settings → GitHub
   - Select your repo: `jbandu/bag`
   - Choose branch: `main`

2. **Every git push triggers deployment:**
   ```bash
   git add .
   git commit -m "Update API"
   git push
   # Railway automatically deploys! 🚀
   ```

3. **View deployment status:**
   - Railway dashboard shows build progress
   - Get notifications on success/failure

---

## 📝 Files Created for Railway

- **`Procfile`** - Tells Railway how to start your app
- **`railway.json`** - Railway configuration
- **`runtime.txt`** - Python version specification
- **`.railwayignore`** - Files to exclude from deployment

---

## 🎯 Testing Your Railway Deployment

Once deployed, test all endpoints:

```bash
# Replace YOUR_URL with your Railway URL
export RAILWAY_URL="https://your-app.up.railway.app"

# Test root
curl $RAILWAY_URL/

# Test health
curl $RAILWAY_URL/health

# Test bag lookup
curl $RAILWAY_URL/api/v1/bag/CM12345

# Test scan event
curl -X POST $RAILWAY_URL/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{
    "raw_scan": "Bag Tag: CM99999\nLocation: PTY",
    "source": "BHS"
  }'

# View API docs
open $RAILWAY_URL/docs
```

---

## 💰 Pricing

**Free Tier:**
- $5 credit/month (enough for hobby projects)
- Sleeps after inactivity (wakes up on request)

**Hobby Plan ($5/month):**
- $5 credit/month included
- Pay-as-you-go beyond that
- No sleep mode

**Pro Plan ($20/month):**
- $20 credit/month included
- Priority support
- Better performance

Your app will likely stay within the free tier for development!

---

## 🐛 Troubleshooting

### Build Fails

```bash
# Check build logs
railway logs --deployment

# Common issues:
# - Missing dependency in requirements.txt
# - Python version mismatch
```

### App Crashes

```bash
# View runtime logs
railway logs --follow

# Common issues:
# - Missing environment variable
# - Database connection error
# - Port binding issue (use $PORT)
```

### Database Connection Issues

```bash
# Test database connectivity
railway run python -c "from utils.database import neo4j_db; print('Connected!')"

# Check environment variables
railway variables
```

---

## 🎓 Learning Resources

- **Railway Docs:** https://docs.railway.app
- **Discord Community:** https://discord.gg/railway
- **Example Projects:** https://railway.app/templates

---

## 🚀 Next Steps After Deployment

1. **Add Custom Domain** (optional)
   - Railway Settings → Domains
   - Add your domain and configure DNS

2. **Set Up Monitoring**
   - Railway provides built-in metrics
   - View CPU, memory, request counts

3. **Configure Auto-scaling**
   - Railway automatically scales based on load
   - Configure in Settings → Scaling

4. **Add Background Workers** (optional)
   - Create another service for background jobs
   - Use the same codebase

---

## ✅ Your Deployment Checklist

- [ ] Railway account created
- [ ] Project deployed from GitHub
- [ ] Environment variables added
- [ ] API health check passing
- [ ] API docs accessible at /docs
- [ ] Sample data populated (optional)
- [ ] Custom domain configured (optional)
- [ ] Auto-deployments working

---

**You're ready to deploy! 🚀**

The easiest path is Option 1 (Web UI + GitHub). Just push your code and Railway handles the rest!
