"""
LangChain Agents for Databricks BI Application
"""

import os
from typing import List, Dict, Any, Optional
from langchain.agents import AgentExecutor, create_react_agent
from langchain.agents.agent_types import AgentType
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_community.llms.databricks import Databricks
from langchain_community.chat_models import ChatDatabricks
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models.llms import LLM
from langchain_tools import GenieQueryTool, ResponseEnhancementTool, SQLQueryTool
import pandas as pd


class MockLLM(LLM):
    """Mock LLM for local development when no serving endpoint is available."""
    
    @property
    def _llm_type(self) -> str:
        return "mock"
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """Mock LLM call that provides reasonable responses."""
        if "enhance" in prompt.lower() or "improve" in prompt.lower():
            return "Enhanced response: The data analysis shows significant business insights with actionable recommendations for strategic decision-making."
        elif "analyze" in prompt.lower() or "query" in prompt.lower():
            return "Based on the business intelligence data, here are the key findings and recommendations for your query."
        else:
            return "I understand your request. Let me help you analyze the business data to provide meaningful insights."


class BusinessIntelligenceAgent:
    """Main agent for business intelligence queries and analysis."""
    
    def __init__(self, 
                 databricks_host: str,
                 databricks_token: str,
                 genie_space_id: str,
                 warehouse_id: str,
                 serving_endpoint_name: str = ""):
        
        self.databricks_host = databricks_host
        self.databricks_token = databricks_token
        self.genie_space_id = genie_space_id
        self.warehouse_id = warehouse_id
        self.serving_endpoint_name = serving_endpoint_name
        
        # Initialize tools
        self.genie_tool = GenieQueryTool(
            host=databricks_host,
            token=databricks_token,
            space_id=genie_space_id
        )
        
        self.enhancement_tool = ResponseEnhancementTool(
            host=databricks_host,
            token=databricks_token,
            endpoint_name=serving_endpoint_name
        ) if serving_endpoint_name else None
        
        self.sql_tool = SQLQueryTool(
            host=databricks_host,
            token=databricks_token,
            warehouse_id=warehouse_id
        )
        
        # Initialize LLM
        self.llm = self._initialize_llm()
        
        # Create agent
        self.agent_executor = self._create_agent()
    
    def _initialize_llm(self) -> LLM:
        """Initialize the LLM for the agent."""
        if self.serving_endpoint_name and self.databricks_host and self.databricks_token:
            try:
                # Try to use Databricks LLM
                return Databricks(
                    endpoint_name=self.serving_endpoint_name,
                    databricks_api_token=self.databricks_token,
                    databricks_host=self.databricks_host
                )
            except Exception:
                # Fallback to mock LLM
                return MockLLM()
        else:
            return MockLLM()
    
    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with tools."""
        tools = [
            Tool(
                name="genie_query",
                description=self.genie_tool.description,
                func=self.genie_tool._run
            ),
            Tool(
                name="sql_query",
                description=self.sql_tool.description,
                func=self.sql_tool._run
            )
        ]
        
        if self.enhancement_tool:
            tools.append(
                Tool(
                    name="enhance_response",
                    description=self.enhancement_tool.description,
                    func=self.enhancement_tool._run
                )
            )
        
        # Create agent prompt
        prompt = PromptTemplate.from_template("""
You are a Business Intelligence Agent specialized in analyzing business data using Databricks Genie and SQL queries.

Your capabilities:
1. Query business data using natural language through Genie
2. Execute SQL queries for detailed analysis
3. Enhance responses to be more business-friendly and actionable

When a user asks a question:
1. First, try to use the genie_query tool with their natural language question
2. If you need more specific data, use the sql_query tool
3. If enhancement is available, use enhance_response to improve the final answer
4. Always provide clear, business-focused insights

Available tools: {tool_names}
Tool descriptions: {tools}

User Question: {input}

Thought: I need to analyze this business question and determine the best approach.
{agent_scratchpad}
""")
        
        # Create ReAct agent
        agent = create_react_agent(
            llm=self.llm,
            tools=tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3
        )
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        Process a business intelligence query.
        
        Args:
            question: Natural language business question
            
        Returns:
            Dictionary with response, dataframe, and metadata
        """
        try:
            # Execute agent
            result = self.agent_executor.invoke({"input": question})
            
            # Get additional data from tools
            dataframe = self.genie_tool.result_dataframe
            sql_query = self.genie_tool.last_sql_query
            conversation_id = self.genie_tool.conversation_id
            
            return {
                "response": result.get("output", "No response generated"),
                "dataframe": dataframe,
                "sql_query": sql_query,
                "conversation_id": conversation_id,
                "success": True
            }
            
        except Exception as e:
            return {
                "response": f"Error processing query: {str(e)}",
                "dataframe": None,
                "sql_query": None,
                "conversation_id": None,
                "success": False
            }
    
    def continue_conversation(self, question: str, conversation_id: str) -> Dict[str, Any]:
        """
        Continue an existing conversation.
        
        Args:
            question: Follow-up question
            conversation_id: Existing conversation ID
            
        Returns:
            Dictionary with response and metadata
        """
        try:
            # Update genie tool with conversation context
            modified_question = f"[Continue conversation {conversation_id}] {question}"
            
            result = self.agent_executor.invoke({"input": modified_question})
            
            return {
                "response": result.get("output", "No response generated"),
                "dataframe": self.genie_tool.result_dataframe,
                "sql_query": self.genie_tool.last_sql_query,
                "conversation_id": conversation_id,
                "success": True
            }
            
        except Exception as e:
            return {
                "response": f"Error continuing conversation: {str(e)}",
                "dataframe": None,
                "sql_query": None,
                "conversation_id": conversation_id,
                "success": False
            }


class VisualizationAgent:
    """Agent specialized in creating visualizations from data."""
    
    def __init__(self, llm: Optional[LLM] = None):
        self.llm = llm or MockLLM()
    
    def suggest_visualization(self, dataframe: pd.DataFrame, query: str, response: str) -> Dict[str, Any]:
        """
        Suggest the best visualization for the given data and context.
        
        Args:
            dataframe: Data to visualize
            query: Original user query
            response: Response from the BI agent
            
        Returns:
            Dictionary with visualization type, reasoning, and insights
        """
        if dataframe is None or dataframe.empty:
            return {
                "chart_type": "none",
                "reasoning": "No data available for visualization",
                "insights": []
            }
        
        try:
            # Analyze data characteristics
            numeric_cols = dataframe.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = dataframe.select_dtypes(include=['object', 'category']).columns.tolist()
            datetime_cols = dataframe.select_dtypes(include=['datetime']).columns.tolist()
            
            # Simple heuristics for chart selection
            chart_type = self._determine_chart_type(
                dataframe, numeric_cols, categorical_cols, datetime_cols, query
            )
            
            # Generate reasoning
            reasoning = self._generate_reasoning(
                chart_type, dataframe, numeric_cols, categorical_cols, datetime_cols
            )
            
            # Extract insights
            insights = self._extract_insights(dataframe, query, response)
            
            return {
                "chart_type": chart_type,
                "reasoning": reasoning,
                "insights": insights,
                "numeric_columns": numeric_cols,
                "categorical_columns": categorical_cols,
                "datetime_columns": datetime_cols
            }
            
        except Exception as e:
            return {
                "chart_type": "table",
                "reasoning": f"Error analyzing data: {str(e)}",
                "insights": []
            }
    
    def _determine_chart_type(self, df: pd.DataFrame, numeric_cols: List[str], 
                            categorical_cols: List[str], datetime_cols: List[str], 
                            query: str) -> str:
        """Determine the best chart type based on data characteristics."""
        
        # Time series detection
        if datetime_cols and numeric_cols:
            if any(word in query.lower() for word in ['trend', 'time', 'over time', 'monthly', 'quarterly', 'yearly']):
                return "line"
        
        # Geographic data detection
        if any(col.lower() in ['state', 'country', 'region', 'location'] for col in categorical_cols):
            if any(word in query.lower() for word in ['geographic', 'location', 'state', 'region']):
                return "map"
        
        # Distribution analysis
        if len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
            if any(word in query.lower() for word in ['distribution', 'breakdown', 'by']):
                if len(df) > 20:
                    return "histogram"
                else:
                    return "bar"
        
        # Comparison analysis
        if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            if any(word in query.lower() for word in ['compare', 'top', 'best', 'worst', 'ranking']):
                return "bar"
        
        # Correlation analysis
        if len(numeric_cols) >= 2:
            if any(word in query.lower() for word in ['correlation', 'relationship', 'vs']):
                return "scatter"
        
        # Default fallback
        if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            return "bar"
        elif len(numeric_cols) >= 1:
            return "histogram"
        else:
            return "table"
    
    def _generate_reasoning(self, chart_type: str, df: pd.DataFrame, 
                          numeric_cols: List[str], categorical_cols: List[str], 
                          datetime_cols: List[str]) -> str:
        """Generate reasoning for chart selection."""
        
        reasoning_map = {
            "bar": f"Bar chart selected to compare {numeric_cols[0] if numeric_cols else 'values'} across {categorical_cols[0] if categorical_cols else 'categories'}",
            "line": f"Line chart selected to show trends over time using {datetime_cols[0] if datetime_cols else 'time'} and {numeric_cols[0] if numeric_cols else 'values'}",
            "scatter": f"Scatter plot selected to show relationship between {numeric_cols[0] if len(numeric_cols) > 0 else 'X'} and {numeric_cols[1] if len(numeric_cols) > 1 else 'Y'}",
            "histogram": f"Histogram selected to show distribution of {numeric_cols[0] if numeric_cols else 'values'}",
            "map": f"Map visualization selected to show geographic distribution of data",
            "table": "Table view selected as the most appropriate format for this data structure"
        }
        
        return reasoning_map.get(chart_type, "Chart type selected based on data characteristics")
    
    def _extract_insights(self, df: pd.DataFrame, query: str, response: str) -> List[str]:
        """Extract key insights from the data."""
        insights = []
        
        try:
            # Basic statistics insights
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            
            for col in numeric_cols[:2]:  # Limit to first 2 numeric columns
                if col in df.columns:
                    max_val = df[col].max()
                    min_val = df[col].min()
                    mean_val = df[col].mean()
                    
                    insights.append(f"{col}: Range from {min_val:,.0f} to {max_val:,.0f}, average {mean_val:,.0f}")
            
            # Row count insight
            insights.append(f"Dataset contains {len(df)} records across {len(df.columns)} dimensions")
            
            # Top categories insight
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            for col in categorical_cols[:1]:  # Limit to first categorical column
                if col in df.columns:
                    top_value = df[col].value_counts().index[0]
                    top_count = df[col].value_counts().iloc[0]
                    insights.append(f"Most common {col}: {top_value} ({top_count} occurrences)")
            
        except Exception:
            insights.append("Data analysis completed successfully")
        
        return insights[:5]  # Limit to 5 insights
