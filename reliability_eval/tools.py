"""Tool registry for the reliability benchmark.

Every tool is deterministic and offline (mock data), so a run is reproducible:
the same call always returns the same result, and the only source of
variation is the model.

Nine tools in four groups:
  arithmetic : add, subtract, multiply, divide
  weather    : get_weather (enum argument `unit`)
  currency   : convert_currency (fixed mock rates)
  employees  : find_employee (name -> id), get_employee (id -> record)
  reminders  : create_reminder (free-text + integer minutes)
"""

from __future__ import annotations

from typing import Literal

from langchain_core.tools import tool

# --------------------------------------------------------------------------
# Mock data
# --------------------------------------------------------------------------

WEATHER_C = {  # temperature in Celsius + condition
    "mumbai": (31, "humid and partly cloudy"),
    "pune": (27, "clear"),
    "delhi": (22, "hazy"),
    "bengaluru": (24, "light drizzle"),
    "london": (9, "rainy"),
    "new york": (12, "windy"),
    "tokyo": (15, "sunny"),
    "paris": (11, "overcast"),
}
CITY_ALIASES = {"bangalore": "bengaluru", "bombay": "mumbai", "nyc": "new york",
                "new york city": "new york", "new delhi": "delhi"}

# Units of currency per 1 USD (fixed, fictional snapshot)
RATES_PER_USD = {"USD": 1.0, "EUR": 0.92, "GBP": 0.79, "INR": 83.0, "JPY": 150.0}

EMPLOYEES = {
    1000: {"name": "Vikram Mehta", "department": "Engineering", "office_city": "Bengaluru", "manager_id": None},
    1001: {"name": "Ananya Rao", "department": "Engineering", "office_city": "Bengaluru", "manager_id": 1000},
    1007: {"name": "Rahul Verma", "department": "Finance", "office_city": "Mumbai", "manager_id": None},
    1013: {"name": "Arjun Nair", "department": "Sales", "office_city": "Delhi", "manager_id": 1021},
    1021: {"name": "Meera Iyer", "department": "Sales", "office_city": "London", "manager_id": None},
    1042: {"name": "Priya Shah", "department": "Finance", "office_city": "Pune", "manager_id": 1007},
    1050: {"name": "Kabir Singh", "department": "Research", "office_city": "Tokyo", "manager_id": 1000},
    1066: {"name": "Sara Thomas", "department": "Legal", "office_city": "New York", "manager_id": 1007},
}


def _norm_city(city: str) -> str:
    c = " ".join(city.lower().replace(",", " ").split())
    c = CITY_ALIASES.get(c, c)
    for known in WEATHER_C:
        if known in c:
            return known
    return c


# --------------------------------------------------------------------------
# Tools (docstrings are what the model reads)
# --------------------------------------------------------------------------

@tool
def add(a: float, b: float) -> float:
    """Add two numbers and return a + b.

    Args:
        a: First number.
        b: Second number.
    """
    return a + b


@tool
def subtract(a: float, b: float) -> float:
    """Subtract b from a and return a - b.

    Args:
        a: The number to subtract from.
        b: The number to subtract.
    """
    return a - b


@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return a * b.

    Args:
        a: First number.
        b: Second number.
    """
    return a * b


@tool
def divide(a: float, b: float) -> float:
    """Divide a by b and return a / b.

    Args:
        a: The dividend.
        b: The divisor (must not be zero).
    """
    if b == 0:
        raise ValueError("Division by zero is not allowed.")
    return a / b


@tool
def get_weather(city: str, unit: Literal["celsius", "fahrenheit"] = "celsius") -> dict:
    """Get the current weather for a city.

    Args:
        city: City name, e.g. "Pune" or "London".
        unit: Temperature unit, either "celsius" or "fahrenheit". Defaults to "celsius".
    """
    key = _norm_city(city)
    if key not in WEATHER_C:
        return {"city": city, "available": False, "message": f"No weather data for {city}."}
    t_c, cond = WEATHER_C[key]
    temp = t_c if unit == "celsius" else round(t_c * 9 / 5 + 32, 1)
    return {"city": key.title(), "temperature": temp, "unit": unit, "condition": cond}


@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert an amount of money from one currency to another.

    Args:
        amount: The amount of money to convert.
        from_currency: Three-letter ISO code of the source currency (USD, EUR, GBP, INR, JPY).
        to_currency: Three-letter ISO code of the target currency (USD, EUR, GBP, INR, JPY).
    """
    f, t = from_currency.strip().upper(), to_currency.strip().upper()
    for code in (f, t):
        if code not in RATES_PER_USD:
            raise ValueError(
                f"Unknown currency code '{code}'. Use one of {sorted(RATES_PER_USD)}."
            )
    converted = round(amount / RATES_PER_USD[f] * RATES_PER_USD[t], 2)
    return {"amount": amount, "from": f, "to": t, "converted": converted}


@tool
def find_employee(name: str) -> list:
    """Search the employee directory by (part of) a name and return matching employee IDs.

    Args:
        name: Full or partial employee name, e.g. "Priya" or "Priya Shah".
    """
    q = name.strip().lower()
    hits = [{"employee_id": eid, "name": rec["name"]}
            for eid, rec in EMPLOYEES.items() if q and q in rec["name"].lower()]
    return hits


@tool
def get_employee(employee_id: int) -> dict:
    """Get an employee's record (name, department, office city, manager ID) by employee ID.

    Args:
        employee_id: Numeric employee ID, e.g. 1042.
    """
    rec = EMPLOYEES.get(int(employee_id))
    if rec is None:
        raise ValueError(f"No employee with ID {employee_id}.")
    return {"employee_id": int(employee_id), **rec}


@tool
def create_reminder(text: str, minutes: int) -> dict:
    """Create a reminder that fires after a number of minutes from now.

    Args:
        text: What to remind the user about.
        minutes: Minutes from now until the reminder fires (whole number).
    """
    if minutes <= 0:
        raise ValueError("minutes must be a positive whole number.")
    return {"status": "scheduled", "text": text, "minutes": minutes}


TOOLS = [add, subtract, multiply, divide, get_weather, convert_currency,
         find_employee, get_employee, create_reminder]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}

# Tools whose two numeric arguments may be swapped without changing the result.
COMMUTATIVE = {"add": ("a", "b"), "multiply": ("a", "b")}


def tool_schema(name: str) -> dict:
    """JSON schema of a tool's arguments: {'properties': ..., 'required': [...]}"""
    return TOOLS_BY_NAME[name].args_schema.model_json_schema()


def run_tool(name: str, args: dict):
    """Execute a tool by name (used to build ground truth). Raises on error."""
    return TOOLS_BY_NAME[name].invoke(args)
