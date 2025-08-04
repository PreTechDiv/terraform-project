# from mcp import ClientSession
# from mcp.client.sse import sse_client
# from azure.ai.inference import ChatCompletionsClient
# from azure.ai.inference.models import SystemMessage, UserMessage
# from azure.core.credentials import AzureKeyCredential
# import os

# endpoint = "https://models.github.ai/inference"
# model = "openai/gpt-4.1"
# token = os.eniron('GPT_4.1_TOKEN)

# async def run():
#     async with sse_client(url="http://localhost:8000/sse") as streams:
#         async with ClientSession(*streams) as session:
#             await session.initialize()

#             tools = await session.list_tools()
#             print(tools)

#             result = await session.call_tool("add", arguments={"a":4 , "b":5})
#             # print(result)

#     # client = ChatCompletionsClient(
#     #     endpoint=endpoint,
#     #     credential=AzureKeyCredential(token),
#     # )

#     # response = client.complete(
#     #     messages=[
#     #         SystemMessage("You are a helpful assistant."),
#     #         UserMessage("What is the weather of france"),
#     #     ],
#     #     temperature=1.0,
#     #     top_p=1.0,
#     #     model=model,
#     #     tools = tools
#     # )

#     # print(response.choices[0].message.content)

# if __name__=="__main__":
#     import asyncio
#     asyncio.run(run())


import asyncio
from typing import Optional, Dict
from contextlib import AsyncExitStack


from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()  # load environment variables from .env
import os

# Set the environment variable directly
OPENAI_API_BASE=os.environ["OPENAI_API_BASE"]
GITHUB_MCP_TOKEN_FINE_GRAINED = os.environ['GITHUB_MCP_TOKEN_FINE_GRAINED']
GITHUB_MCP_TOKEN_CLASSIC = os.environ['GITHUB_MCP_TOKEN_CLASSIC']

GITHUB_MCP_URL = os.environ('GITHUB_MCP_URL')  # Or your actual endpoint
MICROSOFT_MCP_URL=os.environ('MICROSOFT_MCP_URL')

class MCPClient:
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.tool_to_session: Dict[str, str] = {}
        self.exit_stack = AsyncExitStack()
        self.openai = OpenAI(
            base_url=os.getenv("OPENAI_API_BASE"),
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.all_tools = []


    async def connect_to_servers(self, server_script_path: str):
        # Connect to local stdio server
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
        print('we are here at line 89')
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        print('we are here at line 96 stdion client')
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio_session = await self.exit_stack.enter_async_context(ClientSession(*stdio_transport))
        await stdio_session.initialize()
        self.sessions["local"] = stdio_session

        # Connect to GitHub MCP server
        print('we are here at line 103 github connection')
        headers = {
        "Authorization": f"Bearer {GITHUB_MCP_TOKEN_CLASSIC}"
        }
        sse_transport = await self.exit_stack.enter_async_context(sse_client(GITHUB_MCP_URL , headers=headers))
        # sse_transport = await self.exit_stack.enter_async_context(sse_client(MICROSOFT_MCP_URL))
        print('we are here at line 108 before github session')
        github_session = await self.exit_stack.enter_async_context(ClientSession(*sse_transport))
        print('we are here at line 110 before git hub session initialization')
        await github_session.initialize()
        print('we are here at line 112 after git hub session initialization')
        self.sessions["github"] = github_session
        print("GitHub MCP tools:", [tool.name for tool in github_session.list_tools()])


        # Merge tools and map tool names to sessions
        self.tool_to_session = {}
        all_tools = []
        for name, session in self.sessions.items():
            response = await session.list_tools()
            for tool in response.tools:
                self.tool_to_session[tool.name] = name
                all_tools.append(tool)
        print("\nConnected to servers with tools:", [tool.name for tool in all_tools])
        self.all_tools = all_tools

    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in self.all_tools]

        response = self.openai.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            tools=available_tools,
            tool_choice="auto",
        )

        final_text = []
        while True:
            reply = response.choices[0].message
            if reply.content and not reply.tool_calls:
                final_text.append(reply.content)
                messages.append({"role": "assistant", "content": reply.content})

            if reply.tool_calls:
                messages.append({
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        }
                        for tool_call in reply.tool_calls
                    ]
                })
                for tool_call in reply.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments
                    parsed_args = json.loads(tool_args)
                    session_name = self.tool_to_session[tool_name]
                    session = self.sessions[session_name]
                    result = await session.call_tool(tool_name, parsed_args)
                    final_text.append(f"[Calling tool {tool_name} with args {parsed_args}]")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": result.content,
                    })
                response = self.openai.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                )
            else:
                break
        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()



async def main():
    # if len(sys.argv) < 2:
    #     print("Usage: python client.py <path_to_server_script>")
    #     sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_servers(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys
    asyncio.run(main())