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
