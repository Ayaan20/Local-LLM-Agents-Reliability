"""Offline tests for the harness (no Ollama needed): a scripted fake model
plays back fixed replies so every scoring path is exercised.

    python -m pytest reliability_eval/test_harness.py -q
"""

from __future__ import annotations

import itertools

from langchain_core.messages import AIMessage

from reliability_eval.agents import Runner
from reliability_eval.scoring import match_calls, score_run, validate_call
from reliability_eval.tasks import load_tasks

TASKS = {t["id"]: t for t in load_tasks("all")}
_ids = itertools.count()


def call(tool_name, **args):
    return {"name": tool_name, "args": args, "id": f"c{next(_ids)}", "type": "tool_call"}


class FakeLLM:
    """Replies come from a script: list of AIMessages, consumed in order."""

    def __init__(self, script):
        self.script = list(script)

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        if not self.script:
            return AIMessage(content="done")
        nxt = self.script.pop(0)
        return nxt if not callable(nxt) else nxt(messages)


def run(task_id, mode, script, limit=25):
    r = Runner(FakeLLM(script), recursion_limit=limit).run(mode, TASKS[task_id]["prompt"])
    r.update(model="fake", mode=mode, task_id=task_id)
    return score_run(TASKS[task_id], r), r


def test_validate_paths():
    assert validate_call("add", {"a": 1, "b": 2})["status"] == "ok"
    assert validate_call("power", {"a": 1})["status"] == "unknown_tool"
    assert validate_call("add", {"x": 1, "b": 2})["status"] == "unknown_args"
    assert validate_call("add", {"a": 1})["status"] == "missing_args"
    assert validate_call("get_weather", {"city": "Pune", "unit": "F"})["status"] == "validation_error"
    v = validate_call("add", {"a": "25", "b": 4})
    assert v["status"] == "ok" and v["type_drift"] == ["a"] and v["args"]["a"] == 25.0


def test_single_shot_correct_and_commutative():
    s, _ = run("s01", "single_shot", [AIMessage("", tool_calls=[call("multiply", a=4, b=25)])])
    assert s["selection_ok"] and s["args_ok"] and s["exact_match"] and s["success"] is None


def test_subtract_order_matters():
    s, _ = run("s04", "single_shot", [AIMessage("", tool_calls=[call("subtract", a=1999, b=5000)])])
    assert s["selection_ok"] and s["args_ok"] is False and s["primary_failure"] == "wrong_value"


def test_tool_skipped_but_answer_right():
    s, _ = run("s01", "react", [AIMessage("25 times 4 is 100.")])
    assert not s["exact_match"] and s["answer_ok"] and s["answer_ok_but_call_wrong"]
    assert s["primary_failure"] == "tool_skipped"


def test_react_multistep_with_recovery():
    script = [
        AIMessage("", tool_calls=[call("sum", a=15, b=27)]),        # hallucinated tool
        AIMessage("", tool_calls=[call("add", a=15, b=27)]),
        AIMessage("", tool_calls=[call("multiply", a=42, b=3)]),
        AIMessage("The answer is 126."),
    ]
    s, r = run("m01", "react", script)
    assert s["success"] and s["recovered"] and s["n_malformed"] == 1
    assert "schema_hallucination" in s["labels"] and s["primary_failure"] is None
    # same script without error feedback stops at the first bad call
    s2, r2 = run("m01", "react_no_error_feedback", script)
    assert not s2["success"] and r2["stop_reason"] == "tool_error_no_feedback"


def test_recursion_limit_is_stagnation():
    loop = [AIMessage("", tool_calls=[call("get_weather", city="Pune", unit="F")]) for _ in range(30)]
    s, r = run("s07", "react", loop, limit=8)
    assert r["stop_reason"] == "recursion_limit" and s["primary_failure"] == "cyclic_stagnation"


def test_text_json_is_parse_failure():
    s, _ = run("s01", "single_shot",
               [AIMessage('{"name": "multiply", "parameters": {"a": 25, "b": 4}}')])
    assert s["n_malformed"] == 1 and s["primary_failure"] == "parse_failure"


def test_no_tool_task():
    s, _ = run("n01", "react", [AIMessage("The capital of France is Paris.")])
    assert s["exact_match"] and s["success"]
    s, _ = run("n01", "react", [AIMessage("", tool_calls=[call("get_weather", city="Paris")]),
                                AIMessage("Paris.")])
    assert not s["exact_match"] and s["primary_failure"] == "unneeded_call"


def test_unordered_and_incomplete_chain():
    exp = TASKS["m15"]["expected_calls"]
    got = [{"name": "get_weather", "args": {"city": "Delhi", "unit": "celsius"}},
           {"name": "get_weather", "args": {"city": "Bangalore", "unit": "celsius"}}]
    assert match_calls(exp, got, ordered=False) == (True, True)
    s, _ = run("m11", "react", [AIMessage("", tool_calls=[call("find_employee", name="Kabir Singh")]),
                                AIMessage("Kabir's ID is 1050.")])
    assert s["primary_failure"] == "incomplete_chain"


def test_tool_error_value():
    s, _ = run("s11", "react", [
        AIMessage("", tool_calls=[call("convert_currency", amount=250, from_currency="dollars",
                                       to_currency="rupees")]),
        AIMessage("", tool_calls=[call("convert_currency", amount=250, from_currency="USD",
                                       to_currency="INR")]),
        AIMessage("That is 20,750 rupees."),
    ])
    assert s["success"] and s["recovered"] and s["n_tool_error"] == 1 and s["n_malformed"] == 0
