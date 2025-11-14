"""
Working Memory Layer
====================

Layer 1: Short-term working memory using Redis.

Stores:
- Current bags being processed
- Active workflows in progress
- Recent decisions (last hour)
- Cache of frequent queries
- Temporary context for agents

Fast access (< 1ms), volatile, auto-expiring.

Version: 1.0.0
Date: 2025-11-14
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
from loguru import logger

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis not available - using in-memory fallback")
    REDIS_AVAILABLE = False


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class ActiveWorkflow:
    """Currently executing workflow"""
    workflow_id: str
    workflow_type: str
    bag_tag: str
    status: str
    started_at: str
    current_step: str
    progress_pct: float
    agent_assignments: Dict[str, str]


@dataclass
class RecentDecision:
    """Recent decision made by an agent"""
    decision_id: str
    agent_name: str
    bag_tag: str
    decision_type: str
    decision: str
    reasoning: str
    confidence: float
    timestamp: str
    context: Dict[str, Any]


@dataclass
class BagProcessingState:
    """Current processing state of a bag"""
    bag_tag: str
    current_status: str
    current_location: str
    risk_score: float
    assigned_agents: List[str]
    workflow_id: Optional[str]
    last_updated: str
    next_action: Optional[str]


# ============================================================================
# WORKING MEMORY
# ============================================================================

class WorkingMemory:
    """
    Fast, volatile working memory using Redis.

    Provides immediate access to:
    - Current processing state
    - Active workflows
    - Recent decisions
    - Cached queries
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize working memory"""
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None

        # In-memory fallback if Redis not available
        self.fallback_store: Dict[str, Any] = {}

        logger.info("WorkingMemory initialized")

    async def connect(self):
        """Connect to Redis"""
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True
                )
                await self.redis_client.ping()
                logger.info("Connected to Redis")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}, using fallback")
                self.redis_client = None
        else:
            logger.info("Using in-memory fallback for working memory")

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")

    # ========================================================================
    # BAG PROCESSING STATE
    # ========================================================================

    async def set_bag_state(
        self,
        bag_tag: str,
        state: BagProcessingState,
        ttl_seconds: int = 3600  # 1 hour default
    ):
        """
        Store current bag processing state.

        Args:
            bag_tag: Bag tag number
            state: Processing state
            ttl_seconds: Time to live in seconds
        """
        key = f"bag:state:{bag_tag}"
        value = json.dumps(asdict(state))

        if self.redis_client:
            await self.redis_client.setex(key, ttl_seconds, value)
        else:
            self.fallback_store[key] = {
                "value": value,
                "expires_at": datetime.now() + timedelta(seconds=ttl_seconds)
            }

        logger.debug(f"Stored bag state for {bag_tag}")

    async def get_bag_state(self, bag_tag: str) -> Optional[BagProcessingState]:
        """Get current bag processing state"""
        key = f"bag:state:{bag_tag}"

        if self.redis_client:
            value = await self.redis_client.get(key)
            if value:
                data = json.loads(value)
                return BagProcessingState(**data)
        else:
            entry = self.fallback_store.get(key)
            if entry and entry["expires_at"] > datetime.now():
                data = json.loads(entry["value"])
                return BagProcessingState(**data)

        return None

    async def delete_bag_state(self, bag_tag: str):
        """Remove bag from working memory"""
        key = f"bag:state:{bag_tag}"

        if self.redis_client:
            await self.redis_client.delete(key)
        else:
            self.fallback_store.pop(key, None)

        logger.debug(f"Deleted bag state for {bag_tag}")

    async def get_all_active_bags(self) -> List[str]:
        """Get list of all bags currently in working memory"""
        pattern = "bag:state:*"

        if self.redis_client:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                bag_tag = key.split(":")[-1]
                keys.append(bag_tag)
            return keys
        else:
            now = datetime.now()
            keys = []
            for key, entry in self.fallback_store.items():
                if key.startswith("bag:state:") and entry["expires_at"] > now:
                    bag_tag = key.split(":")[-1]
                    keys.append(bag_tag)
            return keys

    # ========================================================================
    # ACTIVE WORKFLOWS
    # ========================================================================

    async def set_active_workflow(
        self,
        workflow_id: str,
        workflow: ActiveWorkflow,
        ttl_seconds: int = 7200  # 2 hours
    ):
        """Store active workflow state"""
        key = f"workflow:active:{workflow_id}"
        value = json.dumps(asdict(workflow))

        if self.redis_client:
            await self.redis_client.setex(key, ttl_seconds, value)
        else:
            self.fallback_store[key] = {
                "value": value,
                "expires_at": datetime.now() + timedelta(seconds=ttl_seconds)
            }

        logger.debug(f"Stored active workflow {workflow_id}")

    async def get_active_workflow(self, workflow_id: str) -> Optional[ActiveWorkflow]:
        """Get active workflow state"""
        key = f"workflow:active:{workflow_id}"

        if self.redis_client:
            value = await self.redis_client.get(key)
            if value:
                data = json.loads(value)
                return ActiveWorkflow(**data)
        else:
            entry = self.fallback_store.get(key)
            if entry and entry["expires_at"] > datetime.now():
                data = json.loads(entry["value"])
                return ActiveWorkflow(**data)

        return None

    async def get_workflows_by_bag(self, bag_tag: str) -> List[ActiveWorkflow]:
        """Get all active workflows for a bag"""
        pattern = "workflow:active:*"
        workflows = []

        if self.redis_client:
            async for key in self.redis_client.scan_iter(match=pattern):
                value = await self.redis_client.get(key)
                if value:
                    data = json.loads(value)
                    if data.get("bag_tag") == bag_tag:
                        workflows.append(ActiveWorkflow(**data))
        else:
            now = datetime.now()
            for key, entry in self.fallback_store.items():
                if key.startswith("workflow:active:") and entry["expires_at"] > now:
                    data = json.loads(entry["value"])
                    if data.get("bag_tag") == bag_tag:
                        workflows.append(ActiveWorkflow(**data))

        return workflows

    # ========================================================================
    # RECENT DECISIONS
    # ========================================================================

    async def store_decision(
        self,
        decision: RecentDecision,
        ttl_seconds: int = 3600  # 1 hour
    ):
        """Store a recent decision"""
        key = f"decision:{decision.agent_name}:{decision.decision_id}"
        value = json.dumps(asdict(decision))

        if self.redis_client:
            await self.redis_client.setex(key, ttl_seconds, value)
        else:
            self.fallback_store[key] = {
                "value": value,
                "expires_at": datetime.now() + timedelta(seconds=ttl_seconds)
            }

        # Also add to agent's decision list
        list_key = f"decisions:agent:{decision.agent_name}"
        if self.redis_client:
            await self.redis_client.lpush(list_key, decision.decision_id)
            await self.redis_client.ltrim(list_key, 0, 99)  # Keep last 100
            await self.redis_client.expire(list_key, ttl_seconds)

        logger.debug(f"Stored decision {decision.decision_id} for {decision.agent_name}")

    async def get_recent_decisions(
        self,
        agent_name: Optional[str] = None,
        bag_tag: Optional[str] = None,
        limit: int = 10
    ) -> List[RecentDecision]:
        """Get recent decisions by agent or bag"""
        decisions = []

        if agent_name:
            # Get from agent's list
            list_key = f"decisions:agent:{agent_name}"

            if self.redis_client:
                decision_ids = await self.redis_client.lrange(list_key, 0, limit - 1)
                for decision_id in decision_ids:
                    key = f"decision:{agent_name}:{decision_id}"
                    value = await self.redis_client.get(key)
                    if value:
                        data = json.loads(value)
                        decisions.append(RecentDecision(**data))
        else:
            # Scan all decisions
            pattern = "decision:*"
            now = datetime.now()

            if self.redis_client:
                count = 0
                async for key in self.redis_client.scan_iter(match=pattern):
                    if count >= limit:
                        break
                    value = await self.redis_client.get(key)
                    if value:
                        data = json.loads(value)
                        if not bag_tag or data.get("bag_tag") == bag_tag:
                            decisions.append(RecentDecision(**data))
                            count += 1
            else:
                count = 0
                for key, entry in self.fallback_store.items():
                    if count >= limit:
                        break
                    if key.startswith("decision:") and entry["expires_at"] > now:
                        data = json.loads(entry["value"])
                        if not bag_tag or data.get("bag_tag") == bag_tag:
                            decisions.append(RecentDecision(**data))
                            count += 1

        return decisions

    # ========================================================================
    # QUERY CACHE
    # ========================================================================

    async def cache_query(
        self,
        query_key: str,
        result: Any,
        ttl_seconds: int = 300  # 5 minutes default
    ):
        """Cache a query result"""
        key = f"cache:query:{query_key}"
        value = json.dumps(result)

        if self.redis_client:
            await self.redis_client.setex(key, ttl_seconds, value)
        else:
            self.fallback_store[key] = {
                "value": value,
                "expires_at": datetime.now() + timedelta(seconds=ttl_seconds)
            }

        logger.debug(f"Cached query: {query_key}")

    async def get_cached_query(self, query_key: str) -> Optional[Any]:
        """Get cached query result"""
        key = f"cache:query:{query_key}"

        if self.redis_client:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
        else:
            entry = self.fallback_store.get(key)
            if entry and entry["expires_at"] > datetime.now():
                return json.loads(entry["value"])

        return None

    async def invalidate_cache(self, pattern: str = "*"):
        """Invalidate cache entries matching pattern"""
        cache_pattern = f"cache:query:{pattern}"

        if self.redis_client:
            deleted = 0
            async for key in self.redis_client.scan_iter(match=cache_pattern):
                await self.redis_client.delete(key)
                deleted += 1
            logger.info(f"Invalidated {deleted} cache entries")
        else:
            deleted = 0
            keys_to_delete = [
                k for k in self.fallback_store.keys()
                if k.startswith("cache:query:")
            ]
            for key in keys_to_delete:
                del self.fallback_store[key]
                deleted += 1
            logger.info(f"Invalidated {deleted} cache entries")

    # ========================================================================
    # STATISTICS
    # ========================================================================

    async def get_stats(self) -> Dict[str, Any]:
        """Get working memory statistics"""
        stats = {
            "active_bags": len(await self.get_all_active_bags()),
            "using_redis": self.redis_client is not None,
            "fallback_keys": len(self.fallback_store) if not self.redis_client else 0
        }

        if self.redis_client:
            info = await self.redis_client.info("memory")
            stats["redis_memory_used_mb"] = info.get("used_memory", 0) / 1024 / 1024
            stats["redis_keys"] = await self.redis_client.dbsize()

        return stats
