import os
import openai
import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
os.environ['OPENAI_API_KEY'] = os.getenv('OPEN_API_KEY_GPT_4.1')
os.environ["OPENAI_API_BASE"]=os.getenv("OPENAI_API_BASE")

# Learn MCP Server is public—no auth needed
MS_LEARN_MCP_URL = "https://learn.microsoft.com/api/mcp"
MCP_SERVER_LABEL = "mslearn"

SYSTEM = (
    "You are an expert assistant about Microsoft services. "
    "You can call the MSP docs tool to retrieve official documentation snippets."
)
USER_PROMPT = "Ask me anything about Microsoft cloud, 365, Azure, Power Platform, Teams, etc."

def make_tool_descriptor():
    return {
        "type": "mcp",
        "server_label": MCP_SERVER_LABEL,
        "server_url": MS_LEARN_MCP_URL,
        "require_approval": "prompt"
        # Captures tool results into the model while limiting surprises
    }

def build_message_history():
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user",   "content": USER_PROMPT},
    ]

def ask_question(prompt: str, history=None):
    """Send user question + tool to Responses API, return answer text."""
    if history is None:
        history = build_message_history()
    history.append({"role": "user", "content": prompt})
    openai = OpenAI(
            base_url=os.getenv("OPENAI_API_BASE"),
            api_key=os.getenv("OPENAI_API_KEY")
        )
    r = openai.chat.completions.create(
        model="gpt-4.1",
        messages=history,
        tools=[make_tool_descriptor()],
        tool_choice="auto"
    )

    return r

def pretty_print_response(resp):
    # resp.output_text is explanation, including citations
    print("\n=== Answer ===\n")
    print(resp.output_text.strip())
    # reasoning_summary may include chain-of-thought stripped for privacy
    if getattr(resp, "reasoning_summary", None):
        print("\n— reasoning_summary:", resp.reasoning_summary.strip())

def main():
    print(f"Microsoft Docs MCP agent — session started at {datetime.datetime.now()}\n")
    while True:
        q = input("\nYour question (or 'exit'): ").strip()
        if not q or q.lower() in ("exit", "quit"):
            print("Goodbye!")
            return
        resp = ask_question(q)
        pretty_print_response(resp)

if __name__ == "__main__":
    main()
