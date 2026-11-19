"""Validation of tool-call attempts, matching against ground truth, and the
rule-based failure taxonomy.

Vocabulary
  attempt   : one tool call the model tried to make (structured, unparseable,
              or written as JSON text in the reply instead of a real call)
  status    : what happened to the attempt
                ok               valid against the schema and executed fine
                tool_error       schema-valid, but the tool rejected the value
                                 (e.g. currency "dollars", employee 9999)
                unknown_tool     tool name not in the registry
                unknown_args     argument key not in the tool's schema
                missing_args     a required argument is absent
                validation_error value cannot be coerced to the schema type /
                                 enum (e.g. unit="F", minutes="soon")
                parse_error      call could not be parsed as a structured call
  MALFORMED = unknown_tool | unknown_args | missing_args | validation_error | parse_error
"""

from __future__ import annotations

import itertools
import json
import math
import re
from collections import Counter

from pydantic import ValidationError

from .tools import COMMUTATIVE, TOOLS_BY_NAME, tool_schema

MALFORMED = {"unknown_tool", "unknown_args", "missing_args", "validation_error", "parse_error"}

NUM_REL_TOL = 1e-3      # argument numbers: 0.1 % relative tolerance
ANSWER_REL_TOL = 5e-3   # numbers in the final answer: 0.5 % (allows rounding to 2 dp)


# --------------------------------------------------------------------------
# Validation of one structured call
# --------------------------------------------------------------------------

def _json_type_ok(prop: dict, value) -> bool:
    """Is the RAW value the JSON type the schema asks for (before coercion)?"""
    t = prop.get("type")
    if t is None and "anyOf" in prop:
        return any(_json_type_ok(p, value) for p in prop["anyOf"])
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "integer":
        return (isinstance(value, int) and not isinstance(value, bool)) or (
            isinstance(value, float) and value.is_integer())
    if t == "string":
        return isinstance(value, str)
    return True


def validate_call(name, raw_args) -> dict:
    """Check a structured call against the registry. Does not execute it.

    Returns {status, error, args (coerced, if valid), type_drift: [keys]}.
    """
    out = {"status": "ok", "error": None, "args": None, "type_drift": []}
    if name not in TOOLS_BY_NAME:
        out.update(status="unknown_tool",
                   error=f"Unknown tool '{name}'. Available tools: {sorted(TOOLS_BY_NAME)}.")
        return out
    if not isinstance(raw_args, dict):
        out.update(status="parse_error", error=f"Arguments must be a JSON object, got {raw_args!r}.")
        return out
    schema = tool_schema(name)
    props = schema.get("properties", {})
    unknown = [k for k in raw_args if k not in props]
    if unknown:
        out.update(status="unknown_args",
                   error=f"Unknown argument(s) {unknown} for '{name}'. Valid arguments: {list(props)}.")
        return out
    out["type_drift"] = [k for k, v in raw_args.items() if not _json_type_ok(props[k], v)]
    try:
        model = TOOLS_BY_NAME[name].args_schema.model_validate(raw_args)
    except ValidationError as e:
        missing = [".".join(map(str, err["loc"])) for err in e.errors() if err["type"] == "missing"]
        if missing:
            out.update(status="missing_args",
                       error=f"Missing required argument(s) {missing} for '{name}'.")
        else:
            msgs = "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors())
            out.update(status="validation_error", error=f"Invalid arguments for '{name}': {msgs}")
        return out
    out["args"] = {k: v for k, v in model.model_dump().items() if k in props}
    return out


def execute_call(name: str, args: dict) -> tuple[str, object, str | None]:
    """Run a validated call. Returns (status, result, error)."""
    try:
        return "ok", TOOLS_BY_NAME[name].invoke(args), None
    except Exception as e:  # tool rejected the value
        return "tool_error", None, f"Tool '{name}' failed: {e}"


# --------------------------------------------------------------------------
# Detecting tool calls written as text (a parsing failure)
# --------------------------------------------------------------------------

_TEXT_CALL_PATTERNS = [
    re.compile(r'"name"\s*:\s*"([A-Za-z_]\w*)"'),
    re.compile(r'"function"\s*:\s*"([A-Za-z_]\w*)"'),
    re.compile(r"<tool_call>\s*\{.*?\"name\"\s*:\s*\"([A-Za-z_]\w*)\"", re.S),
]


def text_json_calls(content: str) -> list[str]:
    """Names of tool calls the model wrote into its reply text instead of
    emitting a structured call. Only names that look like tools count."""
    if not content:
        return []
    names = []
    for pat in _TEXT_CALL_PATTERNS:
        for m in pat.finditer(content):
            n = m.group(1)
            if n in TOOLS_BY_NAME and n not in names:
                names.append(n)
    return names


# --------------------------------------------------------------------------
# Matching against ground truth
# --------------------------------------------------------------------------

def _norm_str(s: str) -> str:
    return " ".join(str(s).lower().strip().strip(".").split())


def _to_num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace(",", "").strip())
        except ValueError:
            return None
    return None


def match_value(spec, value) -> bool:
    if isinstance(spec, dict) and "$contains" in spec:
        return isinstance(value, str) and all(k.lower() in value.lower() for k in spec["$contains"])
    if isinstance(spec, dict) and "$any" in spec:
        return any(match_value(s, value) for s in spec["$any"])
    if spec is None:
        return value is None
    if isinstance(spec, (int, float)) and not isinstance(spec, bool):
        v = _to_num(value)
        return v is not None and math.isclose(v, float(spec), rel_tol=NUM_REL_TOL, abs_tol=1e-6)
    return isinstance(value, str) and _norm_str(value) == _norm_str(spec)


def match_args(tool: str, expected: dict, got: dict) -> bool:
    def _plain(exp, g):
        for k, spec in exp.items():
            if not match_value(spec, g.get(k)):
                return False
        props = tool_schema(tool).get("properties", {})
        for k, v in g.items():  # extra args must equal their schema default
            if k not in exp and v != props.get(k, {}).get("default", object()):
                return False
        return True

    if _plain(expected, got):
        return True
    if tool in COMMUTATIVE:
        x, y = COMMUTATIVE[tool]
        swapped = dict(got)
        swapped[x], swapped[y] = got.get(y), got.get(x)
        return _plain(expected, swapped)
    return False


def _dedupe(calls: list[dict]) -> list[dict]:
    """Drop exact repeats of an identical successful call (same name + args)."""
    seen, out = set(), []
    for c in calls:
        key = (c["name"], json.dumps(c["args"], sort_keys=True, default=str))
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def match_calls(expected: list[dict], got: list[dict], ordered: bool) -> tuple[bool, bool]:
    """(selection_ok, args_ok) for the successful calls of a run."""
    got = _dedupe(got)
    exp_names = [e["name"] for e in expected]
    got_names = [g["name"] for g in got]
    if ordered:
        if got_names != exp_names:
            return False, False
        return True, all(match_args(e["name"], e["args"], g["args"]) for e, g in zip(expected, got))
    if Counter(got_names) != Counter(exp_names):
        return False, False
    for perm in itertools.permutations(got):
        if all(e["name"] == g["name"] and match_args(e["name"], e["args"], g["args"])
               for e, g in zip(expected, perm)):
            return True, True
    return True, False


# --------------------------------------------------------------------------
# Final-answer check
# --------------------------------------------------------------------------

_NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _numbers_in(text: str) -> list[float]:
    out = []
    for m in _NUM_RE.finditer(text or ""):
        try:
            out.append(float(m.group(0).replace(",", "")))
        except ValueError:
            pass
    return out


def _answer_item_ok(spec, text: str) -> bool:
    if isinstance(spec, (int, float)) and not isinstance(spec, bool):
        return any(math.isclose(n, float(spec), rel_tol=ANSWER_REL_TOL, abs_tol=0.01)
                   for n in _numbers_in(text))
    return _norm_str(spec) in _norm_str(text or "")


def answer_correct(spec, text: str):
    if spec is None:
        return None
    if isinstance(spec, dict) and "$all" in spec:
        return all(_answer_item_ok(s, text) for s in spec["$all"])
    if isinstance(spec, list):
        return any(_answer_item_ok(s, text) for s in spec)
    return _answer_item_ok(spec, text)


# --------------------------------------------------------------------------
# Scoring one run + failure taxonomy
# --------------------------------------------------------------------------

# Our fine-grained labels -> the four README classes (others are extra classes
# that the data showed up and the README did not list).
README_CLASS = {
    "schema_hallucination": "1. Schema hallucination",
    "type_drift": "2. Type drift & parsing",
    "parse_failure": "2. Type drift & parsing",
    "invalid_type_or_enum": "2. Type drift & parsing",
    "argument_omission": "3. Argument omission",
    "cyclic_stagnation": "4. Cyclic stagnation",
}

# Order used to pick ONE primary label per failed run (most specific first)
PRIMARY_ORDER = [
    "cyclic_stagnation", "schema_hallucination", "parse_failure", "argument_omission",
    "invalid_type_or_enum", "unneeded_call", "tool_skipped", "wrong_tool",
    "incomplete_chain", "wrong_value", "invalid_value", "stopped_on_error", "answer_wrong",
]


def _repeat_loop(attempts: list[dict], k: int = 3) -> bool:
    keys = [(a.get("name"), json.dumps(a.get("raw_args"), sort_keys=True, default=str))
            for a in attempts]
    return any(n >= k for n in Counter(keys).values())


def score_run(task: dict, run: dict) -> dict:
    """Turn one trace into per-run metrics + taxonomy labels."""
    attempts = run.get("attempts", [])
    expected = task["expected_calls"]
    is_no_tool = not expected
    loop_mode = run["mode"] != "single_shot"

    ok_calls = [{"name": a["name"], "args": a["args"]} for a in attempts if a["status"] == "ok"]
    n_attempts = len(attempts)
    n_malformed = sum(a["status"] in MALFORMED for a in attempts)
    n_tool_err = sum(a["status"] == "tool_error" for a in attempts)
    drift_attempts = [a for a in attempts if a.get("type_drift")]

    if is_no_tool:
        selection_ok = n_attempts == 0
        args_ok = None
    else:
        selection_ok, args_ok = match_calls(expected, ok_calls, task["ordered"])
        if not selection_ok:
            args_ok = None  # argument correctness is conditional on selection
    exact = bool(selection_ok and (args_ok if not is_no_tool else True))

    finished = run.get("stop_reason") in (None, "final_answer")
    ans = answer_correct(task["expected_answer"], run.get("final_text", "")) \
        if (loop_mode or is_no_tool) else None
    if loop_mode:
        success = bool(exact and finished and ans is not False)
    else:
        success = None  # single-shot never sees tool results -> no end-to-end answer

    # ---------------- taxonomy (multi-label)
    labels = set()
    st = Counter(a["status"] for a in attempts)
    if st["unknown_tool"] or st["unknown_args"]:
        labels.add("schema_hallucination")
    if st["parse_error"]:
        labels.add("parse_failure")
    if st["missing_args"]:
        labels.add("argument_omission")
    if drift_attempts:
        labels.add("type_drift")
    if st["validation_error"]:
        labels.add("invalid_type_or_enum")
    if run.get("stop_reason") == "recursion_limit" or _repeat_loop(attempts):
        labels.add("cyclic_stagnation")
    if run.get("stop_reason") == "tool_error_no_feedback":
        labels.add("stopped_on_error")
    if is_no_tool and n_attempts:
        labels.add("unneeded_call")
    if not is_no_tool:
        exp_names = [e["name"] for e in expected]
        got_names = [c["name"] for c in _dedupe(ok_calls)]
        if n_attempts == 0:
            labels.add("tool_skipped")
        elif not selection_ok:
            if got_names and got_names == exp_names[:len(got_names)]:
                labels.add("incomplete_chain")   # right start, stopped too early
            elif got_names:
                labels.add("wrong_tool")         # valid calls, but wrong tool(s)/order/count
        elif args_ok is False:
            labels.add("wrong_value")            # right tools, wrong argument values
    if st["tool_error"]:
        labels.add("invalid_value")              # schema-valid value the tool rejected
    if loop_mode and exact and finished and ans is False:
        labels.add("answer_wrong")

    failed = (not success) if loop_mode else (not exact)
    primary = None
    if failed:  # recovered runs keep their labels but get no primary failure
        primary = next((lab for lab in PRIMARY_ORDER if lab in labels), "other")

    return {
        "model": run["model"], "mode": run["mode"], "task_id": task["id"],
        "category": task["category"],
        "selection_ok": selection_ok, "args_ok": args_ok, "exact_match": exact,
        "answer_ok": ans, "success": success, "finished": finished,
        "stop_reason": run.get("stop_reason"),
        "n_attempts": n_attempts, "n_malformed": n_malformed, "n_tool_error": n_tool_err,
        "n_type_drift": len(drift_attempts),
        "any_malformed": n_malformed > 0,
        "recovered": bool(success and n_malformed + n_tool_err > 0),
        "answer_ok_but_call_wrong": bool(ans is True and not exact and not is_no_tool),
        "llm_calls": len(run.get("turns", [])),
        "latency_s": round(sum(t.get("latency_s", 0) for t in run.get("turns", [])), 3),
        "output_tokens": sum(t.get("eval_count") or 0 for t in run.get("turns", [])),
        "labels": sorted(labels), "primary_failure": primary,
    }
