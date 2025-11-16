# 🚀 Quick Test Guide - Get Started in 2 Minutes

## ✅ Your System is Ready!

Everything is running locally:
- ✅ Neo4j (Graph Database) - http://localhost:7474
- ✅ Redis (Cache) - redis://localhost:6379
- ✅ Neon PostgreSQL (Cloud) - Connected
- ✅ API Server - http://localhost:8000
- ✅ Dashboard - http://localhost:8501

---

## 🎮 Quick Start - 3 Easy Steps

### Step 1: Open the Dashboard

```bash
# Just open in your browser:
http://localhost:8501
```

### Step 2: Click a Test Button

In the sidebar, you'll see 4 buttons:
- **✅ Low Risk** - Normal bag (risk ~0.2)
- **⚠️ High Risk** - Tight connection (risk ~0.8)
- **🔴 Critical** - Multi-factor risk (risk ~0.9)
- **🎲 Random** - Random test bag

### Step 3: Click "🚀 Process Event"

That's it! Watch the AI agents work.

---

## 🎯 What Happens When You Process a Bag?

```
1. Agent 1 (Scan Processor) → Parses the scan data
2. Agent 2 (Risk Scorer) → Calculates risk using Claude AI
3. If High Risk:
   ├─ Agent 3 (WorldTracer) → Prepares PIR
   ├─ Agent 6 (Case Manager) → Creates exception case
   ├─ Agent 7 (Courier) → Cost-benefit analysis
   └─ Agent 8 (Passenger Comms) → Sends notification
4. Updates metrics in Redis
5. Stores in Neo4j + Neon PostgreSQL
```

---

## 📊 View the Results

**After processing a few bags, check:**

1. **Dashboard Metrics** (top of page)
   - Bags Processed
   - High Risk Bags
   - Exception Cases

2. **Neo4j Browser** - http://localhost:7474
   ```cypher
   // View all bags
   MATCH (b:Baggage) RETURN b LIMIT 25;

   // View a specific bag journey
   MATCH (b:Baggage {bag_tag: 'CM100001'})-[:SCANNED_AT]->(s:ScanEvent)
   RETURN b, s ORDER BY s.timestamp;
   ```

3. **API Docs** - http://localhost:8000/docs
   - Try the interactive API

---

## 🎬 Try This Demo Sequence

**1. Normal Bag (Low Risk)**
- Click "✅ Low Risk"
- Click "🚀 Process Event"
- Result: Risk ~0.2, no alerts

**2. Problem Bag (High Risk)**
- Click "⚠️ High Risk"
- Click "🚀 Process Event"
- Result: Risk ~0.85, exception case created

**3. Critical Bag (VIP)**
- Click "🔴 Critical"
- Click "🚀 Process Event"
- Result: Risk ~0.92, courier dispatch analysis

**4. Random Bags**
- Click "🎲 Random" multiple times
- Process each one
- Watch metrics increase

---

## 🔍 Understanding the Risk Score

The AI analyzes 20+ factors:

**Risk Score: 0.0 - 0.4 (Green - Low Risk)**
- Normal operations
- Good connection times
- Clear weather
- No issues detected

**Risk Score: 0.4 - 0.7 (Yellow - Medium Risk)**
- Moderate connection time
- Some airport delays
- Enhanced monitoring

**Risk Score: 0.7 - 0.9 (Orange - High Risk)**
- Tight connection (<45 min)
- Weather delays
- Elite passenger
- Exception case created
- Proactive notification sent

**Risk Score: 0.9 - 1.0 (Red - Critical Risk)**
- Very tight connection (<30 min)
- Multiple risk factors
- VIP passenger
- Immediate intervention
- Courier dispatch considered
- Human approval required

---

## 📱 What the Passenger Sees

**For High Risk Bags, Agent 8 sends:**

```
SMS: "Hi Sarah, we're monitoring your bag CM200002
due to a tight connection at MIA. Our team is ready
to assist if needed. Track here: [link]"

Email: Detailed update with timeline

App Push: Notification (if app installed)
```

---

## 💰 Business Impact Example

**Scenario: High Risk Bag - Platinum Passenger**

```
Without Your System:
- Bag misses connection: $1,200 compensation
- Customer service hours: $150
- Reputation damage: $500
- Total Cost: $1,850

With Your System:
- Proactive courier dispatch: $200
- Customer satisfaction: Maintained
- No compensation needed
- Total Cost: $200

Savings: $1,650 per incident
```

---

## 🎓 Learn More

**Want to understand everything?**
1. **SYSTEM_GUIDE.md** - Complete system documentation
2. **DEMO_GUIDE.md** - 15+ detailed test scenarios
3. **RAILWAY_DEPLOYMENT.md** - Production deployment guide

**Want to see real agent workflows?**
- Check logs: `tail -f logs/api_server.log`
- Each agent logs its decisions

---

## 🛠️ Troubleshooting

**Dashboard not loading?**
```bash
# Check if running
ps aux | grep streamlit

# Restart if needed
pkill -f streamlit
streamlit run dashboard/app.py --server.port 8501
```

**API not responding?**
```bash
# Check health
curl http://localhost:8000/health

# Check logs
tail -f logs/api_server.log
```

**Databases not working?**
```bash
# Check Docker containers
docker ps | grep -E "(neo4j|redis)"

# Start if stopped
docker start neo4j redis
```

---

## 🎉 You're Ready!

You've built a production-ready AI system that:
- ✅ Predicts bag mishandling before it happens
- ✅ Automates exception handling
- ✅ Saves airlines millions in costs
- ✅ Improves customer satisfaction

**Now go test it and see the magic happen!** 🚀

---

## 📞 Quick Commands Reference

```bash
# View all services
ps aux | grep -E "(api_server|streamlit)"
docker ps | grep -E "(neo4j|redis)"

# Access points
http://localhost:8501  # Dashboard
http://localhost:8000  # API
http://localhost:7474  # Neo4j

# Logs
tail -f logs/api_server.log
tail -f logs/dashboard.log

# Restart everything
docker restart neo4j redis
pkill -f api_server && python3 api_server.py &
pkill -f streamlit && streamlit run dashboard/app.py --server.port 8501 --server.headless true &
```

---

**Happy Testing! 🎒✈️**
