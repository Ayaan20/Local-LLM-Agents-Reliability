# Example failures (up to 2 per label)

## argument_omission (2 runs)

**llama3.2:3b | single_shot | dev_n3**: How many continents are there on Earth?
- expected: `[]`
- attempt: `get_weather({})` → missing_args (Missing required argument(s) ['city'] for 'get_weather'.)
- attempt: `subtract({"a": "7", "b": "3"})` → ok
- final text: ''; stop: final_answer

**llama3.2:3b | react | dev_n3**: How many continents are there on Earth?
- expected: `[]`
- attempt: `get_weather({})` → missing_args (Missing required argument(s) ['city'] for 'get_weather'.)
- final text: 'There are 7 continents on Earth: Africa, Antarctica, Asia, Australia, Europe, North America, and South America.'; stop: final_answer

## invalid_type_or_enum (3 runs)

**llama3.2:3b | single_shot | dev_m2**: What department is Ananya Rao in?
- expected: `[{"name": "find_employee", "args": {"name": {"$contains": ["ananya"]}}}, {"name": "get_employee", "args": {"employee_id": 1001}}]`
- attempt: `get_employee({"employee_id": "Ananya Rao"})` → validation_error (Invalid arguments for 'get_employee': employee_id: Input should be a valid integer, unable to parse string as an integer)
- final text: ''; stop: final_answer

**llama3.2:3b | react | dev_m2**: What department is Ananya Rao in?
- expected: `[{"name": "find_employee", "args": {"name": {"$contains": ["ananya"]}}}, {"name": "get_employee", "args": {"employee_id": 1001}}]`
- attempt: `get_employee({"employee_id": "Ananya Rao"})` → validation_error (Invalid arguments for 'get_employee': employee_id: Input should be a valid integer, unable to parse string as an integer)
- final text: "I'll try to find the department for Ananya Rao by searching for her name in an employee directory. Unfortunately, I don't have direct access to a specific employee directory, but I can suggest some po"; stop: final_answer

## schema_hallucination (2 runs)

**llama3.2:3b | single_shot | dev_m1**: Add 10 and 15, then multiply the result by 4.
- expected: `[{"name": "add", "args": {"a": 10, "b": 15}}, {"name": "multiply", "args": {"a": 25, "b": 4}}]`
- attempt: `multiply({"a": "add", "b": "10", "result": "25"})` → unknown_args (Unknown argument(s) ['result'] for 'multiply'. Valid arguments: ['a', 'b'].)
- final text: ''; stop: final_answer

**llama3.2:3b | single_shot | dev_n2**: Who painted the Mona Lisa?
- expected: `[]`
- attempt: `get_employee({"name": "Leonardo"})` → unknown_args (Unknown argument(s) ['name'] for 'get_employee'. Valid arguments: ['employee_id'].)
- final text: ''; stop: final_answer

## unneeded_call (2 runs)

**llama3.2:3b | single_shot | dev_n1**: What is the capital of Japan?
- expected: `[]`
- attempt: `get_weather({"city": "Tokyo", "unit": "celsius"})` → ok
- final text: ''; stop: final_answer

**llama3.2:3b | react | dev_n1**: What is the capital of Japan?
- expected: `[]`
- attempt: `get_weather({"city": "Tokyo", "unit": "celsius"})` → ok
- final text: 'The capital of Japan is Tokyo.'; stop: final_answer

## wrong_tool (1 runs)

**llama3.2:3b | react | dev_m1**: Add 10 and 15, then multiply the result by 4.
- expected: `[{"name": "add", "args": {"a": 10, "b": 15}}, {"name": "multiply", "args": {"a": 25, "b": 4}}]`
- attempt: `multiply({"a": "15", "b": "10"})` → ok
- final text: 'The result of adding 10 and 15 is 25. Multiplying 25 by 4 gives 100.'; stop: final_answer

