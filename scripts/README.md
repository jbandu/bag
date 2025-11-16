# Management Scripts

Convenient scripts to manage the baggage tracking application locally.

## Quick Reference

| Script | Description | Usage |
|--------|-------------|-------|
| **start.sh** | Start all services | `./scripts/start.sh` |
| **stop.sh** | Stop all services | `./scripts/stop.sh` |
| **restart.sh** | Restart all services | `./scripts/restart.sh` |
| **status.sh** | Check service status | `./scripts/status.sh` |
| **rebuild.sh** | Complete rebuild | `./scripts/rebuild.sh` |

## Usage

### Start Everything

```bash
./scripts/start.sh
```

**Starts:**
- Neo4j (Docker)
- Redis (Docker)
- API Server (Python)
- Streamlit Dashboard (Python)

### Stop Everything

```bash
./scripts/stop.sh
```

**Stops:**
- All Python processes
- All Docker containers

### Restart Everything

```bash
./scripts/restart.sh
```

Equivalent to running `stop.sh` then `start.sh`

### Check Status

```bash
./scripts/status.sh
```

**Shows:**
- ✅/❌ Status of each service
- Port availability
- Database health
- Process details

### Complete Rebuild

```bash
./scripts/rebuild.sh
```

**Performs:**
1. Stops all services
2. Cleans Python cache
3. Archives old logs
4. Reinstalls dependencies
5. Rebuilds Docker containers
6. Reinitializes databases
7. Starts all services

**Use when:**
- Updating dependencies
- Cleaning up issues
- Fresh start needed

## Examples

```bash
# Quick restart after code changes
./scripts/restart.sh

# Check what's running
./scripts/status.sh

# Clean slate
./scripts/rebuild.sh

# Just stop for the day
./scripts/stop.sh
```

## Logs

All logs are stored in `logs/`:
- `logs/api_server.log` - API server logs
- `logs/dashboard.log` - Dashboard logs
- `logs/archive/` - Archived logs

**View logs:**
```bash
# API logs
tail -f logs/api_server.log

# Dashboard logs
tail -f logs/dashboard.log

# Neo4j logs
docker logs neo4j -f

# Redis logs
docker logs redis -f
```

## Troubleshooting

### Services won't start

```bash
# Check what's running
./scripts/status.sh

# Check ports
netstat -tulpn | grep -E '(8000|8501|7474|7687|6379)'

# Full rebuild
./scripts/rebuild.sh
```

### Stale processes

```bash
# Force kill everything
pkill -9 -f api_server
pkill -9 -f streamlit
docker kill neo4j redis

# Start fresh
./scripts/start.sh
```

### Database issues

```bash
# Reinitialize databases
python3 init_database.py
python3 init_neo4j.py

# Or full rebuild
./scripts/rebuild.sh
```

## Requirements

- Python 3.11+
- Docker
- Virtual environment activated
- `.env` file configured

## Notes

- Scripts assume you're in the project root directory
- Virtual environment should be activated for `start.sh`
- `rebuild.sh` takes 2-3 minutes to complete
- Logs are rotated on rebuild
