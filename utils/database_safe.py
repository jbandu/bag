"""
Database connection utilities with graceful fallbacks for serverless
"""
from typing import Optional, Dict, Any, List
from loguru import logger
from config.settings import settings

# Initialize connections as None
neo4j_db = None
supabase_db = None
redis_cache = None

# Try to import and initialize connections
try:
    from neo4j import GraphDatabase
    from utils.database import Neo4jConnection
    neo4j_db = Neo4jConnection()
    logger.info("✓ Neo4j connected")
except Exception as e:
    logger.warning(f"Neo4j not available: {e}")
    neo4j_db = None

try:
    from supabase import create_client
    from utils.database import SupabaseConnection
    supabase_db = SupabaseConnection()
    logger.info("✓ Supabase connected")
except Exception as e:
    logger.warning(f"Supabase not available: {e}")
    supabase_db = None

try:
    from redis import Redis
    from utils.database import RedisCache
    redis_cache = RedisCache()
    logger.info("✓ Redis connected")
except Exception as e:
    logger.warning(f"Redis not available: {e}")
    redis_cache = None

def is_database_available() -> Dict[str, bool]:
    """Check which databases are available"""
    return {
        "neo4j": neo4j_db is not None,
        "supabase": supabase_db is not None,
        "redis": redis_cache is not None
    }
