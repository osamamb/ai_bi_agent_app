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
    
    def __init__(self, host: str, token: str, space_id: str):
        super().__init__()
        self.host = host.rstrip('/')
        self.token = token
        self.space_id = space_id
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        self._result_dataframe = None
        self._last_sql_query = None
        self._last_query_results = None
        self._conversation_id = None
    
    def _run(self, query: str, conversation_id: Optional[str] = None) -> str:
        """Execute the Genie query."""
        try:
            # Check if we have Databricks available
            if not self.host or not self.token or not self.space_id:
                return self._mock_response(query)
            
            # Start new conversation or continue existing one
            if not conversation_id:
                response = self._start_conversation(query)
                if not response:
                    return "Failed to start conversation with Genie"
                
                self._conversation_id = response.get("conversation_id")
                message_id = response.get("message_id")
            else:
                self._conversation_id = conversation_id
                message_id = self._create_message(conversation_id, query)
            
            if not message_id:
                return "Failed to send message to Genie"
            
            # Wait for response
            genie_response = self._wait_for_response(self._conversation_id, message_id)
            
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
        
        for url in endpoints_to_try:
            try:
                response = requests.post(url, headers=self.headers, json=payload, timeout=30)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    continue
            except Exception:
                continue
        
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
    
    def _wait_for_response(self, conversation_id: str, message_id: str, max_wait: int = 60) -> Optional[str]:
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
        
        return "Query timed out"
    
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
    
    def __init__(self, host: str, token: str, endpoint_name: str):
        super().__init__()
        self.host = host.rstrip('/')
        self.token = token
        self.endpoint_name = endpoint_name
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        self.endpoint_url = f"{self.host}/serving-endpoints/{self.endpoint_name}/invocations" if self.endpoint_name else ""
    
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
    
    def __init__(self, host: str, token: str, warehouse_id: str):
        super().__init__()
        self.host = host
        self.token = token
        self.warehouse_id = warehouse_id
    
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
