"""The two ways of running a task (plus one ablation).

single_shot             one model call; every tool call must be in that one
                        reply; the model never sees tool results.
react                   LangGraph ReAct loop: agent -> (tools -> agent)* -> END.
                        The tool node validates each call against the schema
                        and returns errors to the model as ToolMessages, so it
                        can correct itself.
react_no_error_feedback same graph, but the first invalid call ends the run.
                        This mimics the upstream tutorial's tool node, which
                        has no error handling (an unknown tool name raises
                        KeyError and the run crashes).

Every run returns a trace dict: attempts, per-turn latency/tokens, messages,
final text, stop reason.
"""

from __future__ import annotations

import json
import operator
import time
from typing import Annotated, Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from .scoring import execute_call, text_json_calls, validate_call
from .tools import TOOLS

MODES = ("single_shot", "react", "react_no_error_feedback")

BASE_PROMPT = (
    "You are a helpful assistant that can call tools.\n"
    "Use a tool whenever the request needs arithmetic, weather, currency conversion, "
    "employee directory data, or a reminder. Do not do arithmetic in your head and do "
    "not guess data. For general-knowledge questions or chit-chat, answer directly "
    "without calling any tool."
)
SINGLE_SHOT_SUFFIX = (
    "\nYou get exactly ONE response and will not see any tool results. Put every tool "
    "call the request needs into this single response."
)
REACT_SUFFIX = (
    "\nYou can work over several turns: call a tool, read its result, then call more "
    "tools or give the final answer. For multi-step requests, do one step at a time and "
    "use each result. When you are done, reply with a short final answer that states "
    "the result."
)


def make_llm(model: str, base_url: str, num_ctx: int = 4096, seed: int = 42):
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=model, base_url=base_url, temperature=0.0, num_ctx=num_ctx,
        seed=seed, num_predict=512, keep_alive="30m",
    )


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _invoke_with_retry(llm, messages, retries: int = 3):
    last = None
    for i in range(retries):
        try:
            t0 = time.perf_counter()
            msg = llm.invoke(messages)
            return msg, time.perf_counter() - t0
        except Exception as e:  # connection hiccup, server restart ...
            last = e
            time.sleep(2 * (i + 1))
    raise last


def _turn_info(msg: AIMessage, latency: float) -> dict:
    md = getattr(msg, "response_metadata", {}) or {}
    return {
        "latency_s": round(latency, 3),
        "eval_count": md.get("eval_count"),             # output tokens
        "prompt_eval_count": md.get("prompt_eval_count"),  # input tokens
        "n_tool_calls": len(msg.tool_calls or []),
    }


def _parse_failures(msg: AIMessage, turn: int) -> list[dict]:
    """Attempts that never became structured calls."""
    out = []
    for bad in getattr(msg, "invalid_tool_calls", None) or []:
        out.append({"turn": turn, "source": "invalid_tool_call", "name": bad.get("name"),
                    "raw_args": bad.get("args"), "status": "parse_error",
                    "error": bad.get("error") or "could not parse tool call", "args": None,
                    "type_drift": []})
    if not msg.tool_calls:  # JSON written into the text instead of a real call
        for name in text_json_calls(msg.content if isinstance(msg.content, str) else str(msg.content)):
            out.append({"turn": turn, "source": "text_json", "name": name, "raw_args": None,
                        "status": "parse_error",
                        "error": "tool call written as text instead of a structured call",
                        "args": None, "type_drift": []})
    return out


def _check_and_run(tc: dict, turn: int) -> dict:
    v = validate_call(tc["name"], tc.get("args"))
    att = {"turn": turn, "source": "structured", "name": tc["name"], "raw_args": tc.get("args"),
           "status": v["status"], "error": v["error"], "args": v["args"],
           "type_drift": v["type_drift"], "result": None}
    if v["status"] == "ok":
        status, result, err = execute_call(tc["name"], v["args"])
        att.update(status=status, result=result, error=err)
    return att


def _ser(m) -> dict:
    d = {"type": m.type, "content": m.content if isinstance(m.content, str) else str(m.content)}
    if isinstance(m, AIMessage) and m.tool_calls:
        d["tool_calls"] = [{"name": t["name"], "args": t["args"]} for t in m.tool_calls]
    if isinstance(m, ToolMessage):
        d["name"], d["status"] = m.name, getattr(m, "status", None)
    return d


# --------------------------------------------------------------------------
# single-shot
# --------------------------------------------------------------------------

def run_single_shot(llm_tools, prompt: str) -> dict:
    messages = [SystemMessage(BASE_PROMPT + SINGLE_SHOT_SUFFIX), HumanMessage(prompt)]
    msg, lat = _invoke_with_retry(llm_tools, messages)
    attempts = [_check_and_run(tc, 0) for tc in msg.tool_calls or []] + _parse_failures(msg, 0)
    return {
        "attempts": attempts, "turns": [_turn_info(msg, lat)],
        "final_text": msg.content if isinstance(msg.content, str) else str(msg.content),
        "stop_reason": "final_answer", "messages": [_ser(m) for m in messages[1:] + [msg]],
    }


# --------------------------------------------------------------------------
# ReAct on LangGraph
# --------------------------------------------------------------------------

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]          # chat history (reducer appends)
    attempts: Annotated[list, operator.add]          # every tool-call attempt
    turns: Annotated[list, operator.add]             # per-LLM-call timing/tokens
    stop: str | None                                 # why the run ended early


def build_react_graph(llm_tools, error_feedback: bool = True):
    system = SystemMessage(BASE_PROMPT + REACT_SUFFIX)

    def agent(state: AgentState) -> dict:
        msg, lat = _invoke_with_retry(llm_tools, [system] + state["messages"])
        turn = len(state["turns"])
        return {"messages": [msg], "turns": [_turn_info(msg, lat)],
                "attempts": _parse_failures(msg, turn)}

    def tools(state: AgentState) -> dict:
        last = state["messages"][-1]
        turn = len(state["turns"]) - 1
        attempts, outs, stop = [], [], None
        for tc in last.tool_calls:
            att = _check_and_run(tc, turn)
            attempts.append(att)
            if att["status"] == "ok":
                outs.append(ToolMessage(content=json.dumps(att["result"], default=str),
                                        name=tc["name"], tool_call_id=tc["id"]))
            else:
                outs.append(ToolMessage(content=f"Error: {att['error']} Please fix the call and try again.",
                                        name=tc["name"], tool_call_id=tc["id"], status="error"))
                if not error_feedback:
                    stop = "tool_error_no_feedback"
        return {"messages": outs, "attempts": attempts, "stop": stop}

    def after_agent(state: AgentState) -> str:
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    def after_tools(state: AgentState) -> str:
        return END if state.get("stop") else "agent"

    g = StateGraph(AgentState)
    g.add_node("agent", agent)
    g.add_node("tools", tools)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", after_agent, {"tools": "tools", END: END})
    g.add_conditional_edges("tools", after_tools, {"agent": "agent", END: END})
    return g.compile()


def run_react(graph, prompt: str, recursion_limit: int = 25) -> dict:
    state: dict[str, Any] = {"messages": [HumanMessage(prompt)], "attempts": [], "turns": [], "stop": None}
    last = state
    stop = None
    try:
        for last in graph.stream(state, config={"recursion_limit": recursion_limit},
                                 stream_mode="values"):
            pass
    except GraphRecursionError:
        stop = "recursion_limit"
    stop = stop or last.get("stop") or "final_answer"
    msgs = last["messages"]
    final = ""
    if stop == "final_answer" and msgs and isinstance(msgs[-1], AIMessage):
        c = msgs[-1].content
        final = c if isinstance(c, str) else str(c)
    return {"attempts": last["attempts"], "turns": last["turns"], "final_text": final,
            "stop_reason": stop, "messages": [_ser(m) for m in msgs]}


class Runner:
    """Holds one model's tool-bound LLM and compiled graphs."""

    def __init__(self, llm, recursion_limit: int = 25):
        self.llm_tools = llm.bind_tools(TOOLS)
        self.recursion_limit = recursion_limit
        self.graphs = {
            "react": build_react_graph(self.llm_tools, error_feedback=True),
            "react_no_error_feedback": build_react_graph(self.llm_tools, error_feedback=False),
        }

    def run(self, mode: str, prompt: str) -> dict:
        t0 = time.perf_counter()
        if mode == "single_shot":
            out = run_single_shot(self.llm_tools, prompt)
        else:
            out = run_react(self.graphs[mode], prompt, self.recursion_limit)
        out["wall_s"] = round(time.perf_counter() - t0, 3)
        return out
