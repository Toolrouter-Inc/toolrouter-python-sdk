"""
Tests for the ToolRouter Python SDK.

This file tests both DirectAccessClient and APIClient functionality
with proper async testing patterns and error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import httpx

from toolrouter import (
    DirectAccessClient,
    APIClient,
    ToolRouter,
    setup_default_router,
    list_tools,
    call_tool,
    ToolRouterError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    ServerError,
    RateLimitError,
    Tool,
    Stack,
    Server,
    CredentialsStatus
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_tools_response():
    """Mock response for list_tools API."""
    return {
        "tools": [
            {
                "name": "weather",
                "description": "Get weather information",
                "parameters": {"type": "object", "properties": {"location": {"type": "string"}}}
            },
            {
                "name": "calculator", 
                "description": "Perform calculations",
                "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}}
            }
        ]
    }

@pytest.fixture
def mock_tool_call_response():
    """Mock response for call_tool API."""
    return {
        "result": {
            "temperature": "72°F",
            "condition": "sunny",
            "location": "San Francisco"
        }
    }

@pytest.fixture
def mock_stacks_response():
    """Mock response for list_stacks API."""
    return [
        {
            "stack_id": "stack-123",
            "stack_name": "My Test Stack",
            "configuration": {"analytics_enabled": True},
            "servers": [
                {
                    "server_name": "github-server",
                    "enabled_tools": ["create_issue", "list_repos"]
                }
            ],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    ]

@pytest.fixture
def mock_servers_response():
    """Mock response for list_servers API."""
    return [
        {
            "server_id": "github-server",
            "name": "GitHub Server", 
            "description": "GitHub integration server",
            "tools": [
                {
                    "tool_id": "create_issue",
                    "name": "create_issue",
                    "description": "Create a GitHub issue",
                    "parameters": {}
                }
            ],
            "required_credentials": [
                {
                    "field_id": "token",
                    "name": "GitHub Token",
                    "description": "GitHub personal access token",
                    "required": True
                }
            ],
            "optional_credentials": []
        }
    ]


# ============================================================================
# DIRECT ACCESS CLIENT TESTS
# ============================================================================

class TestDirectAccessClient:
    """Test DirectAccessClient functionality."""
    
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization with various parameters."""
        client = DirectAccessClient(
            client_id="test-client",
            api_key="test-key",
            schema="openai",
            timeout=60.0
        )
        
        assert client.client_id == "test-client"
        assert client.api_key == "test-key"
        assert client.default_schema == "openai"
        assert client.timeout == 60.0
        assert client.base_url == "https://api.toolrouter.ai/s"
    
    @pytest.mark.asyncio
    async def test_list_tools_success(self, mock_tools_response):
        """Test successful list_tools call."""
        client = DirectAccessClient("test-client", "test-key")
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_tools_response
            
            tools = await client.list_tools(schema="openai")
            
            mock_request.assert_called_once_with(
                "GET",
                "https://api.toolrouter.ai/s/test-client/list_tools",
                params={"schema": "openai"}
            )
            assert len(tools) == 2
            assert tools[0]["name"] == "weather"
    
    @pytest.mark.asyncio
    async def test_call_tool_success(self, mock_tool_call_response):
        """Test successful call_tool call."""
        client = DirectAccessClient("test-client", "test-key")
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_tool_call_response
            
            result = await client.call_tool("weather", {"location": "San Francisco"})
            
            mock_request.assert_called_once_with(
                "POST",
                "https://api.toolrouter.ai/s/test-client/call_tool",
                data={
                    "tool_name": "weather",
                    "tool_input": {"location": "San Francisco"}
                }
            )
            assert result["temperature"] == "72°F"
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using client as async context manager."""
        async with DirectAccessClient("test-client", "test-key") as client:
            assert client._client is None  # Not created until first request
        
        # Client should be closed after exiting context
        assert client._client is None
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        client = DirectAccessClient(
            "test-client", "test-key",
            rate_limit_requests=2,
            rate_limit_window=1
        )
        
        # First two requests should work
        client._check_rate_limit()
        client._check_rate_limit()
        
        # Third request should raise rate limit error
        with pytest.raises(RateLimitError):
            client._check_rate_limit()


# ============================================================================
# ACCOUNT API CLIENT TESTS  
# ============================================================================

class TestAPIClient:
    """Test APIClient functionality."""
    
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test APIClient initialization."""
        client = APIClient(
            api_key="test-account-key",
            schema="anthropic",
            timeout=45.0
        )
        
        assert client.api_key == "test-account-key"
        assert client.default_schema == "anthropic"
        assert client.timeout == 45.0
        assert client.base_url == "https://api.toolrouter.ai/v1"
    
    @pytest.mark.asyncio
    async def test_list_stacks_success(self, mock_stacks_response):
        """Test successful list_stacks call."""
        client = APIClient("test-account-key")
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_stacks_response
            
            stacks = await client.list_stacks()
            
            mock_request.assert_called_once_with("GET", "https://api.toolrouter.ai/v1/stacks")
            assert len(stacks) == 1
            assert isinstance(stacks[0], Stack)
            assert stacks[0].stack_name == "My Test Stack"
    
    @pytest.mark.asyncio
    async def test_create_stack_success(self):
        """Test successful create_stack call."""
        client = APIClient("test-account-key")
        
        mock_response = {
            "stack_id": "new-stack-123",
            "stack_name": "New Stack",
            "configuration": {"analytics_enabled": False},
            "servers": [],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            stack = await client.create_stack("New Stack", analytics_enabled=False)
            
            mock_request.assert_called_once_with(
                "POST",
                "https://api.toolrouter.ai/v1/stacks",
                data={
                    "stack_name": "New Stack",
                    "configuration": {"analytics_enabled": False}
                }
            )
            assert isinstance(stack, Stack)
            assert stack.stack_name == "New Stack"
    
    @pytest.mark.asyncio
    async def test_list_servers_success(self, mock_servers_response):
        """Test successful list_servers call."""
        client = APIClient("test-account-key")
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_servers_response
            
            servers = await client.list_servers()
            
            mock_request.assert_called_once_with("GET", "https://api.toolrouter.ai/v1/servers")
            assert len(servers) == 1
            assert isinstance(servers[0], Server)
            assert servers[0].name == "GitHub Server"
    
    @pytest.mark.asyncio
    async def test_add_server_to_stack_success(self):
        """Test successful add_server_to_stack call."""
        client = APIClient("test-account-key")
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"message": "success"}
            
            result = await client.add_server_to_stack(
                "stack-123", 
                "server-456",
                enable_all_tools=True
            )
            
            mock_request.assert_called_once_with(
                "POST",
                "https://api.toolrouter.ai/v1/stacks/stack-123/servers",
                data={
                    "server_id": "server-456",
                    "enable_all_tools": True
                }
            )
            assert result is True
    
    @pytest.mark.asyncio
    async def test_get_credentials_status_success(self):
        """Test successful get_credentials_status call."""
        client = APIClient("test-account-key")
        
        mock_response = {
            "required_credentials": {"token": "missing"},
            "optional_credentials": {},
            "all_credentials_added": False,
            "required_credentials_added": False
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            status = await client.get_credentials_status("stack-123", "server-456")
            
            mock_request.assert_called_once_with(
                "GET",
                "https://api.toolrouter.ai/v1/stacks/stack-123/servers/server-456/credentials"
            )
            assert isinstance(status, CredentialsStatus)
            assert not status.all_credentials_added
    
    @pytest.mark.asyncio
    async def test_convenience_method_create_stack_with_server(self, mock_stacks_response):
        """Test convenience method create_stack_with_server."""
        client = APIClient("test-account-key")
        
        # Mock the individual method calls
        with patch.object(client, 'create_stack', new_callable=AsyncMock) as mock_create, \
             patch.object(client, 'add_server_to_stack', new_callable=AsyncMock) as mock_add, \
             patch.object(client, 'update_credentials', new_callable=AsyncMock) as mock_creds, \
             patch.object(client, 'list_stacks', new_callable=AsyncMock) as mock_list:
            
            mock_create.return_value = Stack(**mock_stacks_response[0])
            mock_list.return_value = [Stack(**mock_stacks_response[0])]
            
            stack = await client.create_stack_with_server(
                "Test Stack",
                "server-123", 
                enable_all_tools=True,
                credentials={"token": "test-token"}
            )
            
            # Verify all methods were called
            mock_create.assert_called_once()
            mock_add.assert_called_once()
            mock_creds.assert_called_once()
            mock_list.assert_called_once()
            
            assert isinstance(stack, Stack)


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling across the SDK."""
    
    @pytest.mark.asyncio
    async def test_authentication_error(self):
        """Test AuthenticationError handling."""
        client = DirectAccessClient("invalid", "invalid")
        
        # Mock HTTP response with 401 status
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.is_success = False
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.get.return_value = mock_response
            mock_get_client.return_value = mock_http_client
            
            with pytest.raises(AuthenticationError):
                await client.list_tools()
    
    @pytest.mark.asyncio
    async def test_not_found_error(self):
        """Test NotFoundError handling."""
        client = APIClient("test-key")
        
        # Mock HTTP response with 404 status
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.is_success = False
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.delete.return_value = mock_response
            mock_get_client.return_value = mock_http_client
            
            with pytest.raises(NotFoundError):
                await client.delete_stack("non-existent")
    
    @pytest.mark.asyncio
    async def test_server_error(self):
        """Test ServerError handling."""
        client = DirectAccessClient("test", "test")
        
        # Mock HTTP response with 500 status
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.is_success = False
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.get.return_value = mock_response
            mock_get_client.return_value = mock_http_client
            
            with pytest.raises(ServerError):
                await client.list_tools()


# ============================================================================
# BACKWARD COMPATIBILITY TESTS
# ============================================================================

class TestBackwardCompatibility:
    """Test backward compatibility features."""
    
    def test_toolrouter_alias(self):
        """Test that ToolRouter is an alias for DirectAccessClient."""
        client = ToolRouter("test-client", "test-key")
        assert isinstance(client, DirectAccessClient)
        assert client.client_id == "test-client"
    
    def test_setup_default_router(self):
        """Test setup_default_router function."""
        client = setup_default_router("test-client", "test-key")
        assert isinstance(client, DirectAccessClient)
    
    @patch('toolrouter.client.asyncio.run')
    def test_sync_list_tools(self, mock_run):
        """Test synchronous list_tools function."""
        setup_default_router("test-client", "test-key")
        mock_run.return_value = [{"name": "test"}]
        
        result = list_tools("openai")
        
        mock_run.assert_called_once()
        assert result == [{"name": "test"}]
    
    @patch('toolrouter.client.asyncio.run')
    def test_sync_call_tool(self, mock_run):
        """Test synchronous call_tool function."""
        setup_default_router("test-client", "test-key")
        mock_run.return_value = {"result": "success"}
        
        result = call_tool("test-tool", {"param": "value"})
        
        mock_run.assert_called_once()
        assert result == {"result": "success"}


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for the complete SDK."""
    
    @pytest.mark.asyncio
    async def test_full_account_workflow(self, mock_stacks_response, mock_servers_response):
        """Test a complete account workflow end-to-end."""
        client = APIClient("test-account-key")
        
        # Mock all the API calls
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            # Setup mock responses for different endpoints
            def mock_response_handler(method, url, **kwargs):
                if "stacks" in url and method == "GET":
                    return mock_stacks_response
                elif "servers" in url and method == "GET":
                    return mock_servers_response
                elif "stacks" in url and method == "POST":
                    return mock_stacks_response[0]
                elif "credentials" in url and method == "GET":
                    return {
                        "required_credentials": {"token": "added"},
                        "optional_credentials": {},
                        "all_credentials_added": True,
                        "required_credentials_added": True
                    }
                else:
                    return {"message": "success"}
            
            mock_request.side_effect = mock_response_handler
            
            # Execute workflow
            stacks = await client.list_stacks()
            servers = await client.list_servers()
            stack = await client.create_stack("Test Stack")
            
            if servers:
                await client.add_server_to_stack(
                    stack.stack_id, 
                    servers[0].server_id,
                    enable_all_tools=True
                )
                
                status = await client.get_credentials_status(
                    stack.stack_id,
                    servers[0].server_id
                )
                
                assert status.required_credentials_added
            
            # Verify calls were made
            assert mock_request.call_count >= 4


if __name__ == "__main__":
    pytest.main([__file__]) 