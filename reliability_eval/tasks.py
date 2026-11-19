"""Ground-truth task suite.

Each task = a user prompt + the known-correct tool calls (name + arguments)
+ the expected final answer.

Splits
  dev  (12 tasks): used only to smoke-test the harness and freeze the system
                   prompt BEFORE the test split is run.
  test (72 tasks): held out. Never used to change the prompt, tools or
                   matching rules. All reported numbers come from this split.

Categories
  single_simple : one call, arguments stated plainly in the prompt
  single_args   : one call, but the argument needs care (enum value, unit
                  conversion like "2 hours" -> 120, number words, order)
  multi_step    : 2-3 calls; most are dependent (call 2 needs call 1's result),
                  a few are independent pairs (order does not matter)
  no_tool       : general knowledge; the correct behaviour is NO tool call

Argument matching spec (see scoring.match_value)
  plain number            -> numeric match, relative tolerance 1e-3
  plain string            -> case-insensitive, whitespace-normalised equality
  {"$contains": [kw,...]} -> string must contain every keyword (case-insensitive)
  {"$any": [v1, v2,...]}  -> any one of the listed values is accepted
"""

from __future__ import annotations

import json
from pathlib import Path

C = lambda *kw: {"$contains": list(kw)}  # noqa: E731
ANY = lambda *v: {"$any": list(v)}  # noqa: E731


def T(tid, split, cat, prompt, calls=(), answer=None, ordered=True):
    return {
        "id": tid, "split": split, "category": cat, "prompt": prompt,
        "expected_calls": [{"name": n, "args": a} for n, a in calls],
        "ordered": ordered,
        # expected_answer: number, string, list of acceptable strings (any),
        # or {"$all": [...]} (every item must appear). None = not checked.
        "expected_answer": answer,
    }


TASKS = [
    # ------------------------------------------------------------- dev (12)
    T("dev_s1", "dev", "single_simple", "What is 56 plus 44?", [("add", {"a": 56, "b": 44})], 100),
    T("dev_s2", "dev", "single_simple", "What's the weather in Mumbai?", [("get_weather", {"city": "Mumbai"})], 31),
    T("dev_s3", "dev", "single_simple", "Convert 10 dollars to euros.",
      [("convert_currency", {"amount": 10, "from_currency": "USD", "to_currency": "EUR"})], 9.2),
    T("dev_a1", "dev", "single_args", "Weather in Tokyo in fahrenheit.",
      [("get_weather", {"city": "Tokyo", "unit": "fahrenheit"})], 59),
    T("dev_a2", "dev", "single_args", "Remind me in 30 minutes to drink water.",
      [("create_reminder", {"text": C("water"), "minutes": 30})], None),
    T("dev_a3", "dev", "single_args", "What's nine times eight?", [("multiply", {"a": 9, "b": 8})], 72),
    T("dev_m1", "dev", "multi_step", "Add 10 and 15, then multiply the result by 4.",
      [("add", {"a": 10, "b": 15}), ("multiply", {"a": 25, "b": 4})], 100),
    T("dev_m2", "dev", "multi_step", "What department is Ananya Rao in?",
      [("find_employee", {"name": C("ananya")}), ("get_employee", {"employee_id": 1001})], "Engineering"),
    T("dev_m3", "dev", "multi_step", "Get the weather in London and in Paris.",
      [("get_weather", {"city": "London"}), ("get_weather", {"city": "Paris"})], {"$all": [9, 11]}, ordered=False),
    T("dev_n1", "dev", "no_tool", "What is the capital of Japan?", [], "Tokyo"),
    T("dev_n2", "dev", "no_tool", "Who painted the Mona Lisa?", [], ["Leonardo", "da Vinci"]),
    T("dev_n3", "dev", "no_tool", "How many continents are there on Earth?", [], ["7", "seven"]),

    # -------------------------------------------------- test: single_simple (22)
    T("s01", "test", "single_simple", "What is 25 times 4?", [("multiply", {"a": 25, "b": 4})], 100),
    T("s02", "test", "single_simple", "Add 348 and 1276.", [("add", {"a": 348, "b": 1276})], 1624),
    T("s03", "test", "single_simple", "What's 7391 multiplied by 842?", [("multiply", {"a": 7391, "b": 842})], 6223222),
    T("s04", "test", "single_simple", "Subtract 1999 from 5000.", [("subtract", {"a": 5000, "b": 1999})], 3001),
    T("s05", "test", "single_simple", "What is 144 divided by 12?", [("divide", {"a": 144, "b": 12})], 12),
    T("s06", "test", "single_simple", "How much is 3.75 plus 8.6?", [("add", {"a": 3.75, "b": 8.6})], 12.35),
    T("s07", "test", "single_simple", "What's the weather in Pune right now?", [("get_weather", {"city": "Pune"})], 27),
    T("s08", "test", "single_simple", "Is it cold in London today?", [("get_weather", {"city": "London"})], 9),
    T("s09", "test", "single_simple", "Tell me the current weather for Tokyo.", [("get_weather", {"city": "Tokyo"})], 15),
    T("s10", "test", "single_simple", "Convert 100 euros to Japanese yen.",
      [("convert_currency", {"amount": 100, "from_currency": "EUR", "to_currency": "JPY"})], 16304.35),
    T("s11", "test", "single_simple", "How many Indian rupees is 250 US dollars?",
      [("convert_currency", {"amount": 250, "from_currency": "USD", "to_currency": "INR"})], 20750),
    T("s12", "test", "single_simple", "Change 5000 Indian rupees into British pounds.",
      [("convert_currency", {"amount": 5000, "from_currency": "INR", "to_currency": "GBP"})], 47.59),
    T("s13", "test", "single_simple", "Look up employee 1042.", [("get_employee", {"employee_id": 1042})], "Priya Shah"),
    T("s14", "test", "single_simple", "What department does employee 1013 work in?",
      [("get_employee", {"employee_id": 1013})], "Sales"),
    T("s15", "test", "single_simple", "Find the employee ID of Kabir Singh.",
      [("find_employee", {"name": C("kabir")})], 1050),
    T("s16", "test", "single_simple", "Remind me to call the dentist in 45 minutes.",
      [("create_reminder", {"text": C("dentist"), "minutes": 45})], None),
    T("s17", "test", "single_simple", "Set a reminder in 10 minutes to check the oven.",
      [("create_reminder", {"text": C("oven"), "minutes": 10})], None),
    T("s18", "test", "single_simple", "What is 1000 minus 1?", [("subtract", {"a": 1000, "b": 1})], 999),
    T("s19", "test", "single_simple", "Divide 7 by 2.", [("divide", {"a": 7, "b": 2})], 3.5),
    T("s20", "test", "single_simple", "What's 0.15 times 640?", [("multiply", {"a": 0.15, "b": 640})], 96),
    T("s21", "test", "single_simple", "What's the weather like in New York?",
      [("get_weather", {"city": ANY("New York", "New York City", "NYC")})], 12),
    T("s22", "test", "single_simple", "Who is employee number 1001?", [("get_employee", {"employee_id": 1001})], "Ananya Rao"),

    # ---------------------------------------------------- test: single_args (14)
    T("a01", "test", "single_args", "What's the temperature in Mumbai in Fahrenheit?",
      [("get_weather", {"city": "Mumbai", "unit": "fahrenheit"})], 87.8),
    T("a02", "test", "single_args", "Give me Delhi's weather in fahrenheit please.",
      [("get_weather", {"city": ANY("Delhi", "New Delhi"), "unit": "fahrenheit"})], 71.6),
    T("a03", "test", "single_args", "Weather in Paris, in Celsius.",
      [("get_weather", {"city": "Paris", "unit": "celsius"})], 11),
    T("a04", "test", "single_args", "Remind me in 2 hours to submit the report.",
      [("create_reminder", {"text": C("report"), "minutes": 120})], None),
    T("a05", "test", "single_args", "Set a reminder for one and a half hours from now: pick up groceries.",
      [("create_reminder", {"text": C("groceries"), "minutes": 90})], None),
    T("a06", "test", "single_args", "In a quarter of an hour, remind me to stretch.",
      [("create_reminder", {"text": C("stretch"), "minutes": 15})], None),
    T("a07", "test", "single_args", "What is twelve times thirteen?", [("multiply", {"a": 12, "b": 13})], 156),
    T("a08", "test", "single_args", "Add negative 45 and 120.", [("add", {"a": -45, "b": 120})], 75),
    T("a09", "test", "single_args", "Convert 1,250.50 GBP to USD.",
      [("convert_currency", {"amount": 1250.5, "from_currency": "GBP", "to_currency": "USD"})], 1582.91),
    T("a10", "test", "single_args", "How many US dollars do I get for 10000 yen?",
      [("convert_currency", {"amount": 10000, "from_currency": "JPY", "to_currency": "USD"})], 66.67),
    T("a11", "test", "single_args", "Take 72 away from 300.", [("subtract", {"a": 300, "b": 72})], 228),
    T("a12", "test", "single_args", "Split a bill of 1350 rupees equally among 6 people. How much does each pay?",
      [("divide", {"a": 1350, "b": 6})], 225),
    T("a13", "test", "single_args", "Which city is employee 1066's office in?",
      [("get_employee", {"employee_id": 1066})], "New York"),
    T("a14", "test", "single_args", "Search the directory for an employee named Meera.",
      [("find_employee", {"name": C("meera")})], 1021),

    # ----------------------------------------------------- test: multi_step (20)
    T("m01", "test", "multi_step", "What is 15 plus 27, then multiply the result by 3?",
      [("add", {"a": 15, "b": 27}), ("multiply", {"a": 42, "b": 3})], 126),
    T("m02", "test", "multi_step", "Add 120 and 80, then divide the total by 4.",
      [("add", {"a": 120, "b": 80}), ("divide", {"a": 200, "b": 4})], 50),
    T("m03", "test", "multi_step", "Multiply 6 by 7 and then subtract 2 from the result.",
      [("multiply", {"a": 6, "b": 7}), ("subtract", {"a": 42, "b": 2})], 40),
    T("m04", "test", "multi_step", "Subtract 250 from 1000 and then multiply what's left by 2.",
      [("subtract", {"a": 1000, "b": 250}), ("multiply", {"a": 750, "b": 2})], 1500),
    T("m05", "test", "multi_step", "First add 18 and 24, then divide that sum by 7.",
      [("add", {"a": 18, "b": 24}), ("divide", {"a": 42, "b": 7})], 6),
    T("m06", "test", "multi_step", "Add 20 and 30 US dollars, then convert the total to Indian rupees.",
      [("add", {"a": 20, "b": 30}),
       ("convert_currency", {"amount": 50, "from_currency": "USD", "to_currency": "INR"})], 4150),
    T("m07", "test", "multi_step", "Convert 200 euros to US dollars, then add 15 to the converted amount.",
      [("convert_currency", {"amount": 200, "from_currency": "EUR", "to_currency": "USD"}),
       ("add", {"a": 217.39, "b": 15})], 232.39),
    T("m08", "test", "multi_step", "What is the weather in the city where employee 1042's office is?",
      [("get_employee", {"employee_id": 1042}), ("get_weather", {"city": "Pune"})], 27),
    T("m09", "test", "multi_step", "Find Priya Shah's employee ID and then tell me her department.",
      [("find_employee", {"name": C("priya")}), ("get_employee", {"employee_id": 1042})], "Finance"),
    T("m10", "test", "multi_step", "Who is the manager of employee 1013? Give me the manager's name.",
      [("get_employee", {"employee_id": 1013}), ("get_employee", {"employee_id": 1021})], "Meera Iyer"),
    T("m11", "test", "multi_step", "What's the weather in the office city of Kabir Singh?",
      [("find_employee", {"name": C("kabir")}), ("get_employee", {"employee_id": 1050}),
       ("get_weather", {"city": "Tokyo"})], 15),
    T("m12", "test", "multi_step", "Look up Arjun Nair's manager and tell me which department the manager is in.",
      [("find_employee", {"name": C("arjun")}), ("get_employee", {"employee_id": 1013}),
       ("get_employee", {"employee_id": 1021})], "Sales"),
    T("m13", "test", "multi_step", "Multiply 12 by 12, then add 56 to the result.",
      [("multiply", {"a": 12, "b": 12}), ("add", {"a": 144, "b": 56})], 200),
    T("m14", "test", "multi_step", "Divide 900 by 3, then subtract 45 from the result.",
      [("divide", {"a": 900, "b": 3}), ("subtract", {"a": 300, "b": 45})], 255),
    T("m15", "test", "multi_step", "Get the current weather in Bengaluru and in Delhi.",
      [("get_weather", {"city": ANY("Bengaluru", "Bangalore")}), ("get_weather", {"city": ANY("Delhi", "New Delhi")})],
      {"$all": [24, 22]}, ordered=False),
    T("m16", "test", "multi_step", "Convert 50 British pounds to euros, and also 50 British pounds to yen.",
      [("convert_currency", {"amount": 50, "from_currency": "GBP", "to_currency": "EUR"}),
       ("convert_currency", {"amount": 50, "from_currency": "GBP", "to_currency": "JPY"})],
      {"$all": [58.23, 9493.67]}, ordered=False),
    T("m17", "test", "multi_step", "What's 45 times 3, and separately, what is 210 divided by 7?",
      [("multiply", {"a": 45, "b": 3}), ("divide", {"a": 210, "b": 7})], {"$all": [135, 30]}, ordered=False),
    T("m18", "test", "multi_step", "Look up employees 1000 and 1007 and tell me their names.",
      [("get_employee", {"employee_id": 1000}), ("get_employee", {"employee_id": 1007})],
      {"$all": ["Vikram Mehta", "Rahul Verma"]}, ordered=False),
    T("m19", "test", "multi_step", "What is the temperature in Sara Thomas's office city, in Fahrenheit?",
      [("find_employee", {"name": C("sara")}), ("get_employee", {"employee_id": 1066}),
       ("get_weather", {"city": ANY("New York", "New York City", "NYC"), "unit": "fahrenheit"})], 53.6),
    T("m20", "test", "multi_step", "Add 5 and 7, multiply the result by 10, then divide that by 4.",
      [("add", {"a": 5, "b": 7}), ("multiply", {"a": 12, "b": 10}), ("divide", {"a": 120, "b": 4})], 30),

    # -------------------------------------------------------- test: no_tool (16)
    T("n01", "test", "no_tool", "What is the capital of France?", [], "Paris"),
    T("n02", "test", "no_tool", "Who wrote Romeo and Juliet?", [], "Shakespeare"),
    T("n03", "test", "no_tool", "How many days are there in a week?", [], ["7", "seven"]),
    T("n04", "test", "no_tool", "What is the chemical symbol for gold?", [], "Au"),
    T("n05", "test", "no_tool", "Translate 'thank you' into Spanish.", [], "gracias"),
    T("n06", "test", "no_tool", "What does CPU stand for?", [], "central processing unit"),
    T("n07", "test", "no_tool", "Which planet is known as the Red Planet?", [], "Mars"),
    T("n08", "test", "no_tool", "Say hello to me in a friendly way.", [], None),
    T("n09", "test", "no_tool", "At sea level, what is the boiling point of water in Celsius?", [], "100"),
    T("n10", "test", "no_tool", "What kinds of things can you help me with?", [], None),
    T("n11", "test", "no_tool", "Which ocean is the largest on Earth?", [], "Pacific"),
    T("n12", "test", "no_tool", "What's the opposite of the word 'hot'?", [], "cold"),
    T("n13", "test", "no_tool", "Give me one synonym for 'happy'.", [], None),
    T("n14", "test", "no_tool", "What language is mainly spoken in Brazil?", [], "Portuguese"),
    T("n15", "test", "no_tool", "Botanically speaking, is a tomato a fruit or a vegetable?", [], "fruit"),
    T("n16", "test", "no_tool", "What is the largest mammal in the world?", [], "blue whale"),
]


def load_tasks(split: str | None = None) -> list[dict]:
    if split in (None, "all"):
        return list(TASKS)
    return [t for t in TASKS if t["split"] == split]


def write_jsonl(path: str | Path) -> None:
    with open(path, "w") as f:
        for t in TASKS:
            f.write(json.dumps(t) + "\n")


if __name__ == "__main__":
    import collections
    out = Path(__file__).with_name("tasks.jsonl")
    write_jsonl(out)
    c = collections.Counter((t["split"], t["category"]) for t in TASKS)
    for k, v in sorted(c.items()):
        print(k, v)
    print("total", len(TASKS), "->", out)
