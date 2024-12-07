import ast
import logging
import os
import re
import sys
from types import ModuleType
from typing import Any, Dict, List
from importlib.abc import MetaPathFinder, Loader

import requests


MAX_NUM_TRIES = 3


def create_merged_type_str(type_list: List[str]) -> str:
    unique_types = list(set(type_list))
    if len(unique_types) == 1:
        return unique_types[0]
    if len(unique_types) == 0:
        return "Any"
    return f"Union[{', '.join(unique_types)}]"


def get_type_structure_str(obj: Any) -> str:
    """
    Recursively determine the type structure of an object.
    """
    if isinstance(obj, list):
        types = [get_type_structure_str(o) for o in obj]
        return f"list[{create_merged_type_str(types)}]"
    elif isinstance(obj, dict):
        key_types = []
        value_types = []
        for key, value in obj.items():
            key_types.append(get_type_structure_str(key))
            value_types.append(get_type_structure_str(value))
        final_key_type = create_merged_type_str(key_types)
        final_value_type = create_merged_type_str(value_types)
        return f"dict[{final_key_type}, {final_value_type}]"
    elif isinstance(obj, tuple):
        return f"tuple[{', '.join(get_type_structure_str(o) for o in obj)}]"
    else:
        return type(obj).__name__


def generate_args_and_kwargs_types(*args, **kwargs) -> Dict[str, Any]:
    """
    Analyze the types of *args and **kwargs in a function call.
    """
    args_types = [get_type_structure_str(arg) for arg in args]
    kwargs_types = {key: get_type_structure_str(value) for key, value in kwargs.items()}
    
    args_and_kwargs_types = {
        "args_types": args_types,
        "kwargs_types": kwargs_types
    }
    logging.debug(args_and_kwargs_types)
    return args_and_kwargs_types


# Custom Loader
class ChatGPTLoader(Loader):
    def __init__(self):
        self.function_cache = {}

    def exec_function(self, module, function_name):
        wrapper_code = self._lazy_function(function_name)
        module.__dict__[function_name] = wrapper_code
        if function_name in module.__dict__:
            return module.__dict__[function_name]
        else:
            raise ImportError(f"Function '{function_name}' not defined in fetched code.")

    def _lazy_function(self, function_name):
        cache = {}

        def gpt_wrapper(*args, **kwargs):
            args_and_kwargs_types = str(generate_args_and_kwargs_types(*args, **kwargs))
            if args_and_kwargs_types in cache:
                return cache[args_and_kwargs_types](*args, **kwargs)
            num_tries = 0
            previous_implementations = []
            previous_error_messages = []
            while num_tries < MAX_NUM_TRIES:
                try:
                    code = self._generate_code(function_name,
                                               previous_implementations,
                                               previous_error_messages,
                                               *args, **kwargs)
                    logging.debug("GENERATED CODE")
                    logging.debug(code)
                    # Try parsing the code
                    ast.parse(code)
                except Exception as e:
                    num_tries += 1
                    continue
                try:
                    exec(code, globals())
                    func = globals()[function_name]
                    result = func(*args, **kwargs)
                    cache[args_and_kwargs_types] = func
                    return result
                except Exception as e:
                    num_tries += 1
                    previous_implementations.append(code)
                    previous_error_messages.append(str(e))
        return gpt_wrapper

    def _generate_prompt(self,
                         function_name: str,
                         previous_implementations: List[str],
                         previous_errors: List[str],
                         *args, **kwargs):
        args_and_kwargs_types = generate_args_and_kwargs_types(*args, **kwargs)
        logging.debug(str(args_and_kwargs_types))
        prompt = """# TASK

Implement a Python function that takes the most likely arguments based on the name of the function and the provided function signature and example parameters.

Return a very brief description and then the function in between ```python and ```.

For example, if the function name is `add`, with kwargs: {"a": "int", "b": "int"} the response could be:

```python
def add(a, b):
    return a + b
```

The function should be as simple as possible and should not include any additional functionality. The function should be a valid Python function and should not raise any exceptions.

# INPUT

The name to generate the function for is: `""" + function_name + """`

The args and kwargs TYPES for the function are: `""" + str(args_and_kwargs_types) +"""`

Example args are: `""" + str(args) + """

Example kwargs are: `""" + str(kwargs) + "`"

        if previous_implementations:
            prompt += "\n\n# PREVIOUS IMPLEMENTATIONS THAT FAILED\n"
            for i in range(len(previous_implementations)):
                prompt += f"\n## Implementation {i + 1}\n\n```python\n{previous_implementations[i]}\n```\n\n"
                prompt += f"\n## Error Message {i + 1}\n\n{previous_errors[i]}\n\n"
        logging.debug(prompt)
        return prompt

    def _extract_python_code(self, markdown):
        """Extract the first Python block from a Markdown string."""
        pattern = r"```python\n(.*?)```"
        return re.findall(pattern, markdown, re.DOTALL)[0]

    def _generate_code(self, name, previous_implementations, previous_errors, *args, **kwargs):
        API_KEY = os.getenv("OPENAI_API_KEY")
        if not API_KEY:
            raise Exception("API key not found. Please set the OPENAI_API_KEY environment variable.")

        # Endpoint for the OpenAI API
        url = "https://api.openai.com/v1/chat/completions"

        # Request headers
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        
        prompt = self._generate_prompt(name, previous_implementations, previous_errors, *args, **kwargs)
        messages = [{"role": "user", "content": prompt}]

        # Request payload
        data = {
            "model": "gpt-4o",
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 1000,
        }

        # Sending the request
        response = requests.post(url, headers=headers, json=data)

        # Handling the response
        if response.status_code == 200:
            response_json = response.json()
            content = response_json["choices"][0]["message"]["content"]
            code = self._extract_python_code(content)
            return code
        else:
            raise Exception(f"Failed to fetch code for function '{name}'")


# Custom Finder
class ChatGPTFinder(MetaPathFinder):
    def __init__(self):
        self.loader = ChatGPTLoader()

    def find_spec(self, fullname, path, target=None):
        if fullname == "chatgpt":
            from importlib.machinery import ModuleSpec
            return ModuleSpec(fullname, self.loader)
        return None

# Dynamic Module
class ChatGPTModule(ModuleType):
    def __init__(self, name):
        super().__init__(name)
        self._loader = ChatGPTLoader()

    def __getattr__(self, function_name):
        if function_name.startswith("__") and function_name.endswith("__"):
            raise AttributeError(f"Module 'chatgpt' has no attribute '{function_name}'")

        return self._loader.exec_function(self, function_name)

# Install Custom Importer
sys.meta_path.insert(0, ChatGPTFinder())
sys.modules["chatgpt"] = ChatGPTModule("chatgpt")