"""
Streamlit Dashboard for Baggage Operations Monitoring
"""
import sys
import os

# Add parent directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import asyncio
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from loguru import logger

from utils.database import redis_cache, supabase_db
from orchestrator.baggage_orchestrator import orchestrator


# Page config
st.set_page_config(
    page_title="Baggage Operations Intelligence",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .risk-high {
        background-color: #ff4b4b;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
    }
    .risk-critical {
        background-color: #8b0000;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)


# App title
st.title("🎒 Baggage Operations Intelligence Platform")
st.markdown("### AI-Powered Predictive Baggage Management")

# Sidebar
with st.sidebar:
    st.header("⚙️ Controls")
    
    # Manual scan input
    st.subheader("📥 Process Scan Event")
    manual_scan = st.text_area(
        "Paste scan data or Type B message:",
        height=100,
        placeholder="Example:\nBag Tag: CM123456\nLocation: PTY-T1-BHS\nTimestamp: 2024-11-11T14:30:00Z"
    )
    
    if st.button("🚀 Process Event", use_container_width=True):
        if manual_scan:
            with st.spinner("Processing scan event..."):
                try:
                    # Run async function
                    result = asyncio.run(orchestrator.process_baggage_event(manual_scan))
                    if result['status'] == 'success':
                        st.success(f"✅ Event processed successfully!")
                        st.json(result)
                    else:
                        st.error(f"❌ Error: {result.get('error')}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("Please enter scan data")
    
    st.divider()
    
    # Refresh controls
    if st.button("🔄 Refresh Dashboard", use_container_width=True):
        st.rerun()
    
    st.markdown("---")
    st.markdown("**Copa Airlines**\n\nPowered by Number Labs")


# Main dashboard
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Real-Time Monitoring",
    "🎯 Risk Assessment",
    "📦 Active Cases",
    "📈 Analytics"
])


# Tab 1: Real-Time Monitoring
with tab1:
    st.header("Real-Time Operations")
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        bags_processed = redis_cache.get_metric('bags_processed')
        st.metric(
            label="Bags Processed Today",
            value=f"{bags_processed:,}",
            delta="+12 from last hour"
        )
    
    with col2:
        scans_processed = redis_cache.get_metric('scans_processed')
        st.metric(
            label="Scans Processed",
            value=f"{scans_processed:,}",
            delta="+45 from last hour"
        )
    
    with col3:
        exceptions = redis_cache.get_metric('exceptions_handled')
        st.metric(
            label="Exceptions Handled",
            value=f"{exceptions}",
            delta="-3 from yesterday",
            delta_color="inverse"
        )
    
    with col4:
        high_risk_bags = redis_cache.get_metric('high_risk_bags_detected')
        st.metric(
            label="High Risk Bags",
            value=f"{high_risk_bags}",
            delta="+2 from last hour",
            delta_color="inverse"
        )
    
    st.divider()
    
    # Recent scan events
    st.subheader("Recent Scan Events")
    
    # Mock data for demonstration
    recent_scans = pd.DataFrame({
        'Time': pd.date_range(end=datetime.now(), periods=10, freq='5min')[::-1],
        'Bag Tag': [f'CM{1000+i}' for i in range(10)],
        'Location': ['PTY-T1', 'MIA-T3', 'PTY-BHS', 'EWR-T1', 'PTY-T1', 
                     'JFK-T8', 'PTY-BHS', 'MIA-T3', 'PTY-T1', 'ORD-T1'],
        'Status': ['In Transit', 'Arrived', 'Loading', 'In Transit', 'Checked In',
                   'In Transit', 'Sortation', 'Arrived', 'Loading', 'Delayed'],
        'Risk Score': [0.2, 0.1, 0.3, 0.5, 0.1, 0.7, 0.4, 0.2, 0.3, 0.85]
    })
    
    # Color code by risk
    def highlight_risk(row):
        if row['Risk Score'] >= 0.9:
            return ['background-color: #8b0000; color: white'] * len(row)
        elif row['Risk Score'] >= 0.7:
            return ['background-color: #ff4b4b; color: white'] * len(row)
        elif row['Risk Score'] >= 0.4:
            return ['background-color: #ffa500; color: white'] * len(row)
        else:
            return [''] * len(row)
    
    st.dataframe(
        recent_scans.style.apply(highlight_risk, axis=1),
        use_container_width=True,
        hide_index=True
    )


# Tab 2: Risk Assessment
with tab2:
    st.header("Risk Assessment Overview")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Risk distribution chart
        st.subheader("Risk Distribution")
        
        risk_data = pd.DataFrame({
            'Risk Level': ['Low', 'Medium', 'High', 'Critical'],
            'Count': [850, 120, 25, 5]
        })
        
        fig = px.pie(
            risk_data,
            values='Count',
            names='Risk Level',
            color='Risk Level',
            color_discrete_map={
                'Low': '#90EE90',
                'Medium': '#FFD700',
                'High': '#FF6347',
                'Critical': '#8B0000'
            },
            title="Current Risk Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Risk Factors")
        
        factors = pd.DataFrame({
            'Factor': ['Tight Connections', 'Airport Performance', 'Weather', 
                       'Routing Complexity', 'Scan Gaps'],
            'Count': [15, 8, 5, 12, 3]
        })
        
        fig = px.bar(
            factors,
            x='Count',
            y='Factor',
            orientation='h',
            title="Top Risk Factors"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # High risk bags
    st.subheader("🔴 High Risk Bags - Immediate Attention Required")
    
    high_risk_bags = pd.DataFrame({
        'Bag Tag': ['CM1234', 'CM5678', 'CM9012'],
        'Passenger': ['Smith, J.', 'Johnson, M.', 'Williams, R.'],
        'Elite Status': ['Platinum', 'Gold', 'Diamond'],
        'Risk Score': [0.92, 0.85, 0.78],
        'Primary Factor': ['MCT violation - 8 min buffer', 
                          'Airport performance + weather', 
                          'Routing complexity - 3 connections'],
        'Action': ['Courier dispatched', 'Team alerted', 'Monitoring']
    })
    
    st.dataframe(high_risk_bags, use_container_width=True, hide_index=True)


# Tab 3: Active Cases
with tab3:
    st.header("Active Exception Cases")
    
    # Case metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Open Cases", "28", "-5 from yesterday", delta_color="inverse")
    
    with col2:
        st.metric("PIRs Filed Today", "12", "+3 from yesterday")
    
    with col3:
        st.metric("Couriers Dispatched", "8", "+2 from yesterday")
    
    st.divider()
    
    # Active cases table
    st.subheader("Active Cases")
    
    cases = pd.DataFrame({
        'Case ID': ['CASE001', 'CASE002', 'CASE003', 'CASE004', 'CASE005'],
        'Bag Tag': ['CM1234', 'CM5678', 'CM9012', 'CM3456', 'CM7890'],
        'Priority': ['P0', 'P1', 'P2', 'P1', 'P0'],
        'Status': ['In Progress', 'Pending', 'Resolved', 'In Progress', 'Pending'],
        'Assigned To': ['Baggage Ops', 'Customer Service', 'Baggage Ops', 
                       'Ground Handling', 'Station Manager'],
        'Created': ['2 hours ago', '45 min ago', '3 hours ago', '1 hour ago', '30 min ago'],
        'SLA': ['On Track', 'At Risk', 'Met', 'On Track', 'At Risk']
    })
    
    st.dataframe(cases, use_container_width=True, hide_index=True)
    
    # Case details
    st.subheader("Case Details")
    selected_case = st.selectbox("Select case to view details:", cases['Case ID'].tolist())
    
    if selected_case:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Case Information**")
            st.write(f"**Case ID:** {selected_case}")
            st.write("**Bag Tag:** CM1234")
            st.write("**Priority:** P0 (Critical)")
            st.write("**Status:** In Progress")
            
            st.markdown("**Passenger Information**")
            st.write("**Name:** John Smith")
            st.write("**PNR:** ABC123")
            st.write("**Elite Status:** Platinum")
        
        with col2:
            st.markdown("**Timeline**")
            st.write("✅ 10:30 - Case created")
            st.write("✅ 10:35 - Risk assessment completed")
            st.write("✅ 10:40 - WorldTracer PIR filed")
            st.write("🔄 10:45 - Courier dispatch in progress")
            st.write("⏳ 10:50 - Passenger notified")


# Tab 4: Analytics
with tab4:
    st.header("Analytics & Insights")
    
    # Trend charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Baggage Volume Trend")
        
        # Mock trend data
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        volume_data = pd.DataFrame({
            'Date': dates,
            'Bags Processed': [800 + i*10 + (i%7)*50 for i in range(30)]
        })
        
        fig = px.line(
            volume_data,
            x='Date',
            y='Bags Processed',
            title="Daily Baggage Volume (Last 30 Days)"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Exception Rate Trend")
        
        exception_data = pd.DataFrame({
            'Date': dates,
            'Exception Rate': [3.5 - i*0.05 + (i%7)*0.2 for i in range(30)]
        })
        
        fig = px.line(
            exception_data,
            x='Date',
            y='Exception Rate',
            title="Exception Rate % (Last 30 Days)"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Performance metrics
    st.subheader("Performance Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Average Processing Time", "1.2s", "-0.3s from last week")
    
    with col2:
        st.metric("Prediction Accuracy", "94.5%", "+2.1% from last week")
    
    with col3:
        st.metric("Cost Savings (MTD)", "$125K", "+$18K from last month")
    
    st.divider()
    
    # Airport performance
    st.subheader("Airport Performance Comparison")
    
    airport_data = pd.DataFrame({
        'Airport': ['PTY', 'MIA', 'JFK', 'EWR', 'ORD', 'LHR'],
        'Baggage Handled': [25000, 18000, 22000, 15000, 20000, 19000],
        'Exception Rate': [2.1, 3.5, 4.2, 4.8, 3.9, 3.1],
        'On-Time %': [96.5, 92.3, 89.7, 88.2, 90.5, 91.8]
    })
    
    fig = go.Figure(data=[
        go.Bar(name='Baggage Handled (000s)', 
               x=airport_data['Airport'], 
               y=airport_data['Baggage Handled']/1000,
               yaxis='y', offsetgroup=1),
        go.Bar(name='Exception Rate %', 
               x=airport_data['Airport'], 
               y=airport_data['Exception Rate'],
               yaxis='y2', offsetgroup=2)
    ])
    
    fig.update_layout(
        title='Airport Performance Metrics',
        yaxis=dict(title='Bags Handled (000s)'),
        yaxis2=dict(title='Exception Rate %', overlaying='y', side='right'),
        barmode='group'
    )
    
    st.plotly_chart(fig, use_container_width=True)


# Footer
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**System Status:** 🟢 All systems operational")

with col2:
    st.markdown(f"**Last Updated:** {datetime.now().strftime('%H:%M:%S')}")

with col3:
    st.markdown("**Version:** 1.0.0 | **Build:** Production")
