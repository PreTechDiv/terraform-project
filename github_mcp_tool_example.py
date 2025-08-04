import os
import sys
import json
import requests
from typing import Any, Mapping
from dotenv import load_dotenv

load_dotenv()

# ── CONFIGURE HERE ─────────────────────────────────────────────────────────
OWNER = "PreTechDiv"         # e.g. "octocat"
REPO = "terraform-project"              # e.g. "hello-world"
# Set this via environment:  'GITHUB_COPILOT_TOKEN' or 'GITHUB_PERSONAL_ACCESS_TOKEN'
# You can paste the token into environment only, never commit it into code.
TOKEN_EVNAMES = ["GITHUB_MCP_TOKEN_CLASSIC", "GITHUB_MCP_TOKEN_FINE_GRAINED"]
# ---------------------------------------------------------------------------

import os
import requests
import json

# ── CONFIG ──────────────────────────────────────────────────────────────────────
BASE_URL = "https://api.githubcopilot.com/mcp/"
TOKEN = os.getenv("GITHUB_MCP_TOKEN_CLASSIC") or os.getenv("GITHUB_MCP_TOKEN_FINE_GRAINED", "")
assert TOKEN, "set GITHUB_PERSONAL_ACCESS_TOKEN"
AUTH = f"Bearer {TOKEN}"
# ────────────────────────────────────────────────────────────────────────────────

def mcp_initialize():
    payload = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    headers = {
        "Authorization": AUTH,
        "Content-Type": "application/json",
    }
    resp = requests.post(BASE_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    session_id = resp.headers.get("Mcp-Session-Id")
    if not session_id or not session_id.strip():
        raise RuntimeError("GitHub MCP server did not send a session ID")
    return session_id

def mcp_list_issues(session_id, owner, repo, state="open", perPage=20):
    args = {"owner": owner, "repo": repo, "state": state, "perPage": perPage}
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    # list the available tools
    resp = requests.post(BASE_URL, headers={
        "Authorization": AUTH,
        "Mcp-Session-Id": session_id,
        "Content-Type": "application/json",
    }, json=req, timeout=30)
    resp.raise_for_status()
    tools = resp.json().get("result", {}).get("tools", [])
    print("available set of tools ---------------------- ")
    print(tools)

    if not any(t.get("name") == "list_issues" for t in tools):
        raise RuntimeError("`list_issues` tool not available in returned tools")
    print("Available tools includes `list_issues` ✔")

    # now call list_issues
    call_req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "list_issues", "arguments": args}
    }
    resp2 = requests.post(BASE_URL, headers={
        "Authorization": AUTH,
        "Mcp-Session-Id": session_id,
        "Content-Type": "application/json",
    }, json=call_req, timeout=60)
    resp2.raise_for_status()
    call_res = resp2.json().get("result", {})
    content = call_res.get("content", [])
    # usually first item is the JSON payload as text
    text = content[0].get("text", "{}")
    return json.loads(text)

if __name__ == "__main__":
    sid = mcp_initialize()
    print("Session ID:", sid)
    owner = OWNER
    repo = REPO
    issues = mcp_list_issues(sid, owner, repo, state="open", perPage=5)
    for issue in issues:
        print(f"- #{issue['number']} {issue['title']}")
