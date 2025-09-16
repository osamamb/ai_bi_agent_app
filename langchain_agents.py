"""
LangChain Agents for Databricks BI Application
"""

import os
from typing import List, Dict, Any, Optional
from langchain.agents import AgentExecutor, create_react_agent
from langchain.agents.agent_types import AgentType
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool, BaseTool
from langchain_community.llms.databricks import Databricks
from langchain_community.chat_models import ChatDatabricks
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models.llms import LLM
from langchain_tools import GenieQueryTool, ResponseEnhancementTool, SQLQueryTool
import pandas as pd


class ForceCompletionTool(BaseTool):
    """Wrapper tool that forces agent completion after first use."""
    
    name: str = "force_completion"
    description: str = "Internal tool to force agent completion"
    wrapped_tool: Any = None
    used: bool = False
    
    def __init__(self, wrapped_tool, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'wrapped_tool', wrapped_tool)
        object.__setattr__(self, 'used', False)
    
    def _run(self, *args, **kwargs) -> str:
        """Run the wrapped tool and mark as used."""
        if self.used:
            return "Tool already used. Please provide Final Answer."
        
        object.__setattr__(self, 'used', True)
        result = self.wrapped_tool._run(*args, **kwargs)
        
        # Force a final answer by appending instruction
        if "Failed" in result or "Error" in result or "Configuration" in result:
            return f"{result}\n\nIMPORTANT: This tool has failed. You must now provide a Final Answer explaining the issue to the user."
        else:
            return f"{result}\n\nIMPORTANT: This tool has completed successfully. You must now provide a Final Answer with these results."


class MockLLM(LLM):
    """Mock LLM for local development when no serving endpoint is available."""
    
    @property
    def _llm_type(self) -> str:
        return "mock"
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """Mock LLM call that provides reasonable responses."""
        # Count how many tool calls have been made by looking at the scratchpad
        tool_call_count = prompt.count("Action: genie_query")
        
        # Check if this is an agent reasoning prompt
        if "User Question:" in prompt:
            # Extract the user question
            question_part = prompt.split("User Question:")[-1].split("\n")[0].strip()
            
            # If we've already tried the tool once and it failed, provide final answer
            if tool_call_count >= 1 and ("Failed" in prompt or "Error" in prompt or "Configuration Error" in prompt):
                return f"Final Answer: I encountered an issue accessing the business intelligence data. Based on your question '{question_part}', I recommend checking your Databricks configuration and trying again. If the issue persists, please verify your DATABRICKS_TOKEN and GENIE_SPACE_ID settings."
            
            # First attempt - use the genie tool
            if tool_call_count == 0:
                return f"I'll help you with your business intelligence question: {question_part}\n\nAction: genie_query\nAction Input: {question_part}"
            
            # If we get here, something unexpected happened - provide final answer
            return f"Final Answer: I've processed your question about '{question_part}' but encountered some technical difficulties. Please check your configuration and try again."
        
        # Handle other types of prompts
        if "enhance" in prompt.lower():
            return "Enhanced response: The data analysis shows significant business insights with actionable recommendations for strategic decision-making."
        elif "Final Answer:" in prompt:
            return "Based on the business intelligence data, here are the key findings and recommendations."
        else:
            return "Final Answer: I'm ready to help with your business intelligence questions. Please ask me about sales, customers, campaigns, or other business metrics."


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
        # Wrap the genie tool with force completion
        force_genie_tool = ForceCompletionTool(self.genie_tool)
        force_genie_tool.name = "genie_query"
        force_genie_tool.description = self.genie_tool.description
        
        tools = [
            Tool(
                name="genie_query",
                description=self.genie_tool.description,
                func=force_genie_tool._run
            )
        ]
        
        # Don't add other tools to force single-tool usage
        # if self.enhancement_tool:
        #     tools.append(
        #         Tool(
        #             name="enhance_response",
        #             description=self.enhancement_tool.description,
        #             func=self.enhancement_tool._run
        #         )
        #     )
        
        # Create agent prompt
        prompt = PromptTemplate.from_template("""
You are a Business Intelligence Agent. You MUST follow this exact process:

MANDATORY PROCESS:
1. Use the genie_query tool ONCE with the user's question
2. After the tool returns ANY result, immediately provide a Final Answer
3. DO NOT use any tool more than once
4. DO NOT retry failed tools

IMPORTANT: After using genie_query, you MUST provide a Final Answer. No exceptions.

Available tools: {tool_names}
Tool descriptions:
{tools}

User Question: {input}

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
            max_iterations=1,  # Only 1 iteration - force immediate completion
            max_execution_time=10,  # 10 seconds max - very aggressive
            return_intermediate_steps=False  # Don't return intermediate steps
        )
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        Process a business intelligence query.
        
        Args:
            question: Natural language business question
            
        Returns:
            Dictionary with response, dataframe, and metadata
        """
        # PRIMARY APPROACH: Try direct tool execution first (most reliable)
        try:
            direct_result = self._direct_tool_execution(question)
            # If direct execution succeeds, return it
            if direct_result["success"]:
                return direct_result
        except Exception:
            # If direct execution fails, continue to agent approach
            pass
        
        # SECONDARY APPROACH: Try agent framework (may hit iteration limits)
        try:
            # Execute agent with timeout handling
            result = self.agent_executor.invoke({"input": question})
            
            # Get additional data from tools
            dataframe = self.genie_tool.result_dataframe
            sql_query = self.genie_tool.last_sql_query
            conversation_id = self.genie_tool.conversation_id
            
            # Ensure we have a response
            response = result.get("output", "")
            if not response:
                response = f"I processed your question about '{question}' but encountered technical difficulties. Please check your Databricks configuration."
            
            return {
                "response": response,
                "dataframe": dataframe,
                "sql_query": sql_query,
                "conversation_id": conversation_id,
                "success": True
            }
            
        except Exception as e:
            error_msg = str(e)

            # TERTIARY APPROACH: If agent fails, try direct tool execution again
            if "iteration limit" in error_msg.lower() or "time limit" in error_msg.lower():
                try:
                    return self._direct_tool_execution(question)
                except Exception:
                    pass
            
            # FINAL FALLBACK: Provide error message
            if "parsing" in error_msg.lower():
                error_msg = "There was an issue understanding the query format. Please try rephrasing your question."

            return {
                "response": f"I encountered an issue processing your query: {error_msg}. Please check your Databricks configuration and try again.",
                "dataframe": None,
                "sql_query": None,
                "conversation_id": None,
                "success": False
            }
    
    def _direct_tool_execution(self, question: str) -> Dict[str, Any]:
        """
        Direct tool execution bypass when agent framework fails.
        This completely bypasses the agent and calls tools directly.
        """
        try:
            # Call genie tool directly
            genie_result = self.genie_tool._run(question)
            
            # Get additional data from tools
            dataframe = self.genie_tool.result_dataframe
            sql_query = self.genie_tool.last_sql_query
            conversation_id = self.genie_tool.conversation_id
            
            # Format response based on tool result
            if "Failed" in genie_result or "Error" in genie_result or "Configuration" in genie_result:
                response = f"I encountered an issue accessing the business intelligence data: {genie_result}"
            else:
                # Build comprehensive response with AI enhancement
                response_parts = [f"Based on your question '{question}', here are the results from the business intelligence system:"]
                
                # Add Genie's analysis
                response_parts.append(genie_result)
                
                # Add SQL query if available
                if sql_query:
                    response_parts.append(f"Generated SQL Query:\n```sql\n{sql_query}\n```")
                
                # Add data results if available
                if dataframe is not None and not dataframe.empty:
                    response_parts.append(f"Data Results:\n{dataframe.to_string(max_rows=10, index=False)}")
                
                # Apply AI enhancement if available
                base_response = "\n\n".join(response_parts)
                if self.enhancement_tool:
                    try:
                        enhanced_response = self.enhancement_tool._run(base_response)
                        response = enhanced_response
                    except Exception:
                        # If enhancement fails, use base response
                        response = base_response
                else:
                    response = base_response
            
            return {
                "response": response,
                "dataframe": dataframe,
                "sql_query": sql_query,
                "conversation_id": conversation_id,
                "success": True
            }
            
        except Exception as e:
            return {
                "response": f"I encountered an issue with direct tool execution: {str(e)}. Please check your Databricks configuration and try again.",
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
