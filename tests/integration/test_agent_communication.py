"""
Integration Tests for Agent Communication
==========================================

Tests for inter-agent communication, coordination, and data sharing.

Version: 1.0.0
Date: 2025-11-14
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime


# ============================================================================
# MOCK AGENT FRAMEWORK
# ============================================================================

class AgentMessage:
    """Message passed between agents"""
    def __init__(self, sender: str, recipient: str, message_type: str, payload: Dict[str, Any]):
        self.sender = sender
        self.recipient = recipient
        self.message_type = message_type
        self.payload = payload
        self.timestamp = datetime.now().isoformat()
        self.message_id = f"{sender}_{recipient}_{datetime.now().timestamp()}"


class MessageBus:
    """Simple message bus for agent communication"""
    def __init__(self):
        self.messages: List[AgentMessage] = []
        self.subscribers: Dict[str, List[callable]] = {}

    def publish(self, message: AgentMessage):
        """Publish message to bus"""
        self.messages.append(message)

        # Deliver to subscribers
        if message.recipient in self.subscribers:
            for handler in self.subscribers[message.recipient]:
                handler(message)

    def subscribe(self, agent_name: str, handler: callable):
        """Subscribe agent to messages"""
        if agent_name not in self.subscribers:
            self.subscribers[agent_name] = []
        self.subscribers[agent_name].append(handler)

    def get_messages(self, recipient: Optional[str] = None) -> List[AgentMessage]:
        """Get messages for recipient"""
        if recipient:
            return [m for m in self.messages if m.recipient == recipient]
        return self.messages


class BaseAgent:
    """Base agent class"""
    def __init__(self, name: str, message_bus: MessageBus):
        self.name = name
        self.message_bus = message_bus
        self.inbox: List[AgentMessage] = []
        message_bus.subscribe(name, self.receive_message)

    def send_message(self, recipient: str, message_type: str, payload: Dict[str, Any]):
        """Send message to another agent"""
        message = AgentMessage(self.name, recipient, message_type, payload)
        self.message_bus.publish(message)

    def receive_message(self, message: AgentMessage):
        """Receive message from bus"""
        self.inbox.append(message)

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process received message (to be overridden)"""
        return {"status": "processed"}


# ============================================================================
# MOCK AGENTS
# ============================================================================

class ScanProcessorAgent(BaseAgent):
    """Processes scan events"""
    async def process_scan(self, bag_tag: str, location: str) -> Dict[str, Any]:
        """Process scan and notify risk scorer"""
        scan_data = {
            "bag_tag": bag_tag,
            "location": location,
            "timestamp": datetime.now().isoformat()
        }

        # Notify risk scorer
        self.send_message("risk_scorer", "SCAN_EVENT", scan_data)

        return {"status": "scan_processed", "data": scan_data}


class RiskScorerAgent(BaseAgent):
    """Scores risk based on scan data"""
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process scan event and calculate risk"""
        if message.message_type == "SCAN_EVENT":
            bag_tag = message.payload.get("bag_tag")
            risk_score = 0.65  # Mock risk score

            # Notify case manager if high risk
            if risk_score > 0.6:
                self.send_message("case_manager", "HIGH_RISK_DETECTED", {
                    "bag_tag": bag_tag,
                    "risk_score": risk_score,
                    "factors": ["tight_connection"]
                })

            return {"status": "risk_assessed", "risk_score": risk_score}

        return {"status": "unknown_message_type"}


class CaseManagerAgent(BaseAgent):
    """Manages exception cases"""
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process high risk alerts"""
        if message.message_type == "HIGH_RISK_DETECTED":
            bag_tag = message.payload.get("bag_tag")
            risk_score = message.payload.get("risk_score")

            # Create case
            case_id = f"CASE_{bag_tag}"

            # Notify passenger comms
            self.send_message("passenger_comms", "CASE_CREATED", {
                "case_id": case_id,
                "bag_tag": bag_tag,
                "risk_score": risk_score
            })

            # Notify WorldTracer handler
            self.send_message("worldtracer_handler", "CREATE_PIR", {
                "case_id": case_id,
                "bag_tag": bag_tag
            })

            return {"status": "case_created", "case_id": case_id}

        return {"status": "unknown_message_type"}


class WorldTracerAgent(BaseAgent):
    """Handles WorldTracer integration"""
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process PIR creation requests"""
        if message.message_type == "CREATE_PIR":
            bag_tag = message.payload.get("bag_tag")
            pir_number = f"SFOUA{bag_tag[-6:]}"

            # Notify case manager of PIR creation
            self.send_message("case_manager", "PIR_CREATED", {
                "bag_tag": bag_tag,
                "pir_number": pir_number,
                "status": "CREATED"
            })

            return {"status": "pir_created", "pir_number": pir_number}

        return {"status": "unknown_message_type"}


class PassengerCommsAgent(BaseAgent):
    """Handles passenger notifications"""
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process notification requests"""
        if message.message_type == "CASE_CREATED":
            bag_tag = message.payload.get("bag_tag")

            # Send notification (mock)
            notification_id = f"NOTIF_{bag_tag}"

            return {
                "status": "notification_sent",
                "notification_id": notification_id,
                "channel": "SMS"
            }

        return {"status": "unknown_message_type"}


class CourierDispatchAgent(BaseAgent):
    """Handles courier logistics"""
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process delivery requests"""
        if message.message_type == "REQUEST_DELIVERY":
            bag_tag = message.payload.get("bag_tag")
            address = message.payload.get("address")

            booking_id = f"BOOKING_{bag_tag}"

            # Notify case manager
            self.send_message("case_manager", "DELIVERY_BOOKED", {
                "bag_tag": bag_tag,
                "booking_id": booking_id,
                "carrier": "FedEx"
            })

            return {
                "status": "delivery_booked",
                "booking_id": booking_id
            }

        return {"status": "unknown_message_type"}


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestBasicCommunication:
    """Test basic agent-to-agent communication"""

    @pytest.mark.asyncio
    async def test_message_sending(self):
        """Test agent can send message to another agent"""
        bus = MessageBus()
        agent1 = BaseAgent("agent1", bus)
        agent2 = BaseAgent("agent2", bus)

        # Send message
        agent1.send_message("agent2", "TEST", {"data": "hello"})

        # Wait for delivery
        await asyncio.sleep(0.1)

        # Check agent2 received message
        assert len(agent2.inbox) == 1
        assert agent2.inbox[0].sender == "agent1"
        assert agent2.inbox[0].message_type == "TEST"
        assert agent2.inbox[0].payload["data"] == "hello"

    @pytest.mark.asyncio
    async def test_bidirectional_communication(self):
        """Test agents can communicate in both directions"""
        bus = MessageBus()
        agent1 = BaseAgent("agent1", bus)
        agent2 = BaseAgent("agent2", bus)

        # Agent1 sends to Agent2
        agent1.send_message("agent2", "PING", {})
        await asyncio.sleep(0.1)

        # Agent2 replies to Agent1
        agent2.send_message("agent1", "PONG", {})
        await asyncio.sleep(0.1)

        # Check both received messages
        assert len(agent1.inbox) == 1
        assert agent1.inbox[0].message_type == "PONG"

        assert len(agent2.inbox) == 1
        assert agent2.inbox[0].message_type == "PING"

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_agents(self):
        """Test sending messages to multiple agents"""
        bus = MessageBus()
        sender = BaseAgent("sender", bus)
        agent1 = BaseAgent("agent1", bus)
        agent2 = BaseAgent("agent2", bus)
        agent3 = BaseAgent("agent3", bus)

        # Send to each agent
        for agent_name in ["agent1", "agent2", "agent3"]:
            sender.send_message(agent_name, "BROADCAST", {"data": "hello all"})

        await asyncio.sleep(0.1)

        # Check all received message
        assert len(agent1.inbox) == 1
        assert len(agent2.inbox) == 1
        assert len(agent3.inbox) == 1


class TestWorkflowCoordination:
    """Test multi-agent workflow coordination"""

    @pytest.mark.asyncio
    async def test_scan_to_risk_assessment_flow(self):
        """Test scan processor -> risk scorer flow"""
        bus = MessageBus()
        scan_processor = ScanProcessorAgent("scan_processor", bus)
        risk_scorer = RiskScorerAgent("risk_scorer", bus)

        # Process scan
        await scan_processor.process_scan("0016123456789", "MAKEUP_01")

        await asyncio.sleep(0.1)

        # Check risk scorer received scan event
        assert len(risk_scorer.inbox) == 1
        assert risk_scorer.inbox[0].message_type == "SCAN_EVENT"
        assert risk_scorer.inbox[0].payload["bag_tag"] == "0016123456789"

    @pytest.mark.asyncio
    async def test_high_risk_exception_flow(self):
        """Test high risk detection -> case creation flow"""
        bus = MessageBus()
        risk_scorer = RiskScorerAgent("risk_scorer", bus)
        case_manager = CaseManagerAgent("case_manager", bus)
        passenger_comms = PassengerCommsAgent("passenger_comms", bus)
        worldtracer = WorldTracerAgent("worldtracer_handler", bus)

        # Trigger risk assessment
        scan_message = AgentMessage(
            "scan_processor", "risk_scorer", "SCAN_EVENT",
            {"bag_tag": "0016123456789", "location": "MAKEUP_01"}
        )

        await risk_scorer.process_message(scan_message)
        await asyncio.sleep(0.1)

        # Check case manager received high risk alert
        assert len(case_manager.inbox) == 1
        assert case_manager.inbox[0].message_type == "HIGH_RISK_DETECTED"

        # Process case creation
        await case_manager.process_message(case_manager.inbox[0])
        await asyncio.sleep(0.1)

        # Check passenger comms and worldtracer received notifications
        assert len(passenger_comms.inbox) == 1
        assert passenger_comms.inbox[0].message_type == "CASE_CREATED"

        assert len(worldtracer.inbox) == 1
        assert worldtracer.inbox[0].message_type == "CREATE_PIR"

    @pytest.mark.asyncio
    async def test_complete_exception_workflow(self):
        """Test complete exception handling workflow"""
        bus = MessageBus()

        # Create all agents
        scan_processor = ScanProcessorAgent("scan_processor", bus)
        risk_scorer = RiskScorerAgent("risk_scorer", bus)
        case_manager = CaseManagerAgent("case_manager", bus)
        passenger_comms = PassengerCommsAgent("passenger_comms", bus)
        worldtracer = WorldTracerAgent("worldtracer_handler", bus)

        # 1. Scan event
        await scan_processor.process_scan("0016123456789", "MAKEUP_01")
        await asyncio.sleep(0.1)

        # 2. Risk assessment
        scan_msg = risk_scorer.inbox[0]
        await risk_scorer.process_message(scan_msg)
        await asyncio.sleep(0.1)

        # 3. Case creation
        risk_msg = case_manager.inbox[0]
        await case_manager.process_message(risk_msg)
        await asyncio.sleep(0.1)

        # 4. PIR creation
        pir_msg = worldtracer.inbox[0]
        await worldtracer.process_message(pir_msg)
        await asyncio.sleep(0.1)

        # 5. Passenger notification
        notif_msg = passenger_comms.inbox[0]
        result = await passenger_comms.process_message(notif_msg)

        # Verify complete flow
        assert result["status"] == "notification_sent"
        assert len(bus.messages) >= 5  # Multiple messages exchanged


class TestParallelCoordination:
    """Test parallel agent coordination"""

    @pytest.mark.asyncio
    async def test_parallel_case_creation_and_notification(self):
        """Test case creation and notification happen in parallel"""
        bus = MessageBus()
        case_manager = CaseManagerAgent("case_manager", bus)
        passenger_comms = PassengerCommsAgent("passenger_comms", bus)
        worldtracer = WorldTracerAgent("worldtracer_handler", bus)

        # Simulate high risk detection
        risk_message = AgentMessage(
            "risk_scorer", "case_manager", "HIGH_RISK_DETECTED",
            {"bag_tag": "0016123456789", "risk_score": 0.85}
        )

        # Case manager sends to both agents in parallel
        start_time = datetime.now()
        await case_manager.process_message(risk_message)
        await asyncio.sleep(0.1)

        # Both agents should receive messages
        assert len(passenger_comms.inbox) == 1
        assert len(worldtracer.inbox) == 1

        # Messages should be sent roughly at same time (parallel)
        assert passenger_comms.inbox[0].timestamp <= worldtracer.inbox[0].timestamp

    @pytest.mark.asyncio
    async def test_multiple_bags_concurrent_processing(self):
        """Test processing multiple bags concurrently"""
        bus = MessageBus()
        scan_processor = ScanProcessorAgent("scan_processor", bus)
        risk_scorer = RiskScorerAgent("risk_scorer", bus)

        # Process 5 bags concurrently
        bags = [f"001612345678{i}" for i in range(5)]

        tasks = [
            scan_processor.process_scan(bag_tag, "MAKEUP_01")
            for bag_tag in bags
        ]

        await asyncio.gather(*tasks)
        await asyncio.sleep(0.1)

        # Risk scorer should have received all scan events
        assert len(risk_scorer.inbox) == 5

        # All bags should be represented
        received_bags = {msg.payload["bag_tag"] for msg in risk_scorer.inbox}
        assert received_bags == set(bags)


class TestErrorHandling:
    """Test error handling in agent communication"""

    @pytest.mark.asyncio
    async def test_unknown_message_type(self):
        """Test handling of unknown message types"""
        bus = MessageBus()
        agent = RiskScorerAgent("risk_scorer", bus)

        # Send unknown message type
        unknown_message = AgentMessage(
            "sender", "risk_scorer", "UNKNOWN_TYPE",
            {"data": "test"}
        )

        result = await agent.process_message(unknown_message)

        assert result["status"] == "unknown_message_type"

    @pytest.mark.asyncio
    async def test_missing_recipient(self):
        """Test sending to non-existent agent"""
        bus = MessageBus()
        sender = BaseAgent("sender", bus)

        # Send to non-existent agent
        sender.send_message("non_existent", "TEST", {})

        # Should not raise exception
        # Message just won't be delivered
        messages = bus.get_messages("non_existent")
        assert len(messages) == 1  # Message is in bus but not delivered


class TestMessageOrdering:
    """Test message ordering and delivery guarantees"""

    @pytest.mark.asyncio
    async def test_message_order_preservation(self):
        """Test messages are delivered in order"""
        bus = MessageBus()
        sender = BaseAgent("sender", bus)
        receiver = BaseAgent("receiver", bus)

        # Send multiple messages in sequence
        for i in range(10):
            sender.send_message("receiver", "TEST", {"sequence": i})

        await asyncio.sleep(0.1)

        # Check messages received in order
        assert len(receiver.inbox) == 10
        for i, message in enumerate(receiver.inbox):
            assert message.payload["sequence"] == i

    @pytest.mark.asyncio
    async def test_message_timestamps(self):
        """Test messages have timestamps"""
        bus = MessageBus()
        sender = BaseAgent("sender", bus)
        receiver = BaseAgent("receiver", bus)

        sender.send_message("receiver", "TEST", {})
        await asyncio.sleep(0.1)

        assert len(receiver.inbox) == 1
        assert receiver.inbox[0].timestamp is not None
        assert isinstance(receiver.inbox[0].timestamp, str)


class TestDataSharing:
    """Test data sharing between agents"""

    @pytest.mark.asyncio
    async def test_risk_data_propagation(self):
        """Test risk data propagates correctly"""
        bus = MessageBus()
        risk_scorer = RiskScorerAgent("risk_scorer", bus)
        case_manager = CaseManagerAgent("case_manager", bus)

        # Trigger risk assessment
        scan_message = AgentMessage(
            "scan_processor", "risk_scorer", "SCAN_EVENT",
            {"bag_tag": "0016123456789", "location": "MAKEUP_01"}
        )

        await risk_scorer.process_message(scan_message)
        await asyncio.sleep(0.1)

        # Case manager should receive risk data
        assert len(case_manager.inbox) == 1
        risk_message = case_manager.inbox[0]
        assert "risk_score" in risk_message.payload
        assert "bag_tag" in risk_message.payload
        assert risk_message.payload["bag_tag"] == "0016123456789"

    @pytest.mark.asyncio
    async def test_pir_data_feedback_loop(self):
        """Test PIR creation feedback to case manager"""
        bus = MessageBus()
        case_manager = CaseManagerAgent("case_manager", bus)
        worldtracer = WorldTracerAgent("worldtracer_handler", bus)

        # Request PIR creation
        case_manager.send_message("worldtracer_handler", "CREATE_PIR", {
            "case_id": "CASE_001",
            "bag_tag": "0016123456789"
        })

        await asyncio.sleep(0.1)

        # WorldTracer processes request
        pir_msg = worldtracer.inbox[0]
        await worldtracer.process_message(pir_msg)
        await asyncio.sleep(0.1)

        # Case manager should receive PIR confirmation
        pir_created_messages = [m for m in case_manager.inbox if m.message_type == "PIR_CREATED"]
        assert len(pir_created_messages) == 1
        assert "pir_number" in pir_created_messages[0].payload


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
