# ChatGPT importer

Why go through the effort of navigating to `chat.openai.com` to get some generated code when you can import it directly?

Introducing "ChatGPT importer"!

Just import the function you need in Python:

```python
from chatgpt import roman_numeral_to_int

roman_numeral = "LVII"

# Calculate the corresponding integer
output = roman_numeral_to_int(roman_numeral)

# Print the int, should produce: 57
print(output)
```

As it uses the function signature and the arguments of the first invocation to generate the function, it can deal with unexpected arguments. Here is an example recursively merging dictionaries:

```python
from chatgpt import recursive_merge_dicts

original_dict = {"a": 1, "b": {"b1": 2, "b2": 3}} 
additional_dicts = [
    {"b": {"b1": 5, "b2": 6}},
    {"a": 4},
    {"a": 8, "b": {"b1": 9}}
]

# The fact that the second argument is a list of dictionaries is used to prompt OpenAI
output = recursive_merge_dicts(original_dict, additional_dicts)

# Print the merged dict, should produce {"a": 8, "b": {"b1": 9, "b2": 6}}
print(output)
```

## Setup

Make sure to set a valid `OPENAI_API_KEY` in your environment variables and install `requirements.txt`.

## Features

### Lazy loading

When importing your function it doesn't actually produce the function yet, it just provides a (GPT) wrapper. When invoking the function for the first time it uses the following information to produce a function:

- Function name
- A string representation of the (nested) `*args` and `**kwargs`
- The passed values as example values

The prompt includes these values together with a request to generate a Python function within a Markdown `python` block. The code is extracted from the response, checked for valid syntax, loaded into the namespace and executed against the inputs.

### Retries

While the generated functions are usually correct, the produced syntax might not be correct or the function might fail during execution. When this happens, `chatgpt` will regenerate the function with the previous implementations and associated error messages included in the prompt. The number of retries is capped at 3.

### Caching

The function is cached after successful generation. The cache is keyed on the function signature. This means that the next time you invoke the function it will check the cache if there was a previous invocation with the same argument structure, and if so it will reuse that one. This means that you can "safely" run the following code without paying a month of rent to OpenAI:

```python
from chatgpt import square_number

squared_numbers = [square_number(i) for i in range(10000)]
```

### Logging

You can set the logging level to `DEBUG` to log a lot of what is happening under the hood as follows:

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

## Disclaimer

Please don't use this in production. I am not liable in any way for any damages.

## Inspiration

This is inspired by the `stack-overflow-import` project found on [GitHub](https://github.com/drathier/stack-overflow-import).
