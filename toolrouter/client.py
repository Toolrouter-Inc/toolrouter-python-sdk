"""
ToolRouter Python SDK

A comprehensive Python client for the ToolRouter API supporting both direct access
and account-level operations with full async support and type safety.

Copyright 2025 ToolRouter Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

import httpx
from pydantic import BaseModel, Field
from typing_extensions import Literal

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# EXCEPTION CLASSES
# ============================================================================

class ToolRouterError(Exception):
    """Base exception for all ToolRouter SDK errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class AuthenticationError(ToolRouterError):
    """Raised when authentication fails."""
    pass


class NotFoundError(ToolRouterError):
    """Raised when a requested resource is not found."""
    pass


class ValidationError(ToolRouterError):
    """Raised when request validation fails."""
    pass


class ServerError(ToolRouterError):
    """Raised when server returns an error."""
    pass


class RateLimitError(ToolRouterError):
    """Raised when rate limit is exceeded."""
    pass


# ============================================================================
# PYDANTIC MODELS FOR TYPE SAFETY
# ============================================================================

class Tool(BaseModel):
    """Represents a tool in the ToolRouter system."""
    
    tool_id: Optional[str] = None
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    input_schema: Optional[Dict[str, Any]] = None
    server: Optional[str] = None


class DirectAccessTool(BaseModel):
    """Tool format for direct access APIs."""
    
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class StackConfiguration(BaseModel):
    """Configuration for a stack."""
    
    analytics_enabled: bool = False


class StackServer(BaseModel):
    """Server configuration within a stack."""
    
    server_name: str
    enabled_tools: List[str] = Field(default_factory=list)


class Stack(BaseModel):
    """Represents a stack in the account system."""
    
    stack_id: str
    stack_name: str
    configuration: StackConfiguration
    servers: List[StackServer] = Field(default_factory=list)
    created_at: str
    updated_at: str


class Credential(BaseModel):
    """Represents credential information."""
    
    field_id: str
    name: str
    description: str
    required: bool


class Server(BaseModel):
    """Represents a server in the marketplace."""
    
    server_id: str
    name: str
    description: str
    tools: List[Tool] = Field(default_factory=list)
    required_credentials: List[Credential] = Field(default_factory=list)
    optional_credentials: List[Credential] = Field(default_factory=list)


class CredentialsStatus(BaseModel):
    """Status of credentials for a server."""
    
    required_credentials: Dict[str, str] = Field(default_factory=dict)
    optional_credentials: Dict[str, str] = Field(default_factory=dict)
    all_credentials_added: bool
    required_credentials_added: bool


# ============================================================================
# BASE CLIENT CLASS
# ============================================================================

class BaseClient:
    """Base client with shared functionality."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        rate_limit_requests: int = 60,
        rate_limit_window: int = 60
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        
        # Rate limiting state
        self._request_timestamps: List[float] = []
        
        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "ToolRouter-Python-SDK/0.2.0"
                }
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def _check_rate_limit(self):
        """Check if we're within rate limits."""
        now = asyncio.get_event_loop().time()
        # Remove timestamps older than the window
        self._request_timestamps = [
            ts for ts in self._request_timestamps 
            if now - ts < self.rate_limit_window
        ]
        
        if len(self._request_timestamps) >= self.rate_limit_requests:
            raise RateLimitError(
                f"Rate limit exceeded: {self.rate_limit_requests} requests per {self.rate_limit_window} seconds"
            )
        
        self._request_timestamps.append(now)
    
    def _handle_response_error(self, response: httpx.Response):
        """Handle HTTP response errors."""
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key", response.status_code)
        elif response.status_code == 404:
            raise NotFoundError("Resource not found", response.status_code)
        elif response.status_code == 400:
            raise ValidationError("Invalid request", response.status_code)
        elif response.status_code == 429:
            raise RateLimitError("Rate limit exceeded", response.status_code)
        elif response.status_code >= 500:
            raise ServerError("Server error", response.status_code)
        else:
            raise ToolRouterError(f"HTTP {response.status_code}", response.status_code)
    
    async def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request with retries and error handling."""
        
        self._check_rate_limit()
        client = await self._get_client()
        
        for attempt in range(self.max_retries + 1):
            try:
                if method.upper() == "GET":
                    response = await client.get(url, params=params)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data, params=params)
                elif method.upper() == "PUT":
                    response = await client.put(url, json=data, params=params)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                if response.is_success:
                    return response.json()
                else:
                    self._handle_response_error(response)
                    
            except httpx.RequestError as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    await asyncio.sleep(wait_time)
                    continue
                raise ToolRouterError(f"Request failed after {self.max_retries + 1} attempts: {str(e)}")
            except httpx.HTTPStatusError as e:
                self._handle_response_error(e.response)
        
        raise ToolRouterError("Max retries exceeded")


# ============================================================================
# DIRECT ACCESS CLIENT
# ============================================================================

class DirectAccessClient(BaseClient):
    """Client for direct access APIs (MCP-style tool calling)."""
    
    def __init__(
        self,
        client_id: str,
        api_key: str,
        base_url: str = "https://api.toolrouter.ai/s",
        schema: Literal["openai", "anthropic", "default"] = "openai",
        **kwargs
    ):
        """
        Initialize DirectAccessClient.
        
        Args:
            client_id: Your ToolRouter client ID
            api_key: Your ToolRouter API key
            base_url: Base URL for direct access APIs
            schema: Default schema format for tools
            **kwargs: Additional arguments passed to BaseClient
        
        Example:
            >>> client = DirectAccessClient("client-id", "api-key")
            >>> tools = await client.list_tools()
        """
        super().__init__(api_key, base_url, **kwargs)
        self.client_id = client_id
        self.default_schema = schema
    
    async def list_tools(self, schema: Optional[str] = None) -> List[Union[Tool, Dict[str, Any]]]:
        """
        Get available tools from ToolRouter.
        
        Args:
            schema: Schema format ("openai", "anthropic", "default"). Uses client default if not specified.
            
        Returns:
            List of available tools
            
        Example:
            >>> tools = await client.list_tools(schema="openai")
        """
        schema = schema or self.default_schema
        url = f"{self.base_url}/{self.client_id}/list_tools"
        params = {"schema": schema}
        
        response = await self._make_request("GET", url, params=params)
        return response.get("tools", [])
    
    async def call_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool using ToolRouter.
        
        Args:
            tool_name: Name of the tool to call
            tool_input: Input parameters for the tool
            
        Returns:
            Result of the tool execution
            
        Example:
            >>> result = await client.call_tool("weather", {"location": "San Francisco"})
        """
        url = f"{self.base_url}/{self.client_id}/call_tool"
        data = {
            "tool_name": tool_name,
            "tool_input": tool_input
        }
        
        response = await self._make_request("POST", url, data=data)
        return response.get("result", {})

# ============================================================================
# ACCOUNT API CLIENT
# ============================================================================

class APIClient(BaseClient):
    """Client for account-level APIs with full stack management."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.toolrouter.ai/v1",
        schema: Literal["openai", "anthropic", "default"] = "openai",
        **kwargs
    ):
        """
        Initialize APIClient for account-level operations.
        
        Args:
            api_key: Your ToolRouter API key for account access
            base_url: Base URL for account APIs
            schema: Default schema format for tools
            **kwargs: Additional arguments passed to BaseClient
            
        Example:
            >>> client = APIClient("account-api-key")
            >>> stacks = await client.list_stacks()
        """
        super().__init__(api_key, base_url, **kwargs)
        self.default_schema = schema
    
    # ========================================================================
    # STACK METHODS
    # ========================================================================
    
    async def list_stacks(self) -> List[Stack]:
        """
        List all stacks.
        
        Returns:
            List of Stack objects
            
        Example:
            >>> stacks = await client.list_stacks()
            >>> for stack in stacks:
            ...     print(f"{stack.stack_name}: {len(stack.servers)} servers")
        """
        url = f"{self.base_url}/stacks"
        response = await self._make_request("GET", url)
        return [Stack(**stack_data) for stack_data in response]
    
    async def create_stack(
        self,
        stack_name: str,
        analytics_enabled: bool = False
    ) -> Stack:
        """
        Create a new stack.
        
        Args:
            stack_name: Name for the new stack
            analytics_enabled: Whether to enable analytics
            
        Returns:
            Created Stack object
            
        Example:
            >>> stack = await client.create_stack("my-stack", analytics_enabled=True)
        """
        url = f"{self.base_url}/stacks"
        data = {
            "stack_name": stack_name,
            "configuration": {
                "analytics_enabled": analytics_enabled
            }
        }
        
        response = await self._make_request("POST", url, data=data)
        return Stack(**response)
    
    async def update_stack(
        self,
        stack_id: str,
        stack_name: Optional[str] = None,
        analytics_enabled: Optional[bool] = None
    ) -> Stack:
        """
        Update an existing stack.
        
        Args:
            stack_id: ID of the stack to update
            stack_name: New name for the stack
            analytics_enabled: Whether to enable analytics
            
        Returns:
            Updated Stack object
            
        Example:
            >>> stack = await client.update_stack("stack-123", analytics_enabled=True)
        """
        url = f"{self.base_url}/stacks/{stack_id}"
        data = {}
        
        if stack_name is not None:
            data["stack_name"] = stack_name
        if analytics_enabled is not None:
            data["configuration"] = {"analytics_enabled": analytics_enabled}
        
        response = await self._make_request("PUT", url, data=data)
        return Stack(**response)
    
    async def delete_stack(self, stack_id: str) -> bool:
        """
        Delete a stack.
        
        Args:
            stack_id: ID of the stack to delete
            
        Returns:
            True if successful
            
        Example:
            >>> success = await client.delete_stack("stack-123")
        """
        url = f"{self.base_url}/stacks/{stack_id}"
        await self._make_request("DELETE", url)
        return True
    
    # ========================================================================
    # SERVER METHODS
    # ========================================================================
    
    async def list_servers(self) -> List[Server]:
        """
        List all available servers.
        
        Returns:
            List of Server objects
            
        Example:
            >>> servers = await client.list_servers()
            >>> for server in servers:
            ...     print(f"{server.name}: {len(server.tools)} tools")
        """
        url = f"{self.base_url}/servers"
        response = await self._make_request("GET", url)
        return [Server(**server_data) for server_data in response]
    
    async def add_server_to_stack(
        self,
        stack_id: str,
        server_id: str,
        enable_all_tools: bool = False,
        enabled_tools: Optional[List[str]] = None
    ) -> bool:
        """
        Add a server to a stack.
        
        Args:
            stack_id: ID of the stack
            server_id: ID of the server to add
            enable_all_tools: Whether to enable all tools
            enabled_tools: Specific tools to enable
            
        Returns:
            True if successful
            
        Example:
            >>> await client.add_server_to_stack("stack-123", "server-456", enable_all_tools=True)
        """
        url = f"{self.base_url}/stacks/{stack_id}/servers"
        data = {
            "server_id": server_id,
            "enable_all_tools": enable_all_tools
        }
        if enabled_tools is not None:
            data["enabled_tools"] = enabled_tools
        
        await self._make_request("POST", url, data=data)
        return True
    
    async def remove_server_from_stack(self, stack_id: str, server_id: str) -> bool:
        """
        Remove a server from a stack.
        
        Args:
            stack_id: ID of the stack
            server_id: ID of the server to remove
            
        Returns:
            True if successful
            
        Example:
            >>> await client.remove_server_from_stack("stack-123", "server-456")
        """
        url = f"{self.base_url}/stacks/{stack_id}/servers/{server_id}"
        await self._make_request("DELETE", url)
        return True
    
    async def update_server_tools(
        self,
        stack_id: str,
        server_id: str,
        enabled_tools: List[str]
    ) -> bool:
        """
        Update enabled tools for a server in a stack.
        
        Args:
            stack_id: ID of the stack
            server_id: ID of the server
            enabled_tools: List of tool IDs to enable
            
        Returns:
            True if successful
            
        Example:
            >>> await client.update_server_tools("stack-123", "server-456", ["tool1", "tool2"])
        """
        url = f"{self.base_url}/stacks/{stack_id}/servers/{server_id}/tools"
        data = {"enabled_tools": enabled_tools}
        
        await self._make_request("PUT", url, data=data)
        return True
    
    # ========================================================================
    # CREDENTIAL METHODS
    # ========================================================================
    
    async def get_credentials_status(self, stack_id: str, server_id: str) -> CredentialsStatus:
        """
        Get credentials status for a server in a stack.
        
        Args:
            stack_id: ID of the stack
            server_id: ID of the server
            
        Returns:
            CredentialsStatus object
            
        Example:
            >>> status = await client.get_credentials_status("stack-123", "server-456")
            >>> if not status.required_credentials_added:
            ...     print("Missing required credentials")
        """
        url = f"{self.base_url}/stacks/{stack_id}/servers/{server_id}/credentials"
        response = await self._make_request("GET", url)
        return CredentialsStatus(**response)
    
    async def update_credentials(
        self,
        stack_id: str,
        server_id: str,
        credentials: Dict[str, str]
    ) -> bool:
        """
        Update credentials for a server in a stack.
        
        Args:
            stack_id: ID of the stack
            server_id: ID of the server
            credentials: Dictionary of credential field_id -> value
            
        Returns:
            True if successful
            
        Example:
            >>> await client.update_credentials(
            ...     "stack-123", "server-456", 
            ...     {"api_key": "secret-key", "username": "user"}
            ... )
        """
        url = f"{self.base_url}/stacks/{stack_id}/servers/{server_id}/credentials"
        data = {"credentials": credentials}
        
        await self._make_request("PUT", url, data=data)
        return True
    
    # ========================================================================
    # TOOL METHODS
    # ========================================================================
    
    async def list_stack_tools(
        self,
        stack_id: str,
        schema: Optional[str] = None
    ) -> List[Union[Tool, Dict[str, Any]]]:
        """
        List tools available in a stack.
        
        Args:
            stack_id: ID of the stack
            schema: Schema format. Uses client default if not specified.
            
        Returns:
            List of tools
            
        Example:
            >>> tools = await client.list_stack_tools("stack-123", schema="openai")
        """
        schema = schema or self.default_schema
        url = f"{self.base_url}/stacks/{stack_id}/tools"
        params = {"schema": schema}
        
        response = await self._make_request("GET", url, params=params)
        return response.get("tools", [])
    
    async def invoke_tool(
        self,
        stack_id: str,
        tool_id: str,
        tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Invoke a tool in a stack.
        
        Args:
            stack_id: ID of the stack
            tool_id: ID of the tool to invoke
            tool_input: Input parameters for the tool
            
        Returns:
            Tool execution result
            
        Example:
            >>> result = await client.invoke_tool(
            ...     "stack-123", "weather", {"location": "San Francisco"}
            ... )
        """
        url = f"{self.base_url}/stacks/{stack_id}/tools/{tool_id}/invoke"
        data = {"tool_input": tool_input}
        
        response = await self._make_request("POST", url, data=data)
        return response
    
    # ========================================================================
    # CONVENIENCE METHODS
    # ========================================================================
    
    async def create_stack_with_server(
        self,
        stack_name: str,
        server_id: str,
        enable_all_tools: bool = True,
        analytics_enabled: bool = False,
        credentials: Optional[Dict[str, str]] = None
    ) -> Stack:
        """
        Convenience method to create a stack and add a server in one call.
        
        Args:
            stack_name: Name for the new stack
            server_id: ID of the server to add
            enable_all_tools: Whether to enable all tools
            analytics_enabled: Whether to enable analytics
            credentials: Optional credentials to set
            
        Returns:
            Created Stack object
            
        Example:
            >>> stack = await client.create_stack_with_server(
            ...     "my-stack", "github-server", 
            ...     credentials={"token": "ghp_123"}
            ... )
        """
        # Create stack
        stack = await self.create_stack(stack_name, analytics_enabled)
        
        # Add server
        await self.add_server_to_stack(
            stack.stack_id, server_id, enable_all_tools=enable_all_tools
        )
        
        # Set credentials if provided
        if credentials:
            await self.update_credentials(stack.stack_id, server_id, credentials)
        
        # Return updated stack info
        stacks = await self.list_stacks()
        return next(s for s in stacks if s.stack_id == stack.stack_id)
    
    async def get_stack_summary(self, stack_id: str) -> Dict[str, Any]:
        """
        Get a comprehensive summary of a stack.
        
        Args:
            stack_id: ID of the stack
            
        Returns:
            Dictionary with stack details, tools, and credential status
            
        Example:
            >>> summary = await client.get_stack_summary("stack-123")
            >>> print(f"Stack has {summary['total_tools']} tools available")
        """
        # Get stack details
        stacks = await self.list_stacks()
        stack = next((s for s in stacks if s.stack_id == stack_id), None)
        if not stack:
            raise NotFoundError(f"Stack {stack_id} not found")
        
        # Get tools
        tools = await self.list_stack_tools(stack_id)
        
        # Get credential status for each server
        credential_status = {}
        for server in stack.servers:
            try:
                status = await self.get_credentials_status(stack_id, server.server_name)
                credential_status[server.server_name] = status
            except Exception as e:
                logger.warning(f"Could not get credentials for {server.server_name}: {e}")
        
        return {
            "stack": stack,
            "total_tools": len(tools),
            "tools": tools,
            "credential_status": credential_status,
            "servers_configured": len([
                s for s, status in credential_status.items()
                if status.required_credentials_added
            ])
        }


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

# Keep the old ToolRouter class for backward compatibility
ToolRouter = DirectAccessClient

# Standalone functions for backward compatibility
_default_direct_client: Optional[DirectAccessClient] = None

def _get_default_direct_client() -> DirectAccessClient:
    """Get the default direct access client."""
    global _default_direct_client
    if _default_direct_client is None:
        raise ValueError(
            "No default DirectAccessClient has been configured. "
            "Please initialize by calling setup_default_router() first."
        )
    return _default_direct_client

def setup_default_router(
    client_id: str,
    api_key: str,
    base_url: str = "https://api.toolrouter.ai/s",
    **kwargs
) -> DirectAccessClient:
    """
    Configure the default direct access client.
    
    Args:
        client_id: Your ToolRouter client ID
        api_key: Your ToolRouter API key
        base_url: Base URL for direct access APIs
        **kwargs: Additional arguments
        
    Returns:
        Configured DirectAccessClient
    """
    global _default_direct_client
    _default_direct_client = DirectAccessClient(client_id, api_key, base_url, **kwargs)
    return _default_direct_client

def list_tools(schema: str = "openai") -> List[Union[Tool, Dict[str, Any]]]:
    """
    Get available tools using the default client.
    
    Note: This is a synchronous wrapper. For async usage, use DirectAccessClient directly.
    
    Args:
        schema: Schema format
        
    Returns:
        List of tools
    """
    client = _get_default_direct_client()
    return asyncio.run(client.list_tools(schema))

def call_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call a tool using the default client.
    
    Note: This is a synchronous wrapper. For async usage, use DirectAccessClient directly.
    
    Args:
        tool_name: Name of the tool
        tool_input: Tool input parameters
        
    Returns:
        Tool result
    """
    client = _get_default_direct_client()
    return asyncio.run(client.call_tool(tool_name, tool_input))
