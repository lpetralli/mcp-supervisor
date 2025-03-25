from contextlib import asynccontextmanager
import os
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

# Define the model
model = ChatOpenAI(model="gpt-4o")

@asynccontextmanager
async def make_graph():
    # Configure MCP clients for different services
    async with MultiServerMCPClient(
        {
            "zapier": {
                "url": os.environ.get("ZAPIER_MCP_URL"),
                "transport": "sse",
            }
        }
    ) as mcp_client:
        # Get MCP tools
        mcp_tools = mcp_client.get_tools()
        
        # Create agents with both custom and MCP tools
        calendar_agent = create_react_agent(
            model=model,
            tools=mcp_tools,
            name="calendar_agent",
            prompt="You are a calendar agent responsible for managing calendar events and scheduling. You have access to tools that can create, modify, and view calendar events. Always use one tool at a time and only when necessary."
        )

        mail_agent = create_react_agent(
            model=model,
            tools= mcp_tools,
            name="mail_agent",
            prompt="You are a mail agent responsible for managing email communications. You have access to tools that can create and manage email drafts. Always use one tool at a time and only when necessary. Follow best practices for email management."
        )

        # Create supervisor workflow
        workflow = create_supervisor(
            [calendar_agent, mail_agent],
            model=model,
            output_mode="last_message",  # "full_history"
            prompt=(
                "You are a personal assistant that helps manage emails and calendar events. "
                "You are in charge of the team and responsible for chatting directly with the user. "
                "For scheduling and managing calendar events, delegate to calendar_agent. "
                "For composing and managing emails, delegate to mail_agent. "
                "The subagents only answer to you, and you are the one delivering the final message that the user sees. "
                "Ensure your responses are helpful, clear, and maintain a consistent voice for the user experience."
            )
        )
        
        # Compile and yield the workflow
        app = workflow.compile()
        yield app
        