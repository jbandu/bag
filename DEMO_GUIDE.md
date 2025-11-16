# 🎬 Agent Demo Guide - Test Scenarios

## 🎯 How to Demo Each Agent

This guide provides copy-paste test data to demonstrate each of the 8 agents in your system.

---

## 🚀 Getting Started

1. **Open Dashboard**: http://localhost:8501
2. **Find the sidebar**: "📥 Process Scan Event" section
3. **Copy-paste test data** from scenarios below
4. **Click "🚀 Process Event"**
5. **Watch the magic happen!**

---

## Agent 1: Scan Event Processor 📥

### Test 1: Normal Check-In Scan (Low Risk)

**Scenario:** Simple domestic bag check-in

```
Bag Tag: CM100001
Passenger: John Smith
PNR: ABC123
Location: PTY-T1-Checkin
Scan Type: check-in
Timestamp: 2024-11-15T08:00:00Z
Flight: CM101
Route: PTY-MIA
```

**Expected Result:**
- ✅ Scan processed successfully
- ✅ Digital twin created in Neo4j
- ✅ Risk score: ~0.15 (Low)
- ✅ No exception case created

---

### Test 2: Tight Connection (High Risk)

**Scenario:** International connection with minimal buffer time

```
Bag Tag: CM200002
Passenger: Sarah Johnson
PNR: XYZ789
Elite Status: Platinum
Location: PTY-T1-Checkin
Scan Type: check-in
Timestamp: 2024-11-15T08:30:00Z
Flight: CM101 PTY-MIA (arr 11:45)
Connecting Flight: CM205 MIA-JFK (dep 12:15)
Connection Time: 30 minutes
MCT Required: 45 minutes
Weather: Thunderstorms at MIA
```

**Expected Result:**
- ⚠️ Risk score: ~0.85 (High)
- 📦 Exception case created
- 📱 Proactive passenger notification
- 🎯 Enhanced monitoring enabled

---

### Test 3: Scan Gap Detection

**Scenario:** Bag checked in but missing sortation scan

**Step 1 - Check-in:**
```
Bag Tag: CM300003
Location: PTY-T1-Checkin
Scan Type: check-in
Timestamp: 2024-11-15T09:00:00Z
```

**Step 2 - Skip sortation, go straight to load:**
```
Bag Tag: CM300003
Location: PTY-Gate-12
Scan Type: load
Timestamp: 2024-11-15T10:45:00Z
```

**Expected Result:**
- 🚨 Scan gap detected
- ⚠️ Risk score increased
- 📋 Investigation triggered

---

## Agent 2: Risk Scoring Engine 🎯

### Test 4: Multi-Factor High Risk

**Scenario:** Elite passenger, complex routing, weather issues

```
Bag Tag: CM400004
Passenger: Michael Chen
PNR: DEF456
Elite Status: Diamond
Location: PTY-T1-Checkin
Scan Type: check-in
Timestamp: 2024-11-15T07:00:00Z
Flight: CM101 PTY-MIA
Route: PTY → MIA → JFK → LHR (3 connections)
Connection 1: MIA - 35 min (MCT: 45 min)
Connection 2: JFK - 50 min (MCT: 60 min)
Weather: Storms at MIA, Snow at JFK
Bag Weight: 28kg (heavy)
```

**Expected Result:**
- 🔴 Risk score: ~0.92 (Critical)
- 📦 P0 exception case (Diamond elite)
- 🚗 Courier dispatch analysis initiated
- 📱 Immediate passenger communication
- 👤 Human-in-the-loop alert

---

### Test 5: Airport Performance Factor

**Scenario:** Bag routing through poor-performing airport

```
Bag Tag: CM500005
Location: PTY-T1-Checkin
Scan Type: check-in
Timestamp: 2024-11-15T06:00:00Z
Route: PTY → EWR → ORD
EWR Historical Performance: 4.8% mishandling rate
Connection Time: 55 minutes
```

**Expected Result:**
- ⚠️ Risk score: ~0.68 (Medium-High)
- 📊 Airport performance factored in
- 🔍 Enhanced tracking enabled

---

## Agent 3: WorldTracer Integration 🌍

### Test 6: Missed Connection - Auto PIR

**Scenario:** Bag confirmed to miss connection

**Step 1 - Normal check-in:**
```
Bag Tag: CM600006
Passenger: Lisa Rodriguez
PNR: GHI789
Location: PTY-T1-Checkin
Scan Type: check-in
Timestamp: 2024-11-15T08:00:00Z
Flight: CM101 PTY-MIA (dep 10:00, arr 11:40)
Connecting: CM205 MIA-JFK (dep 12:00)
```

**Step 2 - Delayed arrival scan:**
```
Bag Tag: CM600006
Location: MIA-Arrivals
Scan Type: arrival
Timestamp: 2024-11-15T11:58:00Z
(2 minutes before connecting flight departure!)
```

**Expected Result:**
- 🔴 Risk score: 0.98 (Critical - too late)
- 📝 **Auto-filed PIR** to WorldTracer
  - PIR #: MIACM20241115606
  - Status: OHD (Offload Hold)
  - Alternative: CM107 at 15:30
- 🚗 Courier dispatch approved
- 📱 Passenger notified of next available flight

---

## Agent 4: SITA Type B Message Handler 📨

### Test 7: Baggage Transfer Message (BTM)

**Scenario:** Inter-airline bag transfer

```
BTM
FM PTYCMXH
TO MIACMXA
CM101/15NOV.PTY-MIA
.PAXSMITH/JOHN.PNRABC123
.CM700007/23KG/JFK
.PAXJOHNSON/SARAH.PNRXYZ456
.CM700008/18KG/MIA
```

**Expected Result:**
- 📨 Type B message parsed
- 📦 2 bags identified:
  - CM700007 → JFK (requires connection)
  - CM700008 → MIA (terminating)
- ✅ Digital twins updated
- 🔍 Connection monitoring for CM700007

---

### Test 8: Baggage Source Message (BSM)

**Scenario:** Bag manifest from originating station

```
BSM
CM101/15NOV.PTY.1045
.CM800009/PTY/MIA/T/23/KG
.CM800010/PTY/JFK/T/18/KG
.CM800011/PTY/EWR/T/25/KG
```

**Expected Result:**
- 📋 3 bags on flight CM101 manifested
- ✅ All bags tracked
- 🔍 System monitors for arrival scans at MIA

---

## Agent 5: BaggageXML Handler 📋

### Test 9: Interline XML Transfer

**Scenario:** Copa bag connecting to United Airlines

```xml
<?xml version="1.0"?>
<BaggageTransfer>
  <BagTag>CM900012</BagTag>
  <Carrier>CM</Carrier>
  <Flight>CM101</Flight>
  <From>PTY</From>
  <To>MIA</To>
  <TransferTo>
    <Carrier>UA</Carrier>
    <Flight>UA1234</Flight>
    <From>MIA</From>
    <To>LAX</To>
  </TransferTo>
  <Passenger>
    <Name>Robert Williams</Name>
    <PNR>JKL012</PNR>
  </Passenger>
  <ConnectionTime>65</ConnectionTime>
</BaggageTransfer>
```

**Expected Result:**
- 🤝 Interline transfer recognized
- ✅ Downline carrier (UA) notified
- 📊 Risk assessment for inter-airline transfer
- 🔍 Enhanced monitoring

---

## Agent 6: Exception Case Manager 📦

### Test 10: P0 Priority Case (VIP Passenger)

**Scenario:** Diamond elite with critical risk

```
Bag Tag: CM010013
Passenger: Alexandra Thompson
PNR: MNO345
Elite Status: Diamond
Ticket Value: $8,500 (Business Class)
Location: PTY-T1-Checkin
Scan Type: check-in
Timestamp: 2024-11-15T06:00:00Z
Flight: CM101 PTY-MIA
Connecting: CM205 MIA-JFK (20 min connection)
Weather: Severe storms at MIA
Risk Score: 0.96
```

**Expected Result:**
- 🔴 **P0 Case Created**: CASE20241115013
- 👤 **Assigned to**: Station Manager MIA
- ⏰ **SLA**: 15 minutes
- 🚨 **Escalation**: If no action in 7 minutes
- 💰 **Compensation risk**: $1,500 + reputation
- 🚗 **Courier**: Auto-approved (pre-authorized)
- 📱 **Notification**: Immediate SMS + Call

---

### Test 11: Case Escalation

**Scenario:** P1 case approaching SLA breach

```
Bag Tag: CM011014
Passenger: David Kim
PNR: PQR678
Elite Status: Gold
Risk Score: 0.81
Case Status: Open for 28 minutes
SLA: 30 minutes
Actions Taken: None yet
```

**Expected Result:**
- ⚠️ **Escalation Alert**: 2 min to SLA breach
- 📧 **Notification**: Team lead + Manager
- 🔔 **Dashboard Alert**: Red flashing indicator
- 🎯 **Recommendation**: Immediate courier dispatch

---

## Agent 7: Courier Dispatch Agent 🚗

### Test 12: Cost-Benefit Analysis

**Scenario:** Calculate dispatch decision

```
Bag Tag: CM012015
Passenger: Emily Davis
PNR: STU901
Elite Status: Platinum
Risk Score: 0.94
Bag Status: Will miss connection
Next Flight: +6 hours
Passenger Destination: Hotel in Manhattan
Montreal Convention Limit: $1,500
Reputation Cost (Platinum): $800
Courier Cost Estimate: $250
```

**Expected Result:**
- 💰 **Analysis**:
  - Potential Cost: $2,300 ($1,500 + $800)
  - Courier Cost: $250
  - **Net Savings: $2,050**
- ✅ **Decision**: AUTO-DISPATCH
- 🚗 **Courier Booked**: ABC Courier Services
- 📍 **Delivery**: Marriott Marquis, Times Square
- 📱 **Passenger Notified**: ETA 21:30

---

### Test 13: Human Approval Required (High Value)

**Scenario:** Very expensive courier dispatch

```
Bag Tag: CM013016
Passenger: James Wilson
PNR: VWX234
Elite Status: Diamond
Risk Score: 0.97
Location: Delayed at EWR
Passenger Location: San Francisco (cross-country)
Courier Cost: $850 (overnight air freight)
```

**Expected Result:**
- ⚠️ **Human Approval Required**: Cost > $500
- 👤 **Approval Request**: Sent to Operations Manager
- 📊 **Recommendation**: APPROVE (saves $1,400)
- ⏰ **Approval Timeout**: 10 minutes
- 🔄 **Fallback**: Next available flight if denied

---

## Agent 8: Passenger Communication 📱

### Test 14: Proactive Notification

**Scenario:** Potential issue detected early

```
Bag Tag: CM014017
Passenger: Maria Garcia
PNR: YZA567
Elite Status: Gold
Location: Currently in sortation at MIA
Risk Score: 0.76 (increased from 0.45)
Issue: Connection time reduced due to inbound delay
Status: Bag still on track, but monitoring
```

**Expected Result:**
- 📱 **SMS Sent**:
  ```
  Hi Maria, we're monitoring your bag CM014017 due to
  a flight delay. It's currently being processed at MIA
  and we're ensuring it makes your connection. No action
  needed. Track: [link]
  ```
- 📧 **Email**: Detailed update with timeline
- 🔔 **App Push**: (if app installed)
- ⏰ **Follow-up**: Confirmation SMS when loaded

---

### Test 15: Courier Delivery Notification

**Scenario:** Bag being delivered by courier

```
Bag Tag: CM015018
Passenger: Thomas Anderson
PNR: BCD890
Delivery Status: Courier en route
Hotel: The Plaza, New York
ETA: 22:00
Courier: John Doe, #XYZ789
Courier Phone: +1-555-0123
```

**Expected Result:**
- 📱 **SMS Sent**:
  ```
  Thomas, great news! Your bag CM015018 is on its way
  to The Plaza. Delivery expected by 10:00 PM. Courier:
  John (555-0123). It will be left at the front desk.
  Track: [link]
  ```
- 📧 **Email**: Delivery details + courier contact
- ✅ **Delivery Confirmation**: SMS when delivered

---

## 🎭 Complete End-to-End Demo Scenario

### "The Perfect Save" - Full System Demo

**Cast:**
- Passenger: Jennifer Martinez (Diamond Elite)
- Bag Tag: CM999999
- Route: PTY → MIA → JFK → LHR (3 connections)

**Act 1: Check-In (08:00 AM)**

```
Bag Tag: CM999999
Passenger: Jennifer Martinez
PNR: DEMO123
Elite Status: Diamond
Location: PTY-T1-Checkin
Scan Type: check-in
Timestamp: 2024-11-15T08:00:00Z
Flight: CM101 PTY-MIA (dep 10:00, arr 13:45)
Connecting: CM205 MIA-JFK (dep 14:20)
Final: UA100 JFK-LHR (dep 19:00)
Bag Weight: 23kg
```

**System Response:**
- Agent 1: ✅ Scan processed, digital twin created
- Agent 2: 🎯 Risk score: 0.32 (Low - good connection times)
- Agent 6: No case needed
- Agent 8: ✅ Check-in confirmation SMS

---

**Act 2: Weather Alert (10:30 AM - Mid-Flight)**

```
WEATHER UPDATE:
Severe thunderstorms at MIA
Expected delays: 45-60 minutes
CM101 arrival now: 14:30 (45 min delay)
CM205 departure: 14:20 (BAG WILL MISS!)
```

**System Response (Automatic):**
- Agent 2: 🔄 Risk recalculated → 0.91 (Critical!)
- Agent 6: 📦 P0 Case created: CASE20241115999
- Agent 3: 📝 WorldTracer PIR prepared (not filed yet)
- Agent 7: 💰 Courier analysis: $200 vs $2,500 → APPROVED
- Agent 8: 📱 Proactive SMS sent

**SMS to Jennifer:**
```
Hi Jennifer, due to weather delays, your bag may miss
your MIA-JFK connection. Don't worry - we're already
arranging to have it on the next flight (CM207 at 16:30)
and delivered to your hotel in London if needed. We've
got you covered!
```

---

**Act 3: The Scramble (14:35 PM - Arrival at MIA)**

```
Bag Tag: CM999999
Location: MIA-Arrivals
Scan Type: arrival
Timestamp: 2024-11-15T14:35:00Z
Status: CM205 already departed (14:20)
```

**System Response:**
- Agent 1: ✅ Arrival scan confirmed (as expected)
- Agent 3: 📝 **PIR FILED** to WorldTracer
  - Alternative flight: CM207 MIA-JFK (16:30)
  - Connects to: UA102 JFK-LHR (22:00)
- Agent 6: ✅ Case updated: Bag on CM207
- Agent 7: 🚗 Courier booked for LHR hotel delivery
- Agent 8: 📱 Update SMS sent

---

**Act 4: Happy Ending (23:00 PM London Time)**

```
Bag Tag: CM999999
Location: LHR-Arrivals
Scan Type: arrival
Timestamp: 2024-11-16T04:00:00Z (London time: 05:00)
Courier: Dispatched to Hilton Park Lane
```

**System Response:**
- Agent 1: ✅ LHR arrival confirmed
- Agent 7: 🚗 Courier picked up, en route
- Agent 8: 📱 Final SMS

**SMS to Jennifer:**
```
Your bag has arrived in London and is being delivered
to the Hilton Park Lane. Expected by 7:00 AM (before
your 9:00 meeting!). Thank you for your patience and
welcome to London! - Copa Airlines
```

**Delivery Confirmation (07:15 AM):**
```
Your bag CM999999 has been delivered to the Hilton
Park Lane front desk. Have a great day!
```

---

## 📊 Demo Results Dashboard

After running these scenarios, your dashboard should show:

**KPIs:**
- Bags Processed: 18
- High Risk Bags: 8
- Exception Cases: 6
- PIRs Filed: 3
- Couriers Dispatched: 4
- Passengers Notified: 18

**Cost Savings:**
- Potential Compensation: $12,500
- Proactive Costs: $1,850 (couriers)
- **Net Savings: $10,650**

---

## 🎯 Tips for a Great Demo

1. **Start Simple**: Test 1 (normal scan) → builds confidence
2. **Show Intelligence**: Test 2 (tight connection) → shows AI risk scoring
3. **Demonstrate Automation**: Test 6 (missed connection) → auto-PIR filing
4. **Highlight Savings**: Test 12 (courier dispatch) → ROI calculation
5. **End with WOW**: Complete scenario → full orchestration

**Remember**: Each test takes 2-5 seconds to process. The speed is impressive!

---

## 🐛 Troubleshooting

**"Error processing event"**
- Check API server is running: `curl http://localhost:8000/health`
- Check logs: `tail -f logs/api_server.log`

**"No risk score calculated"**
- Ensure ANTHROPIC_API_KEY is set in .env
- Check Claude API quota

**"Dashboard not updating"**
- Click "🔄 Refresh Dashboard" button
- Check Redis is running: `docker ps | grep redis`

---

**Ready to blow some minds? Copy-paste these scenarios and watch your AI agents work their magic!** 🚀
