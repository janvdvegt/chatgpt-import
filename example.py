# import logging
# logging.getLogger().setLevel(logging.DEBUG)

from chatgpt import quick_sort, roman_to_integer, recursive_merge_dicts

result = quick_sort([3, 6, 8, 10, 1, 2, 1])
print(result)


result = roman_to_integer("LVII")
print(result)


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
