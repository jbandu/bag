"""
Simple Streamlit Dashboard for Baggage Operations Monitoring
Lightweight version that works without orchestrator/redis dependencies
"""
import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import plotly.express as px

# Page config
st.set_page_config(
    page_title="Baggage Operations Intelligence",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API URL - configurable via environment or default to Railway API
import os
API_URL = os.getenv("API_URL", "https://web-production-3965.up.railway.app").strip()

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("✈️ Baggage Operations Intelligence Platform")
st.markdown("### AI-Powered Baggage Tracking & Risk Management")

# Sidebar
with st.sidebar:
    st.header("🎯 Navigation")
    page = st.radio("Select View", [
        "📊 Dashboard Overview",
        "🔍 Bag Lookup",
        "🕸️ Knowledge Graph",
        "📈 System Status",
        "🤖 About"
    ])

    st.markdown("---")
    st.markdown(f"**API:** `{API_URL}`")
    st.markdown(f"**Updated:** {datetime.now().strftime('%H:%M:%S')}")

# Main Content
if page == "📊 Dashboard Overview":
    st.header("Dashboard Overview")

    # Fetch real-time stats from API
    try:
        response = requests.get(f"{API_URL}/api/v1/dashboard/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Bags Tracked", stats.get('total_bags', 0))
            with col2:
                st.metric("Total Scans", stats.get('total_scans', 0))
            with col3:
                st.metric("High Risk Alerts", stats.get('high_risk_count', 0))
            with col4:
                medium_risk = stats.get('medium_risk_count', 0)
                st.metric("Medium Risk", medium_risk)

            st.markdown("---")

            # Risk Distribution Chart
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📊 Risk Distribution")
                risk_data = pd.DataFrame({
                    'Risk Level': ['Low Risk', 'Medium Risk', 'High Risk'],
                    'Count': [
                        stats.get('low_risk_count', 0),
                        stats.get('medium_risk_count', 0),
                        stats.get('high_risk_count', 0)
                    ]
                })
                fig = px.pie(risk_data, values='Count', names='Risk Level',
                            color='Risk Level',
                            color_discrete_map={
                                'Low Risk': '#00CC66',
                                'Medium Risk': '#FFB84D',
                                'High Risk': '#FF4444'
                            })
                st.plotly_chart(fig, width='stretch')

            with col2:
                st.subheader("📈 Status Breakdown")
                status_breakdown = stats.get('status_breakdown', {})
                if status_breakdown:
                    status_df = pd.DataFrame([
                        {'Status': k, 'Count': v}
                        for k, v in status_breakdown.items()
                    ])
                    fig = px.bar(status_df, x='Status', y='Count',
                                color='Count',
                                color_continuous_scale='Viridis')
                    st.plotly_chart(fig, width='stretch')
                else:
                    st.info("No status data available")

            # High-Risk Bags Alert Table
            st.markdown("---")
            st.subheader("🔴 High-Risk Bags Requiring Attention")
            high_risk_bags = stats.get('high_risk_bags', [])
            if high_risk_bags:
                df = pd.DataFrame(high_risk_bags)
                # Format risk_score as percentage
                df['risk_score'] = df['risk_score'].apply(lambda x: f"{float(x)*100:.0f}%")
                st.dataframe(
                    df,
                    width='stretch',
                    hide_index=True
                )
            else:
                st.success("✅ No high-risk bags at this time!")

        else:
            st.error(f"Failed to fetch stats: API returned {response.status_code}")
            # Fallback to static data
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Bags Tracked", "N/A")
            with col2:
                st.metric("Active Scans", "N/A")
            with col3:
                st.metric("High Risk Alerts", "N/A")
            with col4:
                st.metric("System Health", "N/A")

    except Exception as e:
        st.error(f"❌ Failed to connect to API: {str(e)}")
        st.info("Please check that the API is running and the API_URL is correct")

elif page == "🔍 Bag Lookup":
    st.header("Bag Lookup")

    # Sample bag tags for quick access
    st.markdown("**Quick Test:** Try searching for: `CM12345`, `CM67890`, `CM11111`, `CM99999`")

    bag_tag = st.text_input("Enter Bag Tag", placeholder="e.g., CM12345")

    if st.button("Search") or bag_tag:
        if bag_tag:
            with st.spinner(f"Searching for {bag_tag}..."):
                try:
                    response = requests.get(f"{API_URL}/api/v1/bag/{bag_tag}", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        bag_info = data.get('status', {})

                        # Display bag header with risk indicator
                        risk_score = float(bag_info.get('risk_score', 0))
                        risk_emoji = "🟢" if risk_score < 0.3 else "🟡" if risk_score < 0.7 else "🔴"
                        st.success(f"{risk_emoji} Found bag: {bag_tag} - Risk: {risk_score*100:.0f}%")

                        # Display bag details in columns
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("Passenger", bag_info.get('passenger_name', 'N/A'))
                            st.metric("PNR", bag_info.get('pnr', 'N/A'))

                        with col2:
                            st.metric("Status", bag_info.get('status', 'N/A'))
                            st.metric("Current Location", bag_info.get('current_location', 'N/A'))

                        with col3:
                            st.metric("Risk Score", f"{risk_score*100:.0f}%")
                            st.metric("Routing", bag_info.get('routing', 'N/A'))

                        # Show full JSON details in expander
                        with st.expander("📋 Full Bag Details (JSON)"):
                            st.json(bag_info)

                    elif response.status_code == 404:
                        st.warning(f"Bag {bag_tag} not found in system")
                    else:
                        st.error(f"API Error: {response.status_code}")
                except Exception as e:
                    st.error(f"Failed to connect to API: {str(e)}")
        else:
            st.warning("Please enter a bag tag")

    # Show all bags table
    st.markdown("---")
    st.subheader("📦 All Tracked Bags")

    try:
        response = requests.get(f"{API_URL}/api/v1/bags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            bags = data.get('bags', [])
            if bags:
                df = pd.DataFrame(bags)
                # Format risk_score as percentage
                df['risk_score'] = df['risk_score'].apply(lambda x: f"{float(x)*100:.0f}%")
                # Select and reorder columns
                display_cols = ['bag_tag', 'passenger_name', 'pnr', 'status',
                               'current_location', 'routing', 'risk_score']
                df = df[display_cols]
                st.dataframe(df, width='stretch', hide_index=True)
            else:
                st.info("No bags found")
    except Exception as e:
        st.error(f"Failed to fetch bags list: {str(e)}")

elif page == "🕸️ Knowledge Graph":
    st.header("Knowledge Graph & Ontology")
    st.markdown("""
    This knowledge graph represents the baggage operations domain model based on the **gist (Semantic Arts) Foundational Ontology**.
    It shows the relationships between entities like Baggage, Passengers, Flights, Risk Assessments, and more.
    """)

    # Tabs for different views
    kg_tab1, kg_tab2, kg_tab3 = st.tabs(["🕸️ Interactive Graph", "📊 Entity Classes", "📝 Ontology Document"])

    with kg_tab1:
        st.subheader("Interactive Knowledge Graph Visualization")

        # Import networkx and plotly graph objects for network visualization
        import plotly.graph_objects as go
        import networkx as nx

        # Create a sample knowledge graph based on the ontology
        G = nx.Graph()

        # Define node categories with colors
        node_colors = {
            'physical': '#3498db',  # Blue for physical things
            'digital': '#9b59b6',   # Purple for digital twins
            'event': '#e74c3c',     # Red for events
            'agent': '#2ecc71',     # Green for agents
            'assessment': '#f39c12', # Orange for assessments
            'case': '#e67e22'       # Dark orange for cases
        }

        # Add nodes (entities from the ontology)
        nodes = [
            ('Baggage', 'physical', 30),
            ('Passenger', 'physical', 25),
            ('Flight', 'physical', 25),
            ('Airport', 'physical', 20),
            ('BaggageDigitalTwin', 'digital', 30),
            ('ScanEvent', 'event', 20),
            ('MishandlingEvent', 'event', 15),
            ('RecoveryEvent', 'event', 15),
            ('RiskAssessment', 'assessment', 25),
            ('ExceptionCase', 'case', 20),
            ('PIR', 'case', 20),
            ('AIAgent', 'agent', 20),
            ('HumanAgent', 'agent', 18),
            ('CourierDispatch', 'case', 18),
        ]

        for node, category, size in nodes:
            G.add_node(node, category=category, size=size)

        # Add edges (relationships from the ontology)
        edges = [
            ('Baggage', 'Passenger', 'BELONGS_TO'),
            ('Baggage', 'Flight', 'ROUTED_ON'),
            ('BaggageDigitalTwin', 'Baggage', 'REPRESENTS'),
            ('ScanEvent', 'Baggage', 'SCANS'),
            ('ScanEvent', 'Airport', 'AT_LOCATION'),
            ('RiskAssessment', 'Baggage', 'ASSESSES'),
            ('ExceptionCase', 'Baggage', 'CONCERNS'),
            ('ExceptionCase', 'HumanAgent', 'ASSIGNED_TO'),
            ('ExceptionCase', 'RiskAssessment', 'HAS_ASSESSMENT'),
            ('PIR', 'Baggage', 'DOCUMENTS'),
            ('CourierDispatch', 'Baggage', 'FOR_BAGGAGE'),
            ('MishandlingEvent', 'Baggage', 'AFFECTS'),
            ('AIAgent', 'ScanEvent', 'PROCESSED'),
            ('AIAgent', 'RiskAssessment', 'CREATED'),
            ('BaggageDigitalTwin', 'ScanEvent', 'HAS_SCAN'),
        ]

        for source, target, rel_type in edges:
            G.add_edge(source, target, relationship=rel_type)

        # Create layout
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

        # Create edge traces
        edge_traces = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_trace = go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode='lines',
                line=dict(width=1, color='#888'),
                hoverinfo='none',
                showlegend=False
            )
            edge_traces.append(edge_trace)

        # Create node traces by category
        node_trace_by_category = {}
        for node in G.nodes():
            category = G.nodes[node]['category']
            size = G.nodes[node]['size']

            if category not in node_trace_by_category:
                node_trace_by_category[category] = {
                    'x': [], 'y': [], 'text': [], 'size': []
                }

            x, y = pos[node]
            node_trace_by_category[category]['x'].append(x)
            node_trace_by_category[category]['y'].append(y)
            node_trace_by_category[category]['text'].append(node)
            node_trace_by_category[category]['size'].append(size)

        # Create plotly traces for each category
        node_traces = []
        for category, data in node_trace_by_category.items():
            trace = go.Scatter(
                x=data['x'],
                y=data['y'],
                mode='markers+text',
                name=category.capitalize(),
                marker=dict(
                    size=data['size'],
                    color=node_colors[category],
                    line=dict(width=2, color='white')
                ),
                text=data['text'],
                textposition='top center',
                textfont=dict(size=10, color='black'),
                hoverinfo='text'
            )
            node_traces.append(trace)

        # Create figure
        fig = go.Figure(data=edge_traces + node_traces)

        fig.update_layout(
            title="Baggage Operations Knowledge Graph",
            titlefont_size=16,
            showlegend=True,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=700,
            plot_bgcolor='#f8f9fa'
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("🔗 Key Relationships")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            **Core Relationships:**
            - `Baggage → Passenger` (BELONGS_TO)
            - `Baggage → Flight` (ROUTED_ON)
            - `BaggageDigitalTwin → Baggage` (REPRESENTS)
            - `ScanEvent → Baggage` (SCANS)
            - `RiskAssessment → Baggage` (ASSESSES)
            """)

        with col2:
            st.markdown("""
            **Case Management:**
            - `ExceptionCase → Baggage` (CONCERNS)
            - `ExceptionCase → HumanAgent` (ASSIGNED_TO)
            - `PIR → Baggage` (DOCUMENTS)
            - `CourierDispatch → Baggage` (FOR_BAGGAGE)
            """)

    with kg_tab2:
        st.subheader("Entity Classes & Properties")

        # Create expandable sections for each entity type
        with st.expander("🎒 Baggage (Physical Thing)"):
            st.markdown("""
            **Properties:**
            - `bagTag`: Unique identifier
            - `weight`: Magnitude (kg)
            - `dimensions`: Magnitude (cm³)
            - `color`: Category
            - `type`: Category (Suitcase, Backpack, DuffelBag)
            - `contentsValue`: Magnitude (USD)
            - `specialHandling`: Array (Fragile, Medical, Sports, LiveAnimal)
            """)

        with st.expander("👤 Passenger (Person)"):
            st.markdown("""
            **Properties:**
            - `pnr`: ID
            - `name`: Text
            - `eliteStatus`: Category (None, Silver, Gold, Platinum, Diamond)
            - `contactEmail`: EmailAddress
            - `contactPhone`: TelephoneNumber
            - `lifetimeValue`: Magnitude (USD)
            - `frequentFlyerNumber`: ID
            """)

        with st.expander("✈️ Flight (Task)"):
            st.markdown("""
            **Properties:**
            - `flightNumber`: ID
            - `origin`: GeoPoint
            - `destination`: GeoPoint
            - `scheduledDeparture`: TimeInterval
            - `actualDeparture`: TimeInterval
            - `scheduledArrival`: TimeInterval
            - `actualArrival`: TimeInterval
            - `status`: Category (Scheduled, Boarding, Departed, Arrived, Cancelled, Delayed)
            """)

        with st.expander("🏢 Airport (Place)"):
            st.markdown("""
            **Properties:**
            - `iataCode`: ID (3-letter)
            - `icaoCode`: ID (4-letter)
            - `city`: Text
            - `country`: Text
            - `timezone`: Text
            - `mctDomestic`: Duration (minutes)
            - `mctInternational`: Duration (minutes)
            - `performanceScore`: Magnitude (0-10)
            """)

        with st.expander("💾 BaggageDigitalTwin (Digital Thing)"):
            st.markdown("""
            **Properties:**
            - `physicalBag`: Reference to Baggage
            - `currentStatus`: BagStatus
            - `currentLocation`: GeoPoint
            - `riskScore`: Magnitude (0-1)
            - `riskLevel`: Category (Low, Medium, High, Critical)
            - `riskFactors`: Array of Text
            - `journeyHistory`: Array of ScanEvents
            """)

        with st.expander("📊 RiskAssessment (Assessment)"):
            st.markdown("""
            **Properties:**
            - `riskScore`: Magnitude (0-1)
            - `riskLevel`: Category
            - `primaryFactors`: Array of Text
            - `recommendedAction`: Category (Monitor, Alert, Intervene, DispatchCourier)
            - `confidence`: Magnitude (0-1)
            - `reasoning`: Text
            - `connectionTimeMinutes`: Duration
            - `mctMinutes`: Duration
            """)

        with st.expander("📋 ExceptionCase (Task)"):
            st.markdown("""
            **Properties:**
            - `caseId`: ID
            - `priority`: Category (P0-Critical, P1-High, P2-Medium, P3-Low)
            - `status`: Category (Open, InProgress, PendingApproval, Resolved, Closed)
            - `assignedTo`: Agent reference
            - `riskAssessment`: RiskAssessment reference
            - `slaDeadline`: TimeInterval
            - `actionsTaken`: Array of Actions
            """)

        with st.expander("🤖 AIAgent (Agent)"):
            st.markdown("""
            **Subtypes:**
            1. **ScanProcessorAgent**: Creates ScanEvent nodes, updates digital twins
            2. **RiskScorerAgent**: Creates RiskAssessment nodes, calculates risk scores
            3. **WorldTracerAgent**: Creates PIR nodes, manages mishandling reports
            4. **SITAHandlerAgent**: Processes SITA Type B messages
            5. **BaggageXMLAgent**: Handles BaggageXML messages
            6. **CaseManagerAgent**: Creates and manages ExceptionCases
            7. **CourierDispatchAgent**: Handles courier dispatch decisions
            8. **PassengerCommsAgent**: Manages passenger notifications
            """)

    with kg_tab3:
        st.subheader("📝 Complete Ontology Documentation")

        # Read and display the markdown document
        try:
            with open('/home/user/bag/docs/knowledge-graph-ontology.md', 'r') as f:
                ontology_content = f.read()

            st.markdown(ontology_content)
        except Exception as e:
            st.error(f"Failed to load ontology document: {str(e)}")
            st.info("The ontology document should be located at: `/docs/knowledge-graph-ontology.md`")

elif page == "📈 System Status":
    st.header("System Status")

    # Check API health
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            st.success("✅ API is healthy")
            st.json(health_data)
        else:
            st.error(f"⚠️ API returned status code: {response.status_code}")
    except Exception as e:
        st.error(f"❌ Failed to connect to API: {str(e)}")

    st.markdown("---")

    # Get API info
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        if response.status_code == 200:
            api_info = response.json()
            st.subheader("API Information")
            st.json(api_info)
    except Exception as e:
        st.error(f"Failed to get API info: {str(e)}")

else:  # About page
    st.header("About")

    st.markdown("""
    ## 🎯 Baggage Operations Intelligence Platform

    An AI-powered baggage tracking and risk management system that provides:

    ### 🤖 Key Features
    - **Real-time Tracking**: Monitor baggage through all checkpoints
    - **Risk Assessment**: AI-powered risk scoring for each bag
    - **Exception Management**: Automated handling of baggage issues
    - **Multi-source Integration**: BRS, BHS, DCS, SITA Type B messages
    - **WorldTracer Integration**: Seamless mishandled baggage reporting

    ### 🚀 Technology Stack
    - **Backend**: FastAPI + Claude Sonnet 4
    - **Dashboard**: Streamlit
    - **Database**: Neon PostgreSQL
    - **Deployment**: Railway
    - **AI Framework**: LangGraph with 8 specialized agents

    ### 📊 Specialized AI Agents
    1. Scan Event Processor
    2. Risk Scoring Engine
    3. WorldTracer Integration
    4. SITA Message Handler
    5. BaggageXML Handler
    6. Exception Case Manager
    7. Courier Dispatch Agent
    8. Passenger Communication

    ---
    **Powered by Claude Sonnet 4 + LangGraph**
    """)

    st.info("Dashboard Version: 1.0.0 (Simple Mode)")

# Footer
st.markdown("---")
st.markdown("*Baggage Operations Intelligence Platform - Powered by AI*")
