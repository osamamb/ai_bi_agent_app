# AI BI Telstra Agent - LangChain Version

A Databricks Streamlit app that combines interactive business intelligence analytics with natural language querying capabilities using **LangChain agents** and Databricks Genie.

## 🆕 What's New in the LangChain Version

This version reimplements the original Brett AI BI App using **LangChain framework** for enhanced agent capabilities:

### 🤖 LangChain Agent Architecture

- **BusinessIntelligenceAgent**: Main agent that orchestrates business intelligence queries
- **VisualizationAgent**: Specialized agent for creating intelligent data visualizations
- **Custom LangChain Tools**:
  - `GenieQueryTool`: Natural language queries to Databricks Genie
  - `ResponseEnhancementTool`: LLM-powered response enhancement
  - `SQLQueryTool`: Direct SQL query execution

### 🔧 Key Improvements

1. **Agent-Based Architecture**: Uses LangChain's ReAct agent pattern for intelligent tool selection
2. **Tool Orchestration**: Agents automatically decide which tools to use based on user queries
3. **Enhanced Error Handling**: Better error recovery and fallback mechanisms
4. **Modular Design**: Separated tools and agents for better maintainability
5. **Mock LLM Support**: Graceful fallback when serving endpoints aren't available

## Features

### 🤖 AI BI Agent Tab (LangChain-Powered)
- Natural language queries on business intelligence dataset
- **LangChain ReAct Agent** with intelligent tool selection
- **Custom LangChain Tools** for Databricks integration
- AI-Enhanced Responses via Databricks Model Serving endpoints
- Intelligent visualization selection using VisualizationAgent
- Ask questions like:
  - "What are the top performing business units by sales?"
  - "Show me sales trends by quarter"
  - "Which campaign channels generate the most revenue?"
  - "What's the customer distribution by age band?"

### 📊 Analytics Dashboard Tab
- Interactive visualizations using Plotly
- Key business metrics and KPIs
- Multiple chart types with AI-powered selection
- Enterprise Telstra-inspired styling

### 📈 Databricks Dashboard Tab
- Embedded Databricks dashboard
- Comprehensive data analytics
- Real-time dashboard view

## Architecture Comparison

### Original Version
```
User Input → Direct API Calls → Genie API → Response Enhancement → UI Display
```

### LangChain Version
```
User Input → LangChain Agent → Tool Selection → Tool Execution → Response → UI Display
                ↓
        [GenieQueryTool, SQLQueryTool, ResponseEnhancementTool]
```

## Prerequisites

1. **Databricks Workspace** with Unity Catalog enabled
2. **Business Intelligence Dataset** accessible in aiops_app_catalog.c809384 schema
3. **Genie Space** configured for the business intelligence dataset
4. **SQL Warehouse** (Pro or Serverless) with CAN USE permissions
5. **Databricks Assistant** enabled in your workspace
6. **Model Serving Endpoint** (Optional) - For AI-enhanced responses

## Setup Instructions

### 1. Install Dependencies

The LangChain version requires additional dependencies:

```bash
pip install -r requirements.txt
```

Key new dependencies:
- `langchain>=0.1.0`
- `langchain-community>=0.0.20`
- `langchain-core>=0.1.0`
- `langchain-experimental>=0.0.50`
- `pydantic>=2.0.0`

### 2. Configure Environment Variables

Update the following environment variables in `app.yaml`:

```yaml
env:
  - name: "DATABRICKS_HOST"
    value: "https://your-workspace.azuredatabricks.net"
  - name: "DATABRICKS_TOKEN"
    value: "your-personal-access-token"
  - name: "GENIE_SPACE_ID"
    value: "your-genie-space-id"
  - name: "DATABRICKS_SERVING_ENDPOINT_NAME"
    value: "your-llm-endpoint-name"  # Optional but recommended
  - name: "ENABLE_RESPONSE_ENHANCEMENT"
    value: "true"
  
  # Optional: LangChain tracing
  - name: "LANGCHAIN_TRACING_V2"
    value: "false"  # Set to true to enable LangSmith tracing
  - name: "LANGCHAIN_API_KEY"
    value: ""  # LangSmith API key for tracing
```

### 3. Deploy to Databricks Apps

#### Option A: Using Databricks UI

1. In your Databricks workspace, go to **Apps**
2. Click **Create App**
3. Upload the app files (`app.py`, `langchain_agents.py`, `langchain_tools.py`, `requirements.txt`, `app.yaml`)
4. Configure environment variables
5. Deploy the app

#### Option B: Using Databricks CLI

```bash
# Install Databricks CLI
pip install databricks-cli

# Configure authentication
databricks configure --token

# Deploy the app
databricks apps create --source-dir . --app-name ai-bi-telstra-agent
```

## File Structure

```
ai_bi_telstra_agent/
├── app.py                 # Main Streamlit application with LangChain integration
├── langchain_agents.py    # LangChain agents (BusinessIntelligenceAgent, VisualizationAgent)
├── langchain_tools.py     # LangChain tools (GenieQueryTool, ResponseEnhancementTool, SQLQueryTool)
├── requirements.txt       # Python dependencies including LangChain
├── app.yaml              # App configuration
└── README.md             # This file
```

## Usage

### AI BI Agent Tab (LangChain)
1. Select the "🤖 AI BI Agent" tab
2. Type natural language questions about business data
3. The LangChain agent will automatically:
   - Select appropriate tools (Genie, SQL, Enhancement)
   - Execute queries in the right sequence
   - Enhance responses if LLM endpoint is available
   - Create intelligent visualizations

### Agent Workflow Example

```
User: "What are the top performing business units by sales?"

LangChain Agent Reasoning:
1. Thought: I need to query business data about sales by business unit
2. Action: Use genie_query tool with natural language query
3. Observation: Got response with sales data
4. Thought: I should enhance this response for better business insights
5. Action: Use enhance_response tool
6. Observation: Got enhanced business-friendly response
7. Final Answer: Enhanced response with actionable insights
```

## LangChain Components

### BusinessIntelligenceAgent
- **Purpose**: Main orchestration agent for BI queries
- **Tools**: GenieQueryTool, SQLQueryTool, ResponseEnhancementTool
- **LLM**: Databricks serving endpoint or MockLLM fallback
- **Pattern**: ReAct (Reasoning + Acting)

### VisualizationAgent
- **Purpose**: Intelligent chart selection and insights
- **Capabilities**: Analyzes data characteristics and query context
- **Output**: Chart type, reasoning, and key insights

### Custom Tools

#### GenieQueryTool
```python
# Natural language queries to Genie
result = genie_tool._run("What are the top sales by business unit?")
```

#### ResponseEnhancementTool
```python
# Enhance responses using LLM
enhanced = enhancement_tool._run(
    original_response="Raw genie response",
    sql_query="SELECT * FROM orders",
    query_results="Query results data"
)
```

#### SQLQueryTool
```python
# Direct SQL execution
result = sql_tool._run("SELECT business_unit, SUM(sales) FROM orders GROUP BY business_unit")
```

## Sample Questions for the AI Agent

- "What are the top performing business units by sales?"
- "Show me quarterly sales trends"
- "Which campaign channels generate the most revenue?"
- "What's the customer distribution by age band?"
- "How do sales vary by state?"
- "What's the average order value by product category?"
- "Show me customer tenure analysis"
- "Which products have the highest sales volume?"
- "How do sales patterns differ by gender?"
- "What's the correlation between campaign channels and sales performance?"

## Troubleshooting

### LangChain-Specific Issues

1. **Agent execution errors**
   - Check that all tools are properly initialized
   - Verify LLM endpoint is accessible
   - Review agent logs in Streamlit interface

2. **Tool execution failures**
   - Ensure Databricks credentials are correct
   - Check tool-specific error messages
   - Verify API endpoints are accessible

3. **Mock LLM fallback**
   - When no serving endpoint is configured, the app uses MockLLM
   - This provides basic functionality but limited reasoning
   - Configure a serving endpoint for full capabilities

### Performance Considerations

- **Agent Iterations**: Limited to 3 iterations to prevent infinite loops
- **Tool Timeouts**: 30-second timeout for API calls
- **Error Handling**: Graceful fallbacks for tool failures
- **Caching**: Session state used to cache agent instances

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (will use mock data and MockLLM)
streamlit run app.py
```

### Adding New Tools

1. Create tool class inheriting from `BaseTool`
2. Define input schema using Pydantic
3. Implement `_run` method
4. Add to agent's tool list

### Extending Agents

1. Modify agent prompts in `langchain_agents.py`
2. Add new tools to agent initialization
3. Update agent reasoning patterns as needed

## Contributing

To modify or extend this app:
1. Edit `langchain_agents.py` for agent behavior changes
2. Edit `langchain_tools.py` for new tools or tool modifications
3. Edit `app.py` for UI changes
4. Update `requirements.txt` for new dependencies
5. Test locally with Streamlit: `streamlit run app.py`

## References

- [LangChain Documentation](https://python.langchain.com/)
- [LangChain Agents](https://python.langchain.com/docs/modules/agents/)
- [LangChain Tools](https://python.langchain.com/docs/modules/agents/tools/)
- [Databricks App Templates](https://github.com/databricks/app-templates)
- [Databricks Genie Documentation](https://docs.databricks.com/en/genie/index.html)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Plotly Documentation](https://plotly.com/python/)
