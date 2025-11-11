# Deploying to Vercel

This guide explains how to deploy the Baggage Operations API to Vercel.

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Vercel CLI** (optional but recommended):
   ```bash
   npm install -g vercel
   ```

3. **Cloud Services** (Required for Vercel deployment):
   - **Neo4j Aura** (free tier): https://neo4j.com/cloud/aura/
     - Create a free AuraDB instance
     - Note the connection URI, username, and password

   - **Upstash Redis** (free tier): https://upstash.com
     - Create a free Redis database
     - Get the Redis URL

   - **Neon PostgreSQL** (you already have this!):
     - Your existing Neon database will work

## Deployment Steps

### 1. Install Vercel CLI (if not already installed)

```bash
npm install -g vercel
```

### 2. Login to Vercel

```bash
vercel login
```

### 3. Set Environment Variables

Before deploying, you need to set up environment variables in Vercel. You can do this in two ways:

**Option A: Via Vercel Dashboard**
1. Go to your project settings on vercel.com
2. Navigate to "Environment Variables"
3. Add the following variables:

```
ANTHROPIC_API_KEY=your_anthropic_key
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
REDIS_URL=redis://default:xxx@xxx.upstash.io:6379
SUPABASE_URL=https://placeholder.supabase.co
SUPABASE_KEY=placeholder
SUPABASE_SERVICE_KEY=placeholder
WORLDTRACER_API_URL=https://worldtracer-api.example.com
WORLDTRACER_API_KEY=placeholder
SITA_TYPE_B_ENDPOINT=https://sita-gateway.example.com
```

**Option B: Via CLI**

```bash
vercel env add ANTHROPIC_API_KEY
vercel env add NEO4J_URI
vercel env add NEO4J_USER
vercel env add NEO4J_PASSWORD
vercel env add REDIS_URL
# ... add other variables
```

### 4. Deploy to Vercel

From the project root directory:

```bash
vercel
```

For production deployment:

```bash
vercel --prod
```

### 5. Initialize Your Cloud Databases

After deployment, you'll need to initialize your Neo4j Aura database. Run this script locally (pointing to your Aura instance):

```bash
# Update .env with Neo4j Aura credentials first
python3 init_neo4j.py
```

## What Gets Deployed

Vercel will deploy:
- ✅ The FastAPI API server as serverless functions
- ✅ All 8 AI agents
- ✅ The orchestrator
- ✅ All utilities and models

What **DOESN'T** get deployed to Vercel:
- ❌ Streamlit Dashboard (deploy to Streamlit Cloud instead)
- ❌ Docker containers
- ❌ Local Neo4j/Redis (use cloud services)

## Streamlit Dashboard Deployment

The Streamlit dashboard should be deployed separately to **Streamlit Cloud**:

1. Go to https://streamlit.io/cloud
2. Sign in with GitHub
3. Deploy the `dashboard/app.py` file
4. Set the API URL to your Vercel deployment URL

## Architecture After Deployment

```
┌─────────────────────────┐
│   Streamlit Cloud       │
│   (Dashboard UI)        │
│   Port: 443 (HTTPS)     │
└───────────┬─────────────┘
            │
            ↓
┌─────────────────────────┐
│   Vercel Serverless     │
│   (FastAPI API)         │
│   https://your-app.     │
│   vercel.app            │
└───────────┬─────────────┘
            │
    ┌───────┴────────┬─────────────┬──────────────┐
    ↓                ↓             ↓              ↓
┌─────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐
│ Neo4j   │  │ Upstash  │  │   Neon     │  │ Anthropic│
│  Aura   │  │  Redis   │  │ PostgreSQL │  │   API    │
│ (Graph) │  │ (Cache)  │  │ (Optional) │  │ (Claude) │
└─────────┘  └──────────┘  └────────────┘  └──────────┘
```

## Testing Your Deployment

After deployment, test your API:

```bash
# Replace with your Vercel URL
curl https://your-app.vercel.app/health

# Test the API docs
open https://your-app.vercel.app/docs
```

## Important Notes

1. **Cold Starts**: Serverless functions on Vercel have cold starts (1-3 seconds). The first request after inactivity will be slower.

2. **Execution Time Limits**:
   - Free tier: 10 seconds
   - Hobby: 10 seconds
   - Pro: 60 seconds

   Make sure your agent processing completes within these limits.

3. **Database Connections**: Use connection pooling for Neo4j and Redis to avoid connection limits.

4. **Costs**:
   - Vercel: Free tier should be sufficient for development
   - Neo4j Aura: Free tier (up to 200k nodes)
   - Upstash Redis: Free tier (10k commands/day)
   - Neon: Free tier (0.5GB storage)
   - Anthropic: Pay per use

## Troubleshooting

**Issue**: Function timeout
**Solution**: Optimize agent processing or upgrade to Pro plan

**Issue**: Database connection errors
**Solution**: Check firewall settings and allowlist Vercel IPs

**Issue**: Import errors
**Solution**: Ensure all dependencies are in requirements.txt

## Local Development vs Production

| Feature | Local | Vercel |
|---------|-------|--------|
| API Server | uvicorn | Vercel serverless |
| Dashboard | localhost:8501 | Streamlit Cloud |
| Neo4j | Docker | Neo4j Aura |
| Redis | Docker | Upstash |
| PostgreSQL | Neon | Neon |

## Support

For issues:
- Vercel Docs: https://vercel.com/docs
- Neo4j Aura: https://neo4j.com/docs/aura/
- Upstash: https://docs.upstash.com/

## Next Steps

1. Deploy to Vercel
2. Set up cloud databases
3. Configure environment variables
4. Deploy dashboard to Streamlit Cloud
5. Test end-to-end functionality
