"""
Baggage AI Metrics Dashboard
Real-time monitoring dashboard for Copa Airlines demo

Run with: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

from src.metrics.collector import get_metrics_collector


# Page config
st.set_page_config(
    page_title="Baggage AI Metrics",
    page_icon="",
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
    .success {
        color: #28a745;
    }
    .error {
        color: #dc3545;
    }
    .warning {
        color: #ffc107;
    }
</style>
""", unsafe_allow_html=True)


# Initialize metrics collector
@st.cache_resource
def init_metrics_collector():
    """Initialize metrics collector (cached)"""
    return get_metrics_collector()


metrics = init_metrics_collector()


# Title
st.title(" Baggage AI Monitoring Dashboard")
st.markdown("**Copa Airlines** - Multi-Agent Baggage Handling System")

# Sidebar
st.sidebar.header("Dashboard Controls")
auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 1, 60, 5)
time_window = st.sidebar.selectbox(
    "Time window",
    [15, 30, 60, 120],
    index=2,
    format_func=lambda x: f"Last {x} minutes"
)

# Manual refresh button
if st.sidebar.button("Refresh Now"):
    st.rerun()

# Reset metrics (for testing)
if st.sidebar.button("Reset Metrics", type="secondary"):
    metrics.reset_metrics()
    st.sidebar.success("Metrics reset!")
    time.sleep(1)
    st.rerun()


# Main dashboard
def main():
    """Main dashboard content"""

    # Get current stats
    current_stats = metrics.get_current_stats()

    # Top-level metrics
    st.header("=Ê Current Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        current_requests = current_stats.get("current_minute", {}).get("requests", 0)
        st.metric(
            label="Requests (current minute)",
            value=current_requests,
            delta=None
        )

    with col2:
        current_errors = current_stats.get("current_minute", {}).get("errors", 0)
        error_rate = current_stats.get("current_minute", {}).get("error_rate", 0)
        st.metric(
            label="Errors (current minute)",
            value=current_errors,
            delta=f"{error_rate:.1f}%" if error_rate > 0 else "0%"
        )

    with col3:
        latency = current_stats.get("latency", {})
        avg_latency = latency.get("avg", 0)
        st.metric(
            label="Avg Latency",
            value=f"{avg_latency:.0f}ms",
            delta=None
        )

    with col4:
        p95_latency = latency.get("p95", 0)
        sla_status = "" if p95_latency < 2000 else " "
        st.metric(
            label="P95 Latency",
            value=f"{p95_latency:.0f}ms",
            delta=f"{sla_status} SLA {'OK' if p95_latency < 2000 else 'WARNING'}"
        )

    st.divider()

    # Request volume chart
    st.header("=È Request Volume")
    requests_data = metrics.get_requests_per_minute(last_n_minutes=time_window)

    if requests_data:
        df_requests = pd.DataFrame(requests_data)
        fig_requests = px.line(
            df_requests,
            x="timestamp",
            y="requests",
            title=f"Requests per Minute (Last {time_window} minutes)",
            labels={"requests": "Requests", "timestamp": "Time"}
        )
        fig_requests.update_traces(line_color="#0066cc")
        st.plotly_chart(fig_requests, use_container_width=True)
    else:
        st.info("No request data available yet")

    # Error rate chart
    st.header("=¨ Error Rate")
    error_data = metrics.get_error_rate(last_n_minutes=time_window)

    if error_data:
        df_errors = pd.DataFrame(error_data)

        # Create dual-axis chart
        fig_errors = go.Figure()

        # Requests line
        fig_errors.add_trace(go.Scatter(
            x=df_errors["timestamp"],
            y=df_errors["requests"],
            name="Requests",
            line=dict(color="#0066cc"),
            yaxis="y"
        ))

        # Errors line
        fig_errors.add_trace(go.Scatter(
            x=df_errors["timestamp"],
            y=df_errors["errors"],
            name="Errors",
            line=dict(color="#dc3545"),
            yaxis="y"
        ))

        # Error rate line
        fig_errors.add_trace(go.Scatter(
            x=df_errors["timestamp"],
            y=df_errors["error_rate"],
            name="Error Rate (%)",
            line=dict(color="#ffc107", dash="dash"),
            yaxis="y2"
        ))

        fig_errors.update_layout(
            title=f"Error Rate (Last {time_window} minutes)",
            yaxis=dict(title="Count"),
            yaxis2=dict(title="Error Rate (%)", overlaying="y", side="right"),
            hovermode="x unified"
        )

        st.plotly_chart(fig_errors, use_container_width=True)
    else:
        st.info("No error data available yet")

    st.divider()

    # Latency stats
    st.header("ñ Latency Statistics")
    latency_stats = metrics.get_latency_stats()

    if latency_stats and latency_stats.get("count", 0) > 0:
        col1, col2 = st.columns(2)

        with col1:
            # Latency percentiles
            percentiles_data = {
                "Metric": ["Minimum", "Average", "P50", "P95", "P99", "Maximum"],
                "Latency (ms)": [
                    latency_stats.get("min", 0),
                    latency_stats.get("avg", 0),
                    latency_stats.get("p50", 0),
                    latency_stats.get("p95", 0),
                    latency_stats.get("p99", 0),
                    latency_stats.get("max", 0)
                ]
            }
            df_percentiles = pd.DataFrame(percentiles_data)

            fig_latency = px.bar(
                df_percentiles,
                x="Metric",
                y="Latency (ms)",
                title="Latency Percentiles",
                color="Latency (ms)",
                color_continuous_scale="RdYlGn_r"
            )
            st.plotly_chart(fig_latency, use_container_width=True)

        with col2:
            # SLA compliance
            p95 = latency_stats.get("p95", 0)
            sla_target = 2000  # 2 seconds

            if p95 < sla_target:
                sla_status = " SLA Compliant"
                sla_color = "success"
            else:
                sla_status = "  SLA Violation"
                sla_color = "error"

            st.markdown(f"""
            <div class="metric-card">
                <h3 class="{sla_color}">{sla_status}</h3>
                <p>P95 Latency: <strong>{p95:.0f}ms</strong></p>
                <p>SLA Target: <strong>{sla_target}ms</strong></p>
                <p>Sample Size: <strong>{latency_stats.get('count', 0)}</strong></p>
            </div>
            """, unsafe_allow_html=True)

    else:
        st.info("No latency data available yet")

    st.divider()

    # Agent performance
    st.header("> Agent Performance")
    agent_perf = metrics.get_agent_performance()

    if agent_perf:
        df_agents = pd.DataFrame(agent_perf)

        col1, col2 = st.columns(2)

        with col1:
            # Calls per agent
            fig_agent_calls = px.bar(
                df_agents,
                x="agent_name",
                y="total_calls",
                title="Agent Call Volume",
                labels={"total_calls": "Total Calls", "agent_name": "Agent"},
                color="total_calls",
                color_continuous_scale="Blues"
            )
            st.plotly_chart(fig_agent_calls, use_container_width=True)

        with col2:
            # Success rate per agent
            fig_success_rate = px.bar(
                df_agents,
                x="agent_name",
                y="success_rate",
                title="Agent Success Rate",
                labels={"success_rate": "Success Rate (%)", "agent_name": "Agent"},
                color="success_rate",
                color_continuous_scale="RdYlGn",
                range_y=[0, 100]
            )
            st.plotly_chart(fig_success_rate, use_container_width=True)

        # Agent details table
        st.subheader("Agent Details")
        df_agents_display = df_agents[[
            "agent_name",
            "total_calls",
            "successful_calls",
            "failed_calls",
            "success_rate",
            "avg_latency_ms"
        ]].copy()

        df_agents_display["success_rate"] = df_agents_display["success_rate"].apply(
            lambda x: f"{x:.1f}%"
        )
        df_agents_display["avg_latency_ms"] = df_agents_display["avg_latency_ms"].apply(
            lambda x: f"{x:.0f}ms"
        )

        df_agents_display.columns = [
            "Agent Name",
            "Total Calls",
            "Successful",
            "Failed",
            "Success Rate",
            "Avg Latency"
        ]

        st.dataframe(df_agents_display, use_container_width=True)

    else:
        st.info("No agent performance data available yet")

    st.divider()

    # Database health
    st.header("=¾ Database Health")
    db_health = metrics.get_db_health()

    if db_health and db_health.get("total_operations", 0) > 0:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="Total Operations",
                value=db_health.get("total_operations", 0)
            )

        with col2:
            error_rate = db_health.get("error_rate", 0)
            st.metric(
                label="Error Rate",
                value=f"{error_rate:.2f}%",
                delta="Normal" if error_rate < 1 else "High"
            )

        with col3:
            st.metric(
                label="Avg Query Latency",
                value=f"{db_health.get('avg_latency_ms', 0):.0f}ms"
            )

        # Operations by type
        ops_by_type = db_health.get("operations_by_type", {})
        if ops_by_type:
            df_ops = pd.DataFrame([
                {"Operation": k, "Count": v}
                for k, v in ops_by_type.items()
            ])

            fig_ops = px.pie(
                df_ops,
                values="Count",
                names="Operation",
                title="Operations by Type"
            )
            st.plotly_chart(fig_ops, use_container_width=True)

    else:
        st.info("No database health data available yet")

    # Footer
    st.divider()
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# Run main dashboard
main()

# Auto-refresh
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
