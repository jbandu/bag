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
API_URL = os.getenv("API_URL", "https://web-production-3965.up.railway.app")

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
        "📈 System Status",
        "🤖 About"
    ])

    st.markdown("---")
    st.markdown(f"**API:** `{API_URL}`")
    st.markdown(f"**Updated:** {datetime.now().strftime('%H:%M:%S')}")

# Main Content
if page == "📊 Dashboard Overview":
    st.header("Dashboard Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Bags Tracked", "1,234", "+52")
    with col2:
        st.metric("Active Scans", "89", "+12")
    with col3:
        st.metric("High Risk Alerts", "3", "-1")
    with col4:
        st.metric("System Health", "98%", "+2%")

    st.markdown("---")

    # Sample chart
    st.subheader("📈 Bag Processing Over Time")
    sample_data = pd.DataFrame({
        'Hour': list(range(24)),
        'Bags Processed': [45, 38, 52, 61, 73, 68, 55, 49, 67, 82, 91, 88,
                          95, 103, 98, 105, 112, 108, 95, 87, 76, 68, 59, 51]
    })
    fig = px.line(sample_data, x='Hour', y='Bags Processed',
                  title='Bags Processed by Hour (Last 24h)')
    st.plotly_chart(fig, use_container_width=True)

elif page == "🔍 Bag Lookup":
    st.header("Bag Lookup")

    bag_tag = st.text_input("Enter Bag Tag", placeholder="e.g., CM12345")

    if st.button("Search"):
        if bag_tag:
            with st.spinner(f"Searching for {bag_tag}..."):
                try:
                    response = requests.get(f"{API_URL}/api/v1/bag/{bag_tag}", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"Found bag: {bag_tag}")

                        col1, col2 = st.columns(2)
                        with col1:
                            st.json(data)
                        with col2:
                            st.info("Bag details retrieved from API")
                    elif response.status_code == 404:
                        st.warning(f"Bag {bag_tag} not found in system")
                    else:
                        st.error(f"API Error: {response.status_code}")
                except Exception as e:
                    st.error(f"Failed to connect to API: {str(e)}")
        else:
            st.warning("Please enter a bag tag")

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
