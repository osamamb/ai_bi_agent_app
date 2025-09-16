"""
LangChain Tools for Databricks Genie and Serving Endpoint Integration
"""

import os
import json
import time
import requests
import pandas as pd
from typing import Dict, Any, Optional, List, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from databricks import sql
import streamlit as st


class GenieQueryInput(BaseModel):
    """Input for Genie query tool."""
    query: str = Field(description="Natural language query to ask Genie")
    conversation_id: Optional[str] = Field(default=None, description="Existing conversation ID to continue")


class GenieQueryTool(BaseTool):
    """Tool for querying Databricks Genie API."""
    
    name: str = "genie_query"
    description: str = """
    Query Databricks Genie with natural language questions about business intelligence data.
    Use this tool to ask questions about sales, customers, campaigns, and business metrics.
    Examples: "What are the top performing business units?", "Show me sales trends by quarter"
    """
    args_schema: Type[BaseModel] = GenieQueryInput
    
    # Define instance attributes as class attributes to avoid Pydantic field issues
    host: str = ""
    token: str = ""
    space_id: str = ""
    headers: Dict[str, str] = {}
    _result_dataframe: Optional[pd.DataFrame] = None
    _last_sql_query: Optional[str] = None
    _last_query_results: Optional[str] = None
    _conversation_id: Optional[str] = None
    
    def __init__(self, host: str, token: str, space_id: str, **kwargs):
        super().__init__(**kwargs)
        # Use object.__setattr__ to bypass Pydantic's field validation
        object.__setattr__(self, 'host', host.rstrip('/'))
        object.__setattr__(self, 'token', token)
        object.__setattr__(self, 'space_id', space_id)
        object.__setattr__(self, 'headers', {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
        object.__setattr__(self, '_result_dataframe', None)
        object.__setattr__(self, '_last_sql_query', None)
        object.__setattr__(self, '_last_query_results', None)
        object.__setattr__(self, '_conversation_id', None)
    
    def _run(self, query: str, conversation_id: Optional[str] = None) -> str:
        """Execute the Genie query."""
        try:
            # Check if we have Databricks available
            if not self.host or not self.token or not self.space_id:
                return self._mock_response(query)
            
            # Check for placeholder values
            if self.token == "YOUR_DATABRICKS_TOKEN_HERE":
                return "Configuration Error: DATABRICKS_TOKEN is still set to placeholder value. Please update app.yaml with your actual Databricks personal access token."
            
            if self.space_id == "YOUR_GENIE_SPACE_ID_HERE":
                return "Configuration Error: GENIE_SPACE_ID is still set to placeholder value. Please update app.yaml with your actual Genie space ID."
            
            # Start new conversation or continue existing one
            if not conversation_id:
                response = self._start_conversation(query)
                if not response:
                    error_detail = getattr(self, '_last_error', 'Unknown error')
                    return f"Failed to start conversation with Genie. {error_detail}"
                
                self._conversation_id = response.get("conversation_id")
                message_id = response.get("message_id")
            else:
                self._conversation_id = conversation_id
                message_id = self._create_message(conversation_id, query)
            
            if not message_id:
                return "Failed to send message to Genie"
            
            # Wait for response with timeout
            genie_response = self._wait_for_response(self._conversation_id, message_id)
            
            # Check if it's a timeout and provide helpful message
            if genie_response and "Query timed out" in genie_response:
                return f"Genie query timed out. The question '{query}' may be too complex or there may be connectivity issues. Try: 1) A simpler, more specific question, 2) Check your network connection, 3) Verify your Genie space is active."
            
            return genie_response or "No response received from Genie"
            
        except Exception as e:
            return f"Error querying Genie: {str(e)}"
    
    def _start_conversation(self, content: str) -> Optional[Dict[str, Any]]:
        """Start a new conversation with Genie."""
        endpoints_to_try = [
            f"{self.host}/api/2.0/genie/spaces/{self.space_id}/start-conversation",
            f"{self.host}/api/2.1/genie/spaces/{self.space_id}/start-conversation",
            f"{self.host}/api/2.0/genie/spaces/{self.space_id}/conversations",
            f"{self.host}/api/2.1/genie/spaces/{self.space_id}/conversations"
        ]
        
        payload = {"content": content}
        last_error = None
        
        for url in endpoints_to_try:
            try:
                response = requests.post(url, headers=self.headers, json=payload, timeout=30)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    last_error = f"Authentication failed (401). Check your DATABRICKS_TOKEN permissions."
                    break
                elif response.status_code == 403:
                    last_error = f"Access forbidden (403). Check if you have access to Genie space {self.space_id[:8]}..."
                    break
                elif response.status_code == 404:
                    last_error = f"Genie space not found (404). Check if space ID {self.space_id[:8]}... exists."
                    continue
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:100]}"
            except requests.exceptions.Timeout:
                last_error = f"Request timeout. Check network connection to {self.host}"
            except requests.exceptions.ConnectionError:
                last_error = f"Connection error. Check if {self.host} is accessible."
            except Exception as e:
                last_error = f"Request error: {str(e)}"
        
        # Store the last error for debugging
        if hasattr(self, '_last_error'):
            object.__setattr__(self, '_last_error', last_error)
        
        return None
    
    def _create_message(self, conversation_id: str, content: str) -> Optional[str]:
        """Create a message in existing conversation."""
        endpoints_to_try = [
            f"{self.host}/api/2.0/genie/spaces/{self.space_id}/conversations/{conversation_id}/messages",
            f"{self.host}/api/2.1/genie/spaces/{self.space_id}/conversations/{conversation_id}/messages"
        ]
        
        payload = {"content": content}
        
        for url in endpoints_to_try:
            try:
                response = requests.post(url, headers=self.headers, json=payload, timeout=30)
                if response.status_code == 200:
                    return response.json().get("id")
            except Exception:
                continue
        
        return None
    
    def _wait_for_response(self, conversation_id: str, message_id: str, max_wait: int = 30) -> Optional[str]:
        """Wait for Genie response."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # Check message status
                url = f"{self.host}/api/2.0/genie/spaces/{self.space_id}/conversations/{conversation_id}/messages/{message_id}"
                response = requests.get(url, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    message_data = response.json()
                    
                    # Check if we have a response
                    if message_data.get("status") == "COMPLETED":
                        content = message_data.get("content", "")
                        
                        # Store SQL query and results if available
                        attachments = message_data.get("attachments", [])
                        for attachment in attachments:
                            if attachment.get("type") == "query_result":
                                self._last_sql_query = attachment.get("query", {}).get("query", "")
                                
                                # Try to get query results
                                statement_id = attachment.get("query", {}).get("statement_id")
                                if statement_id:
                                    self._get_query_results(statement_id)
                        
                        return content
                    
                    elif message_data.get("status") == "FAILED":
                        return "Query failed to execute"
                
                time.sleep(2)
                
            except Exception:
                time.sleep(2)
        
        return f"Query timed out after {max_wait} seconds. This may indicate: 1) Complex query requiring more time, 2) Network connectivity issues, 3) Genie service overload. Try a simpler question or check your connection."
    
    def _get_query_results(self, statement_id: str):
        """Get query results and store as DataFrame."""
        try:
            endpoints_to_try = [
                f"{self.host}/api/2.0/sql/statements/{statement_id}",
                f"{self.host}/api/2.1/sql/statements/{statement_id}"
            ]
            
            for url in endpoints_to_try:
                try:
                    response = requests.get(url, headers=self.headers, timeout=30)
                    if response.status_code == 200:
                        result_data = response.json()
                        
                        # Extract results
                        if "result" in result_data and "data_array" in result_data["result"]:
                            data_array = result_data["result"]["data_array"]
                            columns = [col["name"] for col in result_data["result"]["schema"]["columns"]]
                            
                            # Create DataFrame
                            self._result_dataframe = pd.DataFrame(data_array, columns=columns)
                            self._last_query_results = self._result_dataframe.to_string(max_rows=10)
                            return
                            
                except Exception:
                    continue
                    
        except Exception:
            pass
    
    def _mock_response(self, query: str) -> str:
        """Generate mock response for local testing."""
        query_lower = query.lower()
        
        if "describe" in query_lower and "dataset" in query_lower:
            return """Dataset Description:
- **Sales Data**: Contains transaction records with customer_id, product_id, amount, date
- **Customer Data**: Customer demographics including age, location, segment  
- **Product Data**: Product catalog with categories, prices, descriptions
- **Campaign Data**: Marketing campaign performance metrics
- **Time Range**: Data spans 2020-2024 with daily granularity
- **Total Records**: Approximately 2.5M transactions across all tables
- **Key Metrics**: Revenue, customer acquisition, product performance, regional trends"""
        
        return f"Here's the analysis for your query about {query}. The data shows various patterns in tenure bands, campaigns, and sales metrics that can be visualized effectively."
    
    @property
    def conversation_id(self) -> Optional[str]:
        """Get current conversation ID."""
        return self._conversation_id
    
    @property
    def result_dataframe(self) -> Optional[pd.DataFrame]:
        """Get result DataFrame."""
        return self._result_dataframe
    
    @property
    def last_sql_query(self) -> Optional[str]:
        """Get last SQL query."""
        return self._last_sql_query
    
    @property
    def last_query_results(self) -> Optional[str]:
        """Get last query results."""
        return self._last_query_results


class ResponseEnhancementInput(BaseModel):
    """Input for response enhancement tool."""
    original_response: str = Field(description="Original response to enhance")
    sql_query: Optional[str] = Field(default="", description="SQL query that was executed")
    query_results: Optional[str] = Field(default="", description="Results from the query")


class ResponseEnhancementTool(BaseTool):
    """Tool for enhancing responses using Databricks serving endpoint."""
    
    name: str = "enhance_response"
    description: str = """
    Enhance a response using an LLM serving endpoint to make it more business-friendly 
    and provide additional insights. Use this after getting a response from Genie.
    """
    args_schema: Type[BaseModel] = ResponseEnhancementInput
    
    # Define instance attributes as class attributes to avoid Pydantic field issues
    host: str = ""
    token: str = ""
    endpoint_name: str = ""
    headers: Dict[str, str] = {}
    endpoint_url: str = ""
    
    def __init__(self, host: str, token: str, endpoint_name: str, **kwargs):
        super().__init__(**kwargs)
        # Use object.__setattr__ to bypass Pydantic's field validation
        object.__setattr__(self, 'host', host.rstrip('/'))
        object.__setattr__(self, 'token', token)
        object.__setattr__(self, 'endpoint_name', endpoint_name)
        object.__setattr__(self, 'headers', {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
        object.__setattr__(self, 'endpoint_url', f"{host.rstrip('/')}/serving-endpoints/{endpoint_name}/invocations" if endpoint_name else "")
    
    def _run(self, original_response: str, sql_query: str = "", query_results: str = "") -> str:
        """Enhance the response using LLM."""
        if not self.endpoint_url:
            return original_response
        
        try:
            # Create enhancement prompt
            enhancement_prompt = self._create_enhancement_prompt(original_response, sql_query, query_results)
            
            # Try different payload formats
            payload_formats = [
                {
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are a senior business intelligence analyst providing in-depth analysis. Transform raw data responses into comprehensive, actionable business analysis."
                        },
                        {
                            "role": "user", 
                            "content": enhancement_prompt
                        }
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.3
                },
                {
                    "inputs": enhancement_prompt,
                    "parameters": {
                        "max_new_tokens": 1000,
                        "temperature": 0.3,
                        "do_sample": True
                    }
                }
            ]
            
            for payload_format in payload_formats:
                try:
                    response = requests.post(
                        self.endpoint_url, 
                        headers=self.headers, 
                        json=payload_format,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Extract response based on format
                        if "choices" in result and result["choices"]:
                            return result["choices"][0]["message"]["content"]
                        elif "generated_text" in result:
                            return result["generated_text"]
                        elif isinstance(result, list) and result:
                            return result[0].get("generated_text", original_response)
                        elif "predictions" in result and result["predictions"]:
                            return result["predictions"][0]
                        
                except Exception:
                    continue
            
            return original_response
            
        except Exception as e:
            return original_response
    
    def _create_enhancement_prompt(self, original_response: str, sql_query: str, query_results: str) -> str:
        """Create prompt for response enhancement."""
        prompt = f"""
Please enhance the following business intelligence response to make it more comprehensive and actionable:

Original Response:
{original_response}

"""
        
        if sql_query:
            prompt += f"""
SQL Query Executed:
{sql_query}

"""
        
        if query_results:
            prompt += f"""
Query Results Sample:
{query_results}

"""
        
        prompt += """
Please provide an enhanced response that:
1. Uses clear, business-friendly language
2. Highlights key insights and patterns
3. Provides actionable recommendations
4. Explains the business implications
5. Maintains accuracy while adding context

Enhanced Response:"""
        
        return prompt


class SQLQueryInput(BaseModel):
    """Input for SQL query tool."""
    query: str = Field(description="SQL query to execute")


class SQLQueryTool(BaseTool):
    """Tool for executing SQL queries against Databricks warehouse."""
    
    name: str = "sql_query"
    description: str = """
    Execute SQL queries against the Databricks warehouse to retrieve business data.
    Use this for direct database queries when you need specific data analysis.
    """
    args_schema: Type[BaseModel] = SQLQueryInput
    
    # Define instance attributes as class attributes to avoid Pydantic field issues
    host: str = ""
    token: str = ""
    warehouse_id: str = ""
    
    def __init__(self, host: str, token: str, warehouse_id: str, **kwargs):
        super().__init__(**kwargs)
        # Use object.__setattr__ to bypass Pydantic's field validation
        object.__setattr__(self, 'host', host)
        object.__setattr__(self, 'token', token)
        object.__setattr__(self, 'warehouse_id', warehouse_id)
    
    def _run(self, query: str) -> str:
        """Execute SQL query and return results."""
        try:
            if not self.host or not self.token or not self.warehouse_id:
                return "SQL query not available in local mode"
            
            with sql.connect(
                server_hostname=self.host,
                http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
                access_token=self.token
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query)
                    df = cursor.fetchall_arrow().to_pandas()
                    
                    if df.empty:
                        return "No results found"
                    
                    # Return formatted results
                    return f"Query executed successfully. Results:\n{df.to_string(max_rows=10)}"
                    
        except Exception as e:
            return f"Error executing SQL query: {str(e)}"
