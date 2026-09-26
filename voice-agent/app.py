"""Brightside Dental voice agent server.

Run:  python app.py   then open http://localhost:5050 in Chrome or Edge.
"""

import json
import os
import uuid

import anthropic
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

from prompt import GREETING, build_system_prompt
from tools import TOOLS, run_tool

load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    raise SystemExit("Missing ANTHROPIC_API_KEY. Copy .env.example to .env and add your key.")

# Haiku is fastest, which matters a lot for voice. Set CLAUDE_MODEL in .env to switch.
MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
PORT = int(os.getenv("PORT", "5050"))
MAX_TOOL_ROUNDS = 6
ENDING_TOOLS = {"transfer_to_staff", "end_call"}

client = anthropic.Anthropic()
app = Flask(__name__, static_folder="static")

# session_id -> conversation history. In-memory only: restarting the server clears it.
SESSIONS: dict[str, list] = {}


def run_turn(history: list) -> dict:
    """Send the conversation to Claude, run any tools it calls, and return what to say."""
    spoken, tool_log, ended_by = [], [], None

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=400,
            system=build_system_prompt(),
            tools=TOOLS,
            messages=history,
        )

        assistant_blocks, tool_results = [], []
        for block in response.content:
            if block.type == "text" and block.text.strip():
                spoken.append(block.text.strip())
                assistant_blocks.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_blocks.append(
                    {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
                )
                result = run_tool(block.name, block.input)
                print(f"  [tool] {block.name}({block.input}) -> {result}")
                tool_log.append({"name": block.name, "input": block.input, "result": result})
                if block.name in ENDING_TOOLS:
                    ended_by = block.name
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)}
                )

        if assistant_blocks:
            history.append({"role": "assistant", "content": assistant_blocks})

        if response.stop_reason != "tool_use" or not tool_results or ended_by:
            break  # no need for another round trip once the call is over
        history.append({"role": "user", "content": tool_results})
    else:
        spoken.append("Sorry, I'm having trouble with that. I'll have someone from the office call you back.")

    return {"reply": " ".join(spoken), "tool_calls": tool_log, "call_ended": ended_by}


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/start")
def start_call():
    session_id = uuid.uuid4().hex
    # The API needs the conversation to start with a user turn, so we mark the call connecting.
    SESSIONS[session_id] = [
        {"role": "user", "content": "[Phone call connected]"},
        {"role": "assistant", "content": GREETING},
    ]
    print(f"\n=== New call {session_id[:8]} ===\n  Maya: {GREETING}")
    return jsonify({"session_id": session_id, "reply": GREETING})


@app.post("/api/message")
def message():
    data = request.get_json(silent=True) or {}
    history = SESSIONS.get(data.get("session_id", ""))
    text = (data.get("text") or "").strip()
    if history is None:
        return jsonify({"error": "Call not found. Start a new call."}), 404
    if not text:
        return jsonify({"error": "Empty message."}), 400

    checkpoint = len(history)
    history.append({"role": "user", "content": text})
    print(f"  Caller: {text}")
    try:
        result = run_turn(history)
    except anthropic.APIError as exc:
        del history[checkpoint:]  # roll back so the conversation stays valid
        print(f"  [error] {exc}")
        return jsonify({"error": f"Claude API error: {exc}"}), 502

    print(f"  Maya: {result['reply']}")
    if result["call_ended"]:
        SESSIONS.pop(data["session_id"], None)
        print("=== Call ended ===")
    return jsonify(result)


if __name__ == "__main__":
    print(f"Voice agent running with {MODEL}")
    print(f"Open http://localhost:{PORT} in Chrome or Edge")
    app.run(host="127.0.0.1", port=PORT, debug=False)
