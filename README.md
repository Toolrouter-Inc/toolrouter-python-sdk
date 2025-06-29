# ToolRouter Python SDK

A comprehensive Python client for the ToolRouter API supporting both direct access and account-level operations with full async support and type safety.

## ✨ ToolRouter Key Features

🚀 **Instant Integration** - Deploy Model Control Panels (MCPs) in seconds and seamlessly integrate with your AI agents

🔐 **Authentication Made Simple** - Built-in credential management with secure authentication handling, no manual setup needed

🔄 **Flexible Tool Composition** - Mix and match tools across different MCPs to create powerful custom workflows

🤖 **Universal Model Support** - Compatible with OpenAI, Anthropic, Meta Llama, and all major AI models

🛠️ **Extensive Tool Library** - Access to 450+ production-ready tools across 40+ MCPs, with bi-weekly updates

💪 **Enterprise-Grade Reliability** - Production-tested infrastructure trusted by numerous companies, with continuous improvements

## 🚀 SDK Features

- **Two Client Types**: DirectAccessClient for MCP-style tool calling, APIClient for full account management
- **Full Async Support**: Built with `httpx` for modern async/await patterns
- **Type Safety**: Complete Pydantic models for all API responses
- **Error Handling**: Custom exceptions for different error types
- **Rate Limiting**: Built-in client-side rate limiting
- **Retry Logic**: Automatic retry with exponential backoff
- **Schema Support**: OpenAI, Anthropic, and default schema formats
- **Backward Compatibility**: Maintains compatibility with existing code
- **Production Ready**: Comprehensive error handling, logging, and testing

## 📦 Installation

```bash
pip install toolrouter
```

## 🏃 Quick Start

### Direct Access (MCP-style)

```python
import asyncio
from toolrouter import DirectAccessClient

async def main():
    async with DirectAccessClient(
        client_id="your-client-id",
        api_key="your-api-key",
        schema="openai"  # or "anthropic", "default"
    ) as client:
        
        # List available tools
        tools = await client.list_tools()
        print(f"Available: {len(tools)} tools")
        
        # Call a tool
        if tools:
            result = await client.call_tool(
                tool_name=tools[0]['name'],
                tool_input={"location": "San Francisco"}
            )
            print(f"Result: {result}")

asyncio.run(main())
```

### Account Management

```python
import asyncio
from toolrouter import APIClient

async def main():
    async with APIClient(
        api_key="your-account-api-key",
        schema="openai"
    ) as client:
        
        # Create a stack with server
        stack = await client.create_stack_with_server(
            stack_name="my-ai-stack",
            server_id="github-server",
            enable_all_tools=True,
            credentials={"token": "ghp_your_token"}
        )
        
        # List tools in the stack
        tools = await client.list_stack_tools(stack.stack_id)
        print(f"Stack has {len(tools)} tools available")
        
        # Invoke a tool
        result = await client.invoke_tool(
            stack_id=stack.stack_id,
            tool_id="create_issue",
            tool_input={"title": "Bug report", "body": "Description"}
        )
        print(f"Tool result: {result}")

asyncio.run(main())
```

## 📚 API Documentation

### Available Methods

#### DirectAccessClient (MCP-Style)

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `list_tools()` | Get available tools from ToolRouter | `schema: Optional[str]` | `List[Union[Tool, Dict[str, Any]]]` |
| `call_tool()` | Call a tool using ToolRouter | `tool_name: str, tool_input: Dict[str, Any]` | `Dict[str, Any]` |

#### APIClient (Account Level API)

##### Stack Management
| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `list_stacks()` | List all stacks | None | `List[Stack]` |
| `create_stack()` | Create a new stack | `stack_name: str, analytics_enabled: bool = False` | `Stack` |
| `update_stack()` | Update an existing stack | `stack_id: str, stack_name: Optional[str] = None, analytics_enabled: Optional[bool] = None` | `Stack` |
| `delete_stack()` | Delete a stack | `stack_id: str` | `bool` |

##### Server Management
| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `list_servers()` | List all available servers | None | `List[Server]` |
| `add_server_to_stack()` | Add a server to a stack | `stack_id: str, server_id: str, enable_all_tools: bool = False, enabled_tools: Optional[List[str]] = None` | `bool` |
| `remove_server_from_stack()` | Remove a server from a stack | `stack_id: str, server_id: str` | `bool` |
| `update_server_tools()` | Update enabled tools for a server | `stack_id: str, server_id: str, enabled_tools: List[str]` | `bool` |

##### Credential Management
| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `get_credentials_status()` | Get credentials status for a server | `stack_id: str, server_id: str` | `CredentialsStatus` |
| `update_credentials()` | Update credentials for a server | `stack_id: str, server_id: str, credentials: Dict[str, str]` | `bool` |

##### Tool Operations
| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `list_stack_tools()` | List tools available in a stack | `stack_id: str, schema: Optional[str] = None` | `List[Union[Tool, Dict[str, Any]]]` |
| `invoke_tool()` | Invoke a tool in a stack | `stack_id: str, tool_id: str, tool_input: Dict[str, Any]` | `Dict[str, Any]` |

##### Convenience Methods
| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `create_stack_with_server()` | Create stack and add server in one call | `stack_name: str, server_id: str, enable_all_tools: bool = True, analytics_enabled: bool = False, credentials: Optional[Dict[str, str]] = None` | `Stack` |
| `get_stack_summary()` | Get comprehensive stack summary | `stack_id: str` | `Dict[str, Any]` |

#### Backward Compatibility Functions
| Function | Description | Parameters | Returns |
|----------|-------------|------------|---------|
| `setup_default_router()` | Configure the default direct access client | `client_id: str, api_key: str, base_url: str = "https://api.toolrouter.ai/s", **kwargs` | `DirectAccessClient` |
| `list_tools()` | Sync wrapper for list_tools (uses default client) | `schema: str = "openai"` | `List[Union[Tool, Dict[str, Any]]]` |
| `call_tool()` | Sync wrapper for call_tool (uses default client) | `tool_name: str, tool_input: Dict[str, Any]` | `Dict[str, Any]` |

### Usage Examples

#### DirectAccessClient

For MCP-style direct tool access:

```python
from toolrouter import DirectAccessClient

client = DirectAccessClient(
    client_id="your-client-id",
    api_key="your-api-key",
    base_url="https://api.toolrouter.ai/s",  # optional
    schema="openai",  # or "anthropic", "default"
    timeout=30.0,
    max_retries=3,
    rate_limit_requests=60,
    rate_limit_window=60
)

# List tools
tools = await client.list_tools(schema="openai")

# Call tool
result = await client.call_tool("tool_name", {"param": "value"})
```

#### APIClient

For full account and stack management:

```python
from toolrouter import APIClient

client = APIClient(
    api_key="your-account-api-key",
    base_url="https://api.toolrouter.ai/v1",  # optional
    schema="openai",
    timeout=30.0,
    max_retries=3
)

# Stack operations
stacks = await client.list_stacks()
stack = await client.create_stack("My Stack", analytics_enabled=True)
await client.update_stack(stack.stack_id, stack_name="Updated Name")
await client.delete_stack(stack.stack_id)

# Server operations
servers = await client.list_servers()
await client.add_server_to_stack(stack_id, server_id, enable_all_tools=True)
await client.remove_server_from_stack(stack_id, server_id)
await client.update_server_tools(stack_id, server_id, ["tool1", "tool2"])

# Credential management
status = await client.get_credentials_status(stack_id, server_id)
await client.update_credentials(stack_id, server_id, {"api_key": "secret"})

# Tool operations
tools = await client.list_stack_tools(stack_id, schema="openai")
result = await client.invoke_tool(stack_id, tool_id, {"param": "value"})

# Convenience methods
stack = await client.create_stack_with_server(
    "Stack Name", "server-id", 
    enable_all_tools=True,
    credentials={"token": "secret"}
)
summary = await client.get_stack_summary(stack_id)
```

## 🔧 Configuration

### Environment Variables

```bash
export TOOLROUTER_CLIENT_ID="your-client-id"
export TOOLROUTER_API_KEY="your-api-key"
export TOOLROUTER_ACCOUNT_API_KEY="your-account-api-key"
```

### Client Configuration

```python
# Custom configuration
client = DirectAccessClient(
    client_id="your-client-id",
    api_key="your-api-key",
    timeout=60.0,           # Request timeout
    max_retries=5,          # Retry attempts
    rate_limit_requests=100, # Requests per window
    rate_limit_window=60     # Window in seconds
)
```

## 🚨 Error Handling

The SDK provides specific exception types:

```python
from toolrouter import (
    ToolRouterError,        # Base exception
    AuthenticationError,    # Invalid credentials
    NotFoundError,         # Resource not found
    ValidationError,       # Invalid request
    ServerError,          # Server-side error
    RateLimitError        # Rate limit exceeded
)

try:
    result = await client.call_tool("tool_name", {})
except AuthenticationError:
    print("Check your API key")
except NotFoundError:
    print("Tool or resource not found")
except RateLimitError:
    print("Rate limit exceeded, slow down")
except ToolRouterError as e:
    print(f"General error: {e.message} (Status: {e.status_code})")
```

## 🔄 Backward Compatibility

Existing code continues to work:

```python
# Old synchronous API still works
from toolrouter import ToolRouter, setup_default_router, list_tools, call_tool

setup_default_router("client-id", "api-key")
tools = list_tools(schema="openai")
result = call_tool("tool_name", {"param": "value"})

# ToolRouter class is now an alias for DirectAccessClient
client = ToolRouter("client-id", "api-key")  # Same as DirectAccessClient
```

## 🏗️ Architecture

```
toolrouter/
├── client.py              # Main SDK implementation
│   ├── BaseClient         # Shared functionality
│   ├── DirectAccessClient # MCP-style tool calling
│   ├── APIClient         # Account management
│   ├── Exception classes # Custom error types
│   └── Pydantic models   # Type safety
├── __init__.py           # Public API exports
├── examples.py           # Comprehensive examples
└── tests/                # Test suite
    └── test_toolrouter.py
```

## 🧪 Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=toolrouter
```

### Code Quality

```bash
# Format code
black toolrouter/

# Sort imports
isort toolrouter/

# Lint
flake8 toolrouter/
```

## 📋 Examples

Check out `examples.py` for comprehensive usage examples including:

- Basic DirectAccessClient usage
- Complete APIClient workflows
- Credential management
- Error handling patterns
- Convenience methods
- Backward compatibility

## 📝 Changelog

### v0.2.0
- ✨ Added APIClient for account-level operations
- ✨ Full async support with httpx
- ✨ Type safety with Pydantic models
- ✨ Custom exception hierarchy
- ✨ Built-in rate limiting and retries
- ✨ Support for multiple schema formats
- ✨ Convenience methods for common workflows
- 🔄 Maintained backward compatibility

### v0.1.0
- 🎉 Initial release with DirectAccessClient

## 📄 License

Apache 2.0 License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📞 Support

- Documentation: [https://docs.toolrouter.ai](https://docs.toolrouter.ai)
- Issues: [GitHub Issues](https://github.com/Toolrouter-Inc/toolrouter-python-sdk/issues)
- Email: admin@toolrouter.ai 