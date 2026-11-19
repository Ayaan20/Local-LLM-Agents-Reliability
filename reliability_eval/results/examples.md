# Example failures (up to 2 per label)

## answer_wrong (2 runs)

**qwen2.5:3b | react | n04**: What is the chemical symbol for gold?
- expected: `[]`
- final text: "I can provide information on various topics including chemistry, but currently, I don't have the capability to provide the chemical symbol for gold. How can I assist you with something else?"; stop: final_answer

**qwen2.5:3b | react_no_error_feedback | n04**: What is the chemical symbol for gold?
- expected: `[]`
- final text: "I can provide information on various topics including chemistry, but currently, I don't have the capability to provide the chemical symbol for gold. How can I assist you with something else?"; stop: final_answer

## argument_omission (2 runs)

**llama3.2:3b | react | n10**: What kinds of things can you help me with?
- expected: `[]`
- attempt: `get_employee({})` → missing_args (Missing required argument(s) ['employee_id'] for 'get_employee'.)
- final text: 'I made a mistake by calling the "get_employee" tool without providing the required employee ID. Let me try again.\n\nTo answer your original question, I can help with a wide range of topics, including b'; stop: final_answer

**llama3.2:3b | react_no_error_feedback | n10**: What kinds of things can you help me with?
- expected: `[]`
- attempt: `get_employee({})` → missing_args (Missing required argument(s) ['employee_id'] for 'get_employee'.)
- final text: ''; stop: tool_error_no_feedback

## cyclic_stagnation (6 runs)

**qwen2.5:3b | react | m05**: First add 18 and 24, then divide that sum by 7.
- expected: `[{"name": "add", "args": {"a": 18, "b": 24}}, {"name": "divide", "args": {"a": 42, "b": 7}}]`
- attempt: `add({"a": 18, "b": 24})` → ok
- attempt: `divide({"a": 42, "b": 7})` → ok
- attempt: `divide({"result": 6})` → unknown_args (Unknown argument(s) ['result'] for 'divide'. Valid arguments: ['a', 'b'].)
- attempt: `add({"a": 18, "b": 24})` → ok
- attempt: `divide({"b": 7, "a": 42})` → ok
- attempt: `divide({"a": 6})` → missing_args (Missing required argument(s) ['b'] for 'divide'.)
- attempt: `divide({"a": 42})` → missing_args (Missing required argument(s) ['b'] for 'divide'.)
- attempt: `add({"b": 24, "a": 18})` → ok
- attempt: `divide({"a": 42})` → missing_args (Missing required argument(s) ['b'] for 'divide'.)
- attempt: `add({"a": 18, "b": 24})` → ok
- attempt: `divide({"a": 42})` → missing_args (Missing required argument(s) ['b'] for 'divide'.)
- attempt: `divide({"a": 6})` → missing_args (Missing required argument(s) ['b'] for 'divide'.)
- final text: "It seems there is a misunderstanding in the previous steps. Let me correct this. First, I will add 18 and 24 to get the sum. Then, I will divide this sum by 7 to get the final result. Let's proceed wi"; stop: final_answer

**qwen2.5:3b | react | m19**: What is the temperature in Sara Thomas's office city, in Fahrenheit?
- expected: `[{"name": "find_employee", "args": {"name": {"$contains": ["sara"]}}}, {"name": "get_employee", "args": {"employee_id": 1066}}, {"name": "get_weather", "args": {"city": {"$any": ["New York", "New York City", "NYC"]}, "unit": "fahrenheit"}}]`
- attempt: `find_employee({"name": "Sara Thomas"})` → ok
- attempt: `get_employee({"employee_id": "result.employee_id"})` → validation_error (Invalid arguments for 'get_employee': employee_id: Input should be a valid integer, unable to parse string as an integer)
- attempt: `find_employee({"name": "Sara Thomas"})` → ok
- attempt: `get_employee({"employee_id": "result.employee_id"})` → validation_error (Invalid arguments for 'get_employee': employee_id: Input should be a valid integer, unable to parse string as an integer)
- attempt: `find_employee({"name": "Sara Thomas"})` → ok
- attempt: `get_employee({"employee_id": "result.employee_id"})` → validation_error (Invalid arguments for 'get_employee': employee_id: Input should be a valid integer, unable to parse string as an integer)
- attempt: `find_employee({"name": "Sara Thomas"})` → ok
- attempt: `get_weather({"city": "Pune", "unit": "fahrenheit"})` → ok
- final text: "The temperature in Sara Thomas's office city, Pune, is 80.6°F."; stop: final_answer

## incomplete_chain (28 runs)

**llama3.2:3b | single_shot | m04**: Subtract 250 from 1000 and then multiply what's left by 2.
- expected: `[{"name": "subtract", "args": {"a": 1000, "b": 250}}, {"name": "multiply", "args": {"a": 750, "b": 2}}]`
- attempt: `subtract({"a": 1000, "b": 250})` → ok
- final text: ''; stop: final_answer

**llama3.2:3b | single_shot | m08**: What is the weather in the city where employee 1042's office is?
- expected: `[{"name": "get_employee", "args": {"employee_id": 1042}}, {"name": "get_weather", "args": {"city": "Pune"}}]`
- attempt: `get_employee({"employee_id": "1042"})` → ok
- final text: ''; stop: final_answer

## invalid_type_or_enum (35 runs)

**llama3.2:3b | single_shot | m03**: Multiply 6 by 7 and then subtract 2 from the result.
- expected: `[{"name": "multiply", "args": {"a": 6, "b": 7}}, {"name": "subtract", "args": {"a": 42, "b": 2}}]`
- attempt: `multiply({"a": 6, "b": 7})` → ok
- attempt: `subtract({"a": "multiply", "b": 2})` → validation_error (Invalid arguments for 'subtract': a: Input should be a valid number, unable to parse string as a number)
- final text: ''; stop: final_answer

**llama3.2:3b | single_shot | m13**: Multiply 12 by 12, then add 56 to the result.
- expected: `[{"name": "multiply", "args": {"a": 12, "b": 12}}, {"name": "add", "args": {"a": 144, "b": 56}}]`
- attempt: `multiply({"a": "12", "b": "12"})` → ok
- attempt: `add({"b": "56", "a": "result of multiply"})` → validation_error (Invalid arguments for 'add': a: Input should be a valid number, unable to parse string as a number)
- final text: ''; stop: final_answer

## parse_failure (25 runs)

**llama3.2:3b | react | m02**: Add 120 and 80, then divide the total by 4.
- expected: `[{"name": "add", "args": {"a": 120, "b": 80}}, {"name": "divide", "args": {"a": 200, "b": 4}}]`
- attempt: `add({"a": "120", "b": "80"})` → ok
- attempt: `divide(null)` → parse_error (tool call written as text instead of a structured call)
- final text: 'Now, let\'s divide the total by 4:\n\n{"name": "divide", "parameters": {"a": "200", "b": "4"}}'; stop: final_answer

**llama3.2:3b | react | m04**: Subtract 250 from 1000 and then multiply what's left by 2.
- expected: `[{"name": "subtract", "args": {"a": 1000, "b": 250}}, {"name": "multiply", "args": {"a": 750, "b": 2}}]`
- attempt: `subtract({"a": "1000", "b": "250"})` → ok
- attempt: `multiply(null)` → parse_error (tool call written as text instead of a structured call)
- final text: 'The result of subtracting 250 from 1000 is 750. \n\nNow, I will multiply 750 by 2. \n\n{"name": "multiply", "parameters": {"a": "750", "b": "2"}}'; stop: final_answer

## schema_hallucination (193 runs)

**llama3.2:3b | single_shot | m02**: Add 120 and 80, then divide the total by 4.
- expected: `[{"name": "add", "args": {"a": 120, "b": 80}}, {"name": "divide", "args": {"a": 200, "b": 4}}]`
- attempt: `divide({"b": "120", "minutes": 4, "a": "add"})` → unknown_args (Unknown argument(s) ['minutes'] for 'divide'. Valid arguments: ['a', 'b'].)
- final text: ''; stop: final_answer

**llama3.2:3b | single_shot | m05**: First add 18 and 24, then divide that sum by 7.
- expected: `[{"name": "add", "args": {"a": 18, "b": 24}}, {"name": "divide", "args": {"a": 42, "b": 7}}]`
- attempt: `divide({"minutes": 7, "a": "add", "b": "18"})` → unknown_args (Unknown argument(s) ['minutes'] for 'divide'. Valid arguments: ['a', 'b'].)
- final text: ''; stop: final_answer

## tool_skipped (2 runs)

**qwen2.5:3b | react | m18**: Look up employees 1000 and 1007 and tell me their names.
- expected: `[{"name": "get_employee", "args": {"employee_id": 1000}}, {"name": "get_employee", "args": {"employee_id": 1007}}]`
- final text: ''; stop: final_answer

**qwen2.5:3b | react_no_error_feedback | m18**: Look up employees 1000 and 1007 and tell me their names.
- expected: `[{"name": "get_employee", "args": {"employee_id": 1000}}, {"name": "get_employee", "args": {"employee_id": 1007}}]`
- final text: ''; stop: final_answer

## unneeded_call (18 runs)

**llama3.2:3b | single_shot | n03**: How many days are there in a week?
- expected: `[]`
- attempt: `add({"a": "7", "b": "0"})` → ok
- final text: ''; stop: final_answer

**llama3.2:3b | single_shot | n07**: Which planet is known as the Red Planet?
- expected: `[]`
- attempt: `get_weather({"city": "Mars", "unit": "celsius"})` → ok
- final text: ''; stop: final_answer

## wrong_tool (49 runs)

**llama3.2:3b | single_shot | a08**: Add negative 45 and 120.
- expected: `[{"name": "add", "args": {"a": -45, "b": 120}}]`
- attempt: `subtract({"a": "120", "b": "-45"})` → ok
- final text: ''; stop: final_answer

**llama3.2:3b | single_shot | m01**: What is 15 plus 27, then multiply the result by 3?
- expected: `[{"name": "add", "args": {"a": 15, "b": 27}}, {"name": "multiply", "args": {"a": 42, "b": 3}}]`
- attempt: `multiply({"b": 27, "a": 15})` → ok
- final text: ''; stop: final_answer

## wrong_value (9 runs)

**llama3.2:3b | single_shot | s08**: Is it cold in London today?
- expected: `[{"name": "get_weather", "args": {"city": "London"}}]`
- attempt: `get_weather({"city": "London", "unit": "fahrenheit"})` → ok
- final text: ''; stop: final_answer

**qwen2.5:7b | single_shot | s21**: What's the weather like in New York?
- expected: `[{"name": "get_weather", "args": {"city": {"$any": ["New York", "New York City", "NYC"]}}}]`
- attempt: `get_weather({"city": "New York", "unit": "fahrenheit"})` → ok
- final text: ''; stop: final_answer

