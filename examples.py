"""
Comprehensive examples for the ToolRouter Python SDK.

This file demonstrates both DirectAccessClient and APIClient usage patterns
with real-world workflows and best practices.
"""

import asyncio
from toolrouter import (
    DirectAccessClient,
    APIClient,
    ToolRouter,  # Backward compatibility
    setup_default_router,
    list_tools,
    call_tool,
    ToolRouterError,
    AuthenticationError,
    NotFoundError
)

# ============================================================================
# DIRECT ACCESS CLIENT EXAMPLES
# ============================================================================

async def direct_access_basic_example():
    """Basic usage of DirectAccessClient with async/await."""
    
    print("🔧 Direct Access Client - Basic Example")
    print("=" * 50)
    
    # Initialize client
    async with DirectAccessClient(
        client_id="your-client-id",
        api_key="your-api-key",
        schema="openai"  # or "anthropic", "default"
    ) as client:
        
        try:
            # List available tools
            print("📋 Available tools:")
            tools = await client.list_tools()
            for tool in tools[:3]:  # Show first 3 tools
                print(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')[:60]}...")
            
            # Call a tool (example with weather tool)
            if tools:
                tool_name = tools[0]['name']
                print(f"\n🌟 Calling tool: {tool_name}")
                
                # Example tool input - adjust based on actual tool requirements
                result = await client.call_tool(
                    tool_name=tool_name,
                    tool_input={"location": "San Francisco"}
                )
                print(f"✅ Result: {result}")
                
        except AuthenticationError:
            print("❌ Authentication failed - check your client_id and api_key")
        except ToolRouterError as e:
            print(f"❌ ToolRouter error: {e.message}")


async def direct_access_with_different_schemas():
    """Demonstrate using different schema formats."""
    
    print("\n🔄 Direct Access Client - Schema Formats")
    print("=" * 50)
    
    async with DirectAccessClient(
        client_id="your-client-id",
        api_key="your-api-key"
    ) as client:
        
        try:
            # Test different schemas
            schemas = ["openai", "anthropic", "default"]
            
            for schema in schemas:
                print(f"\n📊 Tools in {schema} format:")
                tools = await client.list_tools(schema=schema)
                if tools:
                    first_tool = tools[0]
                    print(f"  Example tool structure: {list(first_tool.keys())}")
                else:
                    print("  No tools available")
                    
        except Exception as e:
            print(f"❌ Error: {e}")


# ============================================================================
# ACCOUNT API CLIENT EXAMPLES  
# ============================================================================

async def account_api_basic_workflow():
    """Complete workflow using APIClient - stacks, servers, tools."""
    
    print("\n🏗️ Account API Client - Complete Workflow")
    print("=" * 50)
    
    async with APIClient(
        api_key="your-account-api-key",
        schema="openai"
    ) as client:
        
        try:
            # 1. List existing stacks
            print("📚 Existing stacks:")
            stacks = await client.list_stacks()
            for stack in stacks:
                print(f"  - {stack.stack_name} ({stack.stack_id}): {len(stack.servers)} servers")
            
            # 2. List available servers
            print("\n🖥️ Available servers:")
            servers = await client.list_servers()
            for server in servers[:3]:  # Show first 3
                print(f"  - {server.name}: {len(server.tools)} tools, {len(server.required_credentials)} required credentials")
            
            if not servers:
                print("  No servers available")
                return
                
            # 3. Create a new stack
            print(f"\n➕ Creating new stack...")
            stack = await client.create_stack(
                stack_name=f"demo-stack-{asyncio.get_event_loop().time():.0f}",
                analytics_enabled=True
            )
            print(f"✅ Created stack: {stack.stack_name} ({stack.stack_id})")
            
            # 4. Add a server to the stack
            first_server = servers[0]
            print(f"\n🔗 Adding server '{first_server.name}' to stack...")
            await client.add_server_to_stack(
                stack_id=stack.stack_id,
                server_id=first_server.server_id,
                enable_all_tools=True
            )
            print("✅ Server added successfully")
            
            # 5. Check credentials status
            print(f"\n🔐 Checking credentials status...")
            cred_status = await client.get_credentials_status(
                stack_id=stack.stack_id,
                server_id=first_server.server_id
            )
            print(f"  Required credentials added: {cred_status.required_credentials_added}")
            print(f"  All credentials added: {cred_status.all_credentials_added}")
            
            # 6. List tools in the stack
            print(f"\n🛠️ Tools available in stack:")
            tools = await client.list_stack_tools(stack.stack_id)
            for tool in tools[:3]:  # Show first 3
                print(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')[:60]}...")
            
            # 7. Get stack summary
            print(f"\n📊 Stack summary:")
            summary = await client.get_stack_summary(stack.stack_id)
            print(f"  Total tools: {summary['total_tools']}")
            print(f"  Servers configured: {summary['servers_configured']}")
            
            # 8. Cleanup - delete the demo stack
            print(f"\n🗑️ Cleaning up demo stack...")
            await client.delete_stack(stack.stack_id)
            print("✅ Demo stack deleted")
            
        except NotFoundError as e:
            print(f"❌ Resource not found: {e.message}")
        except ToolRouterError as e:
            print(f"❌ ToolRouter error: {e.message}")


async def account_api_convenience_methods():
    """Demonstrate convenience methods for common workflows."""
    
    print("\n⚡ Account API Client - Convenience Methods")
    print("=" * 50)
    
    async with APIClient(api_key="your-account-api-key") as client:
        
        try:
            # List available servers to pick one
            servers = await client.list_servers()
            if not servers:
                print("❌ No servers available")
                return
                
            first_server = servers[0]
            
            # Use convenience method to create stack with server in one call
            print(f"🚀 Creating stack with server in one call...")
            stack = await client.create_stack_with_server(
                stack_name=f"convenience-stack-{asyncio.get_event_loop().time():.0f}",
                server_id=first_server.server_id,
                enable_all_tools=True,
                analytics_enabled=True,
                credentials={"api_key": "demo-key"}  # Only if server needs credentials
            )
            print(f"✅ Stack created: {stack.stack_name}")
            
            # Use convenience method to get comprehensive stack info
            print(f"\n📈 Getting comprehensive stack summary...")
            summary = await client.get_stack_summary(stack.stack_id)
            print(f"  Stack: {summary['stack'].stack_name}")
            print(f"  Total tools: {summary['total_tools']}")
            print(f"  Servers configured: {summary['servers_configured']}")
            
            # Cleanup
            await client.delete_stack(stack.stack_id)
            print("✅ Cleanup completed")
            
        except Exception as e:
            print(f"❌ Error: {e}")


async def account_api_credential_management():
    """Demonstrate credential management workflow."""
    
    print("\n🔑 Account API Client - Credential Management")
    print("=" * 50)
    
    async with APIClient(api_key="your-account-api-key") as client:
        
        try:
            # Find a server that requires credentials
            servers = await client.list_servers()
            server_with_creds = None
            
            for server in servers:
                if server.required_credentials or server.optional_credentials:
                    server_with_creds = server
                    break
            
            if not server_with_creds:
                print("ℹ️ No servers found that require credentials")
                return
            
            print(f"🔍 Found server with credentials: {server_with_creds.name}")
            print(f"  Required credentials: {[c.name for c in server_with_creds.required_credentials]}")
            print(f"  Optional credentials: {[c.name for c in server_with_creds.optional_credentials]}")
            
            # Create a stack and add the server
            stack = await client.create_stack(f"cred-demo-{asyncio.get_event_loop().time():.0f}")
            await client.add_server_to_stack(
                stack.stack_id, 
                server_with_creds.server_id,
                enable_all_tools=True
            )
            
            # Check initial credential status
            status = await client.get_credentials_status(stack.stack_id, server_with_creds.server_id)
            print(f"\n📋 Initial credential status:")
            print(f"  Required credentials added: {status.required_credentials_added}")
            
            # Set some demo credentials (adjust field names based on actual server)
            if server_with_creds.required_credentials:
                demo_creds = {}
                for cred in server_with_creds.required_credentials[:2]:  # Just first 2
                    demo_creds[cred.field_id] = f"demo-{cred.field_id}-value"
                
                print(f"\n🔐 Setting credentials...")
                await client.update_credentials(
                    stack.stack_id,
                    server_with_creds.server_id,
                    demo_creds
                )
                
                # Check updated status
                status = await client.get_credentials_status(stack.stack_id, server_with_creds.server_id)
                print(f"✅ Updated credential status:")
                print(f"  Required credentials added: {status.required_credentials_added}")
            
            # Cleanup
            await client.delete_stack(stack.stack_id)
            print("✅ Cleanup completed")
            
        except Exception as e:
            print(f"❌ Error: {e}")


# ============================================================================
# BACKWARD COMPATIBILITY EXAMPLES
# ============================================================================

def backward_compatibility_example():
    """Demonstrate backward compatibility with synchronous API."""
    
    print("\n🔄 Backward Compatibility - Synchronous API")
    print("=" * 50)
    
    try:
        # Setup using the old method
        setup_default_router(
            client_id="your-client-id",
            api_key="your-api-key"
        )
        
        # Use old synchronous functions
        print("📋 Getting tools (sync)...")
        tools = list_tools(schema="openai")
        print(f"Found {len(tools)} tools")
        
        if tools:
            # Call a tool using old method
            tool_name = tools[0]['name']
            print(f"🔧 Calling {tool_name} (sync)...")
            # result = call_tool(tool_name, {"param": "value"})
            # print(f"Result: {result}")
        
        # Also demonstrate the ToolRouter class (alias)
        print("\n🏗️ Using ToolRouter class (backward compatible)...")
        toolr = ToolRouter(
            client_id="your-client-id",
            api_key="your-api-key"
        )
        # This is actually a DirectAccessClient instance
        print(f"ToolRouter class type: {type(toolr).__name__}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


# ============================================================================
# ERROR HANDLING EXAMPLES
# ============================================================================

async def error_handling_examples():
    """Demonstrate proper error handling patterns."""
    
    print("\n🚨 Error Handling Examples")
    print("=" * 50)
    
    # Example 1: Authentication Error
    try:
        async with DirectAccessClient(
            client_id="invalid-id",
            api_key="invalid-key"
        ) as client:
            await client.list_tools()
    except AuthenticationError as e:
        print(f"✅ Caught authentication error: {e.message}")
    
    # Example 2: Not Found Error
    try:
        async with APIClient(api_key="your-account-api-key") as client:
            await client.delete_stack("non-existent-stack-id")
    except NotFoundError as e:
        print(f"✅ Caught not found error: {e.message}")
    
    # Example 3: General ToolRouter Error
    try:
        async with APIClient(api_key="invalid-key") as client:
            await client.list_stacks()
    except ToolRouterError as e:
        print(f"✅ Caught general error: {e.message} (Status: {e.status_code})")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def run_all_examples():
    """Run all async examples."""
    
    print("🚀 ToolRouter Python SDK Examples")
    print("=" * 60)
    
    # Note: Replace API keys with your actual credentials
    print("ℹ️ Remember to replace 'your-client-id', 'your-api-key', and 'your-account-api-key' with actual values")
    
    # Direct Access Examples
    # await direct_access_basic_example()
    # await direct_access_with_different_schemas()
    
    # Account API Examples  
    # await account_api_basic_workflow()
    # await account_api_convenience_methods()
    # await account_api_credential_management()
    
    # Error Handling
    # await error_handling_examples()
    
    print("\n✨ All examples completed!")


def main():
    """Main entry point."""
    # Run backward compatibility example (synchronous)
    backward_compatibility_example()
    
    # Run async examples
    asyncio.run(run_all_examples())


if __name__ == "__main__":
    main() 