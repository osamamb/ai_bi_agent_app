"""
AI BI Agent - LangChain Version
A Databricks Streamlit app with LangChain agents for:
1. Genie Chatbot - Natural language queries using LangChain agents
2. Analytics Dashboard - Visual insights from campaigns, orders, and customer data
3. Databricks Dashboard - Embedded Databricks dashboard iframe
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
import os
import numpy as np

from typing import Optional, List, Dict, Any

# LangChain imports
from langchain_agents import BusinessIntelligenceAgent, VisualizationAgent
from langchain_tools import GenieQueryTool, ResponseEnhancementTool, SQLQueryTool

# Databricks imports (conditional for local development)
try:
    from databricks import sql
    DATABRICKS_AVAILABLE = True
except ImportError:
    DATABRICKS_AVAILABLE = False
    sql = None

# Enterprise styling configuration
ENTERPRISE_COLORS = {
    'primary': '#132257',      # Deep Blue
    'secondary': '#00A9CE',    # Cyan
    'accent': '#E20074',       # Magenta
    'success': '#00B04F',      # Professional Green
    'warning': '#FF6900',      # Professional Orange
    'error': '#D32F2F',        # Professional Red
    'neutral': '#4A4A4A',      # Professional Gray
    'background': '#FFFFFF',   # Clean White
    'light_gray': '#F5F5F5',   # Light Background
    'border': '#E0E0E0'        # Subtle Borders
}

ENTERPRISE_STYLE = {
    'font_family': '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
    'title_size': 24,
    'subtitle_size': 18,
    'grid_color': '#E0E0E0',
    'paper_bgcolor': '#FFFFFF',
    'plot_bgcolor': '#FFFFFF',
    'card_shadow': '0 2px 8px rgba(0,0,0,0.1)',
    'border_radius': '8px'
}

def apply_enterprise_styling(fig, title, chart_type):
    """Apply enterprise styling to Plotly figures"""
    
    # Color palette based on chart type
    if chart_type in ['bar', 'column']:
        colors = [ENTERPRISE_COLORS['primary']]
    elif chart_type == 'line':
        colors = [ENTERPRISE_COLORS['primary'], ENTERPRISE_COLORS['secondary']]
    elif chart_type == 'pie':
        colors = [ENTERPRISE_COLORS['primary'], ENTERPRISE_COLORS['secondary'], 
                 ENTERPRISE_COLORS['accent'], ENTERPRISE_COLORS['success'], 
                 ENTERPRISE_COLORS['neutral']]
    elif chart_type == 'scatter':
        colors = [ENTERPRISE_COLORS['secondary']]
    elif chart_type == 'heatmap':
        colors = [ENTERPRISE_COLORS['primary'], '#ffffff', ENTERPRISE_COLORS['accent']]
    else:
        colors = [ENTERPRISE_COLORS['primary']]
    
    # Update layout with enterprise styling
    fig.update_layout(
        title={
            'text': title,
            'font': {
                'family': ENTERPRISE_STYLE['font_family'],
                'size': ENTERPRISE_STYLE['title_size'],
                'color': ENTERPRISE_COLORS['neutral'],
                'weight': 600
            },
            'x': 0.02,
            'xanchor': 'left'
        },
        font={
            'family': ENTERPRISE_STYLE['font_family'],
            'color': ENTERPRISE_COLORS['neutral'],
            'size': 12
        },
        paper_bgcolor=ENTERPRISE_STYLE['paper_bgcolor'],
        plot_bgcolor=ENTERPRISE_STYLE['plot_bgcolor'],
        margin=dict(t=80, l=60, r=40, b=60),
        showlegend=True if chart_type in ['pie', 'line'] else False
    )
    
    # Update axes styling
    if chart_type not in ['pie', 'treemap', 'heatmap']:
        fig.update_xaxes(
            gridcolor=ENTERPRISE_STYLE['grid_color'],
            linecolor=ENTERPRISE_COLORS['border'],
            tickcolor=ENTERPRISE_COLORS['neutral'],
            tickfont=dict(size=11, color=ENTERPRISE_COLORS['neutral'])
        )
        fig.update_yaxes(
            gridcolor=ENTERPRISE_STYLE['grid_color'],
            linecolor=ENTERPRISE_COLORS['border'],
            tickcolor=ENTERPRISE_COLORS['neutral'],
            tickfont=dict(size=11, color=ENTERPRISE_COLORS['neutral'])
        )
    
    # Apply colors to traces
    if hasattr(fig, 'data') and fig.data:
        for i, trace in enumerate(fig.data):
            if hasattr(trace, 'marker'):
                if chart_type == 'bar':
                    trace.marker.color = colors[0]
                elif chart_type == 'scatter':
                    trace.marker.color = colors[0]
                    trace.marker.size = 8
                elif chart_type == 'line':
                    trace.line.color = colors[i % len(colors)]
                    trace.line.width = 3
    
    return fig

# Configure Streamlit page
st.set_page_config(
    page_title="AI BI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ensure environment variables are set correctly (only when Databricks is available)
if DATABRICKS_AVAILABLE:
    # Only assert these in Databricks environments
    if not os.getenv('DATABRICKS_WAREHOUSE_ID'):
        st.error("⚠️ DATABRICKS_WAREHOUSE_ID must be set in app.yaml for Databricks functionality.")
    if not os.getenv('DATABRICKS_HOST'):
        st.error("⚠️ DATABRICKS_HOST must be set in app.yaml for Databricks functionality.")
    if not os.getenv('DATABRICKS_TOKEN'):
        st.error("⚠️ DATABRICKS_TOKEN must be set in app.yaml for Databricks functionality.")
else:
    # Local development mode
    st.info("🏠 Running in local development mode - Databricks features will use mock data.")

# Configuration - use only PAT authentication to avoid OAuth conflicts
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "")
DATABRICKS_WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "")
GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID", "") or os.getenv("DATABRICKS_GENIE_SPACE_ID", "")
DATABRICKS_DASHBOARD_URL = os.getenv("DATABRICKS_DASHBOARD_URL", "")

# Serving endpoint configuration
DATABRICKS_SERVING_ENDPOINT_NAME = os.getenv("DATABRICKS_SERVING_ENDPOINT_NAME", "")
ENABLE_RESPONSE_ENHANCEMENT = os.getenv("ENABLE_RESPONSE_ENHANCEMENT", "true").lower() == "true"

# Query the SQL warehouse with PAT authentication
def sql_query_with_pat(query: str) -> pd.DataFrame:
    """Execute a SQL query and return the result as a pandas DataFrame using PAT authentication."""
    if not DATABRICKS_AVAILABLE:
        # Return empty DataFrame for local development
        st.warning("Databricks SQL not available in local environment. Using mock data for testing.")
        return pd.DataFrame()
    
    with sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=f"/sql/1.0/warehouses/{DATABRICKS_WAREHOUSE_ID}",
        access_token=DATABRICKS_TOKEN
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall_arrow().to_pandas()


def create_mock_business_data():
    """Create mock business data for local testing"""
    np.random.seed(42)
    
    # Business units and products
    business_units = ['Consumer Mobile', 'Enterprise', 'NBN', 'International', 'Digital Services']
    products = ['Mobile Plans', 'Broadband', 'Cloud Services', 'IoT Solutions', 'Digital TV']
    states = ['NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'NT', 'ACT']
    campaigns = ['Summer Sale', 'Business Connect', 'Family Bundle', 'Enterprise Plus', 'Digital First']
    channels = ['Online', 'Retail Store', 'Call Center', 'Partner', 'Direct Sales']
    age_bands = ['18-25', '26-35', '36-45', '46-55', '56-65', '65+']
    tenure_bands = ['0-1 years', '1-3 years', '3-5 years', '5-10 years', '10+ years']
    
    # Generate 1000 sample records
    n_records = 1000
    
    data = {
        'ORDER_NO': [f'ORD{i:06d}' for i in range(1, n_records + 1)],
        'SERVICE_NO': [f'SVC{i:06d}' for i in range(1, n_records + 1)],
        'CAC': [f'CAC{i:06d}' for i in range(1, n_records + 1)],
        'Sales': np.random.lognormal(8, 1, n_records).round(2),
        'Business_Unit_Name': np.random.choice(business_units, n_records),
        'Sales_Product': np.random.choice(products, n_records),
        'State': np.random.choice(states, n_records),
        'CalendarDate': pd.date_range('2023-01-01', periods=n_records, freq='D')[:n_records],
        'Campaign_Name': np.random.choice(campaigns, n_records),
        'Campaign_Channel': np.random.choice(channels, n_records),
        'Customer_Age_Band': np.random.choice(age_bands, n_records),
        'Customer_Tenure_Band': np.random.choice(tenure_bands, n_records),
        'Gender': np.random.choice(['M', 'F'], n_records),
        'Loyalty_Status': np.random.choice(['Active', 'Inactive'], n_records, p=[0.7, 0.3])
    }
    
    return pd.DataFrame(data)


def get_business_data():
    """Get business data from Databricks or return mock data for local testing"""
    if not DATABRICKS_AVAILABLE:
        return create_mock_business_data()
    
    try:
        # Query to get comprehensive business data
        query = """
        SELECT 
            o.ORDER_NO,
            o.SERVICE_NO,
            o.CAC,
            o.Sales,
            o.Business_Unit_Name,
            o.Sales_Product,
            o.State,
            o.CalendarDate,
            c.campaignname as Campaign_Name,
            c.campaign_channel as Campaign_Channel,
            uc.Cstmr_Age_Bnd as Customer_Age_Band,
            uc.Cstmr_Tenure_Bnd as Customer_Tenure_Band,
            uc.Gndr_Cd as Gender,
            uc.Loyalty_Status as Loyalty_Status
        FROM aiops_app_catalog.c809384.orders o
        LEFT JOIN aiops_app_catalog.c809384.campaigns c ON o.CAC = c.CAC
        LEFT JOIN aiops_app_catalog.c809384.unique_customers uc ON o.CAC = uc.CAC
        WHERE o.CalendarDate >= '2023-01-01'
        LIMIT 1000
        """
        
        return sql_query_with_pat(query)
    except Exception as e:
        st.warning(f"Could not fetch data from Databricks: {str(e)}. Using mock data.")
        return create_mock_business_data()


def create_visualization_from_dataframe(df, query="", description="", chart_type=None):
    """Create AI-selected visualization from DataFrame using LangChain agent"""
    if df is None or df.empty:
        return None, "No data available for visualization", []
    
    # Initialize visualization agent
    viz_agent = VisualizationAgent()
    
    # Get visualization suggestion
    viz_suggestion = viz_agent.suggest_visualization(df, query, description)
    
    chart_type = chart_type or viz_suggestion.get("chart_type", "bar")
    reasoning = viz_suggestion.get("reasoning", "Chart selected based on data characteristics")
    insights = viz_suggestion.get("insights", [])
    
    numeric_cols = viz_suggestion.get("numeric_columns", [])
    categorical_cols = viz_suggestion.get("categorical_columns", [])
    datetime_cols = viz_suggestion.get("datetime_columns", [])
    
    try:
        fig = None
        
        if chart_type == "bar" and categorical_cols and numeric_cols:
            # Bar chart
            df_grouped = df.groupby(categorical_cols[0])[numeric_cols[0]].sum().reset_index()
            df_grouped = df_grouped.sort_values(numeric_cols[0], ascending=False).head(10)
            
            fig = px.bar(
                df_grouped, 
                x=categorical_cols[0], 
                y=numeric_cols[0],
                title=f"{numeric_cols[0]} by {categorical_cols[0]}"
            )
            
        elif chart_type == "line" and datetime_cols and numeric_cols:
            # Line chart for time series
            df_time = df.groupby(datetime_cols[0])[numeric_cols[0]].sum().reset_index()
            
            fig = px.line(
                df_time, 
                x=datetime_cols[0], 
                y=numeric_cols[0],
                title=f"{numeric_cols[0]} Over Time"
            )
            
        elif chart_type == "scatter" and len(numeric_cols) >= 2:
            # Scatter plot
            fig = px.scatter(
                df, 
                x=numeric_cols[0], 
                y=numeric_cols[1],
                title=f"{numeric_cols[1]} vs {numeric_cols[0]}"
            )
            
        elif chart_type == "histogram" and numeric_cols:
            # Histogram
            fig = px.histogram(
                df, 
                x=numeric_cols[0],
                title=f"Distribution of {numeric_cols[0]}"
            )
            
        else:
            # Default to bar chart if we have categorical and numeric data
            if categorical_cols and numeric_cols:
                df_grouped = df.groupby(categorical_cols[0])[numeric_cols[0]].sum().reset_index()
                df_grouped = df_grouped.sort_values(numeric_cols[0], ascending=False).head(10)
                
                fig = px.bar(
                    df_grouped, 
                    x=categorical_cols[0], 
                    y=numeric_cols[0],
                    title=f"{numeric_cols[0]} by {categorical_cols[0]}"
                )
        
        if fig:
            fig = apply_enterprise_styling(fig, fig.layout.title.text, chart_type)
            
        return fig, reasoning, insights
        
    except Exception as e:
        return None, f"Error creating visualization: {str(e)}", []


def create_analytics_tab():
    """Create the analytics dashboard tab with the same visualizations as original"""
    st.header("📊 Business Intelligence Analytics")
    
    # Get business data
    with st.spinner("Loading business data..."):
        df = get_business_data()
    
    if df.empty:
        st.warning("No data available for analytics")
        return
    
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sales = df['Sales'].sum()
        st.metric("Total Sales", f"${total_sales:,.0f}")
    
    with col2:
        total_orders = len(df)
        st.metric("Total Orders", f"{total_orders:,}")
    
    with col3:
        avg_order_value = df['Sales'].mean()
        st.metric("Avg Order Value", f"${avg_order_value:,.0f}")
    
    with col4:
        unique_customers = df['CAC'].nunique()
        st.metric("Unique Customers", f"{unique_customers:,}")
    
    st.divider()
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Sales by Business Unit
        if 'Business_Unit_Name' in df.columns and 'Sales' in df.columns:
            fig1, reason1, _ = create_visualization_from_dataframe(
                df, 
                "sales by business unit", 
                "Business unit performance analysis",
                "bar"
            )
            if fig1:
                st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Sales by State
        if 'State' in df.columns and 'Sales' in df.columns:
            fig2, reason2, _ = create_visualization_from_dataframe(
                df, 
                "sales by state", 
                "Geographic sales distribution",
                "bar"
            )
            if fig2:
                st.plotly_chart(fig2, use_container_width=True)
    
    # Additional visualizations
    col3, col4 = st.columns(2)
    
    with col3:
        # Campaign Performance
        if 'Campaign_Channel' in df.columns and 'Sales' in df.columns:
            fig3, _, _ = create_visualization_from_dataframe(
                df, 
                "sales by campaign channel", 
                "Campaign channel effectiveness",
                "bar"
            )
            if fig3:
                st.plotly_chart(fig3, use_container_width=True)
    
    with col4:
        # Customer Demographics
        if 'Customer_Age_Band' in df.columns and 'Sales' in df.columns:
            fig4, _, _ = create_visualization_from_dataframe(
                df, 
                "sales by age band", 
                "Customer age demographics",
                "bar"
            )
            if fig4:
                st.plotly_chart(fig4, use_container_width=True)


def create_genie_chatbot_tab():
    """Create the Genie chatbot interface tab using LangChain agents"""
    st.header("🤖 AI BI Agent (LangChain)")
    
    # Configuration check
    config_issues = []
    if not DATABRICKS_HOST:
        config_issues.append("○ DATABRICKS_HOST not set")
    if not DATABRICKS_TOKEN:
        config_issues.append("○ DATABRICKS_TOKEN not set")
    if not GENIE_SPACE_ID:
        config_issues.append("○ GENIE_SPACE_ID not set")
    
    if config_issues:
        st.error("**Configuration Required**: This chatbot requires proper configuration.")
        st.write("Missing configuration:")
        for issue in config_issues:
            st.write(issue)
        st.write("""
        Please set the following environment variables in your `app.yaml`:
        - `DATABRICKS_HOST`: Your Databricks workspace URL
        - `DATABRICKS_TOKEN`: Your personal access token
        - `GENIE_SPACE_ID`: Your Genie space ID for business intelligence dataset
        """)
        return
    
    # Show configuration status
    with st.expander("🔧 Configuration Status", expanded=False):
        st.write("**Current Configuration:**")
        st.write(f"**DATABRICKS_HOST:** {DATABRICKS_HOST}")
        st.write(f"**GENIE_SPACE_ID:** {GENIE_SPACE_ID[:8] + '...' if GENIE_SPACE_ID else 'Not set'}")
        st.write(f"**DATABRICKS_SERVING_ENDPOINT_NAME:** {DATABRICKS_SERVING_ENDPOINT_NAME or 'Not set'}")
        
        if DATABRICKS_SERVING_ENDPOINT_NAME:
            st.success("🔗 LangChain agent with LLM enhancement enabled")
        else:
            st.info("💡 LangChain agent running with mock LLM (configure serving endpoint for full LLM capabilities)")
    
    # Initialize LangChain Business Intelligence Agent
    try:
        if not DATABRICKS_TOKEN:
            st.error("DATABRICKS_TOKEN is required for the BI Agent.")
            return
        
        # Initialize the agent
        if 'bi_agent' not in st.session_state:
            with st.spinner("🤖 Initializing LangChain BI Agent..."):
                st.session_state.bi_agent = BusinessIntelligenceAgent(
                    databricks_host=DATABRICKS_HOST,
                    databricks_token=DATABRICKS_TOKEN,
                    genie_space_id=GENIE_SPACE_ID,
                    warehouse_id=DATABRICKS_WAREHOUSE_ID,
                    serving_endpoint_name=DATABRICKS_SERVING_ENDPOINT_NAME
                )
                st.success("✅ LangChain BI Agent initialized successfully!")
        
        bi_agent = st.session_state.bi_agent
        
    except Exception as e:
        st.error(f"Unable to initialize LangChain BI Agent: {str(e)}")
        st.info("Please verify your configuration is correct.")
        return
    
    # Chat interface
    st.subheader("💬 Chat with AI BI Agent")
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'conversation_id' not in st.session_state:
        st.session_state.conversation_id = None
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Display dataframe if available
            if message.get("dataframe") is not None:
                with st.expander("📋 Data Table View", expanded=False):
                    st.dataframe(message["dataframe"], use_container_width=True)
                    st.write(f"*Showing {len(message['dataframe'])} rows × {len(message['dataframe'].columns)} columns*")
            
            # Display visualization if available
            if message.get("visualization") is not None:
                st.plotly_chart(message["visualization"], use_container_width=True)
                
                if message.get("viz_reasoning"):
                    with st.expander("🤖 AI Chart Selection Reasoning", expanded=False):
                        st.write(message["viz_reasoning"])
                        if message.get("viz_insights"):
                            st.write("**Key Insights:**")
                            for insight in message["viz_insights"]:
                                st.write(f"• {insight}")
    
    # Chat input
    if user_input := st.chat_input("Ask me about business data..."):
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Get response from LangChain agent
        with st.chat_message("assistant"):
            with st.spinner("🤖 LangChain Agent is analyzing your query..."):
                try:
                    # Query the agent
                    if st.session_state.conversation_id:
                        result = bi_agent.continue_conversation(user_input, st.session_state.conversation_id)
                    else:
                        result = bi_agent.query(user_input)
                    
                    if result["success"]:
                        # Store conversation ID
                        if result.get("conversation_id"):
                            st.session_state.conversation_id = result["conversation_id"]
                        
                        # Display response
                        response = result["response"]
                        st.markdown(response)
                        
                        # Prepare message for history
                        message_data = {
                            "role": "assistant", 
                            "content": response,
                            "dataframe": result.get("dataframe"),
                            "sql_query": result.get("sql_query")
                        }
                        
                        # Create visualization if dataframe is available
                        if result.get("dataframe") is not None:
                            df = result["dataframe"]
                            
                            # Display data table
                            with st.expander("📋 Data Table View", expanded=False):
                                st.dataframe(df, use_container_width=True)
                                st.write(f"*Showing {len(df)} rows × {len(df.columns)} columns*")
                            
                            # Create AI-selected visualization
                            with st.spinner("🎨 Creating AI-selected visualization..."):
                                fig, reasoning, insights = create_visualization_from_dataframe(
                                    df, user_input, response
                                )
                                
                                if fig:
                                    st.write("**📊 AI-Selected Visualization:**")
                                    st.plotly_chart(fig, use_container_width=True)
                                    
                                    # Show AI reasoning
                                    with st.expander("🤖 AI Chart Selection Reasoning", expanded=False):
                                        st.write(reasoning)
                                        if insights:
                                            st.write("**Key Insights:**")
                                            for insight in insights:
                                                st.write(f"• {insight}")
                                    
                                    # Add visualization to message data
                                    message_data["visualization"] = fig
                                    message_data["viz_reasoning"] = reasoning
                                    message_data["viz_insights"] = insights
                        
                        # Add assistant message to chat history
                        st.session_state.chat_history.append(message_data)
                        
                    else:
                        error_message = result["response"]
                        st.error(f"Agent Error: {error_message}")
                        
                        # Add error to chat history
                        st.session_state.chat_history.append({
                            "role": "assistant", 
                            "content": f"❌ Error: {error_message}"
                        })
                
                except Exception as e:
                    error_msg = f"Unexpected error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_history.append({
                        "role": "assistant", 
                        "content": f"❌ {error_msg}"
                    })
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.session_state.conversation_id = None
        st.rerun()
    
    # Sample questions
    st.subheader("💡 Sample Questions")
    sample_questions = [
        "What are the top performing business units by sales?",
        "Show me sales trends by quarter",
        "Which campaign channels generate the most revenue?",
        "What's the customer distribution by age band?",
        "How do sales vary by state?",
        "What's the average order value by product category?",
        "Show me customer tenure analysis",
        "Which products have the highest sales volume?"
    ]
    
    for question in sample_questions:
        if st.button(f"💬 {question}", key=f"sample_{hash(question)}"):
            # Simulate clicking the question
            st.session_state.sample_question = question
            st.rerun()


def create_dashboard_tab():
    """Create the embedded Databricks dashboard tab"""
    st.header("📈 Databricks Dashboard")
    
    if DATABRICKS_DASHBOARD_URL:
        st.components.v1.iframe(
            DATABRICKS_DASHBOARD_URL,
            height=800,
            scrolling=True
        )
    else:
        st.info("Dashboard URL not configured. Please set DATABRICKS_DASHBOARD_URL in your app.yaml file.")
        
        st.write("**To configure the dashboard:**")
        st.write("1. Create or find your dashboard in Databricks SQL")
        st.write("2. Get the embed URL from the dashboard sharing options")
        st.write("3. Set the DATABRICKS_DASHBOARD_URL environment variable in app.yaml")


def main():
    """Main application function"""
    
    # Custom CSS for enterprise styling
    st.markdown(f"""
    <style>
        .main-header {{
            color: {ENTERPRISE_COLORS['primary']};
            font-family: {ENTERPRISE_STYLE['font_family']};
            font-weight: 600;
            border-bottom: 3px solid {ENTERPRISE_COLORS['secondary']};
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: {ENTERPRISE_COLORS['background']};
            padding: 20px;
            border-radius: {ENTERPRISE_STYLE['border_radius']};
            box-shadow: {ENTERPRISE_STYLE['card_shadow']};
            border-left: 4px solid {ENTERPRISE_COLORS['primary']};
        }}
        
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background-color: {ENTERPRISE_COLORS['light_gray']};
            border-radius: 8px 8px 0 0;
            padding: 10px 20px;
            font-weight: 500;
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: {ENTERPRISE_COLORS['primary']};
            color: white;
        }}
    </style>
    """, unsafe_allow_html=True)
    
    # Main title
    st.markdown('<h1 class="main-header">🤖 AI BI Agent (LangChain)</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    Explore business intelligence data through interactive analytics and natural language queries powered by **LangChain agents** and Databricks Genie.
    """)
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["🤖 AI BI Agent", "📊 Analytics Dashboard", "📈 Databricks Dashboard"])
    
    with tab1:
        create_genie_chatbot_tab()
    
    with tab2:
        create_analytics_tab()
    
    with tab3:
        create_dashboard_tab()
    
    # Sidebar with information
    with st.sidebar:
        st.header("🤖 AI BI Agent Features")
        
        st.markdown("""
        **🤖 AI BI Agent (LangChain)**
        - Powered by LangChain agents and tools
        - Natural language business intelligence queries
        - AI-enhanced responses via serving endpoints
        - Intelligent tool selection and orchestration
        
        **📊 Analytics Dashboard**
        - Interactive Plotly visualizations
        - Key business metrics and KPIs
        - Enterprise-styled charts
        
        **📈 Databricks Dashboard**
        - Embedded Databricks SQL dashboard
        - Real-time business intelligence
        """)
        
        st.divider()
        
        st.subheader("🎯 Try asking the AI Agent:")
        st.markdown("""
        - "What are the top performing business units?"
        - "Show me sales trends over time"
        - "Which campaigns are most effective?"
        - "Analyze customer demographics"
        - "Compare product performance"
        """)
        
        st.divider()
        
        # Configuration status
        st.subheader("⚙️ Configuration Status")
        config_status = []
        
        if DATABRICKS_HOST and DATABRICKS_TOKEN:
            config_status.append("● Databricks connection configured")
        else:
            config_status.append("○ Databricks connection not configured")
        
        if GENIE_SPACE_ID:
            config_status.append("● Genie API configured")
        else:
            config_status.append("○ Genie API not configured")
        
        if DATABRICKS_AVAILABLE:
            if DATABRICKS_SERVING_ENDPOINT_NAME:
                config_status.append(f"● LangChain LLM configured (`{DATABRICKS_SERVING_ENDPOINT_NAME}`)")
            else:
                config_status.append("◐ LangChain with mock LLM (needs serving_endpoint resource)")
        else:
            config_status.append("○ Running in local development mode")
        
        for status in config_status:
            st.write(status)
        
        if DATABRICKS_SERVING_ENDPOINT_NAME:
            st.success("🚀 Full LangChain agent capabilities enabled!")


if __name__ == "__main__":
    main()
