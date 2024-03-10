import os
import random

import openai
import tiktoken
from tenacity import retry, wait_random_exponential, stop_after_attempt
from termcolor import colored


openai.api_key = os.environ['OPENAI_API_KEY']

# Used only for token count presently
MODEL = "gpt-3.5-turbo"
# Used for retry
ATTEMPTS = 3



@retry(wait=wait_random_exponential(min=1, max=40), stop=stop_after_attempt(ATTEMPTS))
def logic_gate_request(messages, model="gpt-3.5-turbo-0613", temperature=0):
    try:
        response = openai.ChatCompletion.create(
            model=model,
            temperature=temperature,
            messages=messages,
            logit_bias={
                "1904": 100, # token for "true"
                "3934": 100  # token for "false"
            },
            max_tokens=1
        )
        # print(response)
        print(response["usage"])
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e


@retry(wait=wait_random_exponential(min=1, max=40), stop=stop_after_attempt(ATTEMPTS))
def token_list_request(messages, token_list, model="gpt-3.5-turbo", temperature=0):
    logit_bias = {}
    if len(token_list) > 300:
        raise ValueError("`token_list` must not exceed 300")
    for token in token_list:
        logit_bias[str(token)] = 100
    try:
        response = openai.ChatCompletion.create(
            model=model,
            temperature=temperature,
            messages=messages,
            logit_bias=logit_bias,
            max_tokens=1
        )
        # print(response)
        # print(response["usage"])
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e


@retry(wait=wait_random_exponential(min=1, max=40), stop=stop_after_attempt(ATTEMPTS))
def limited_tokens_request(
    messages, 
    token_list, 
    max_tokens=100, 
    model="gpt-3.5-turbo", 
    temperature=0
):
    logit_bias = {}
    if len(token_list) > 300:
        raise ValueError("`token_list` must not exceed 300")
    for token in token_list:
        logit_bias[str(token)] = 100
    try:
        response = openai.ChatCompletion.create(
            model=model,
            temperature=temperature,
            messages=messages,
            logit_bias=logit_bias,
            max_tokens=max_tokens,
        )
        # print(response)
        # print(response["usage"])
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e


def get_content_from_response(response):
    try:
        content = response.choices[0].message["content"]
        return content
    except AttributeError as e:
        print(f"Error in get_content_from_response: {e}")
        return None

# ---------------- TOKEN RELATED FUNCTIONS ----------------- #
def check_list_each_one_token(list_to_check: list):
    """
    Gets token encoding for each item in a list (converted to a string), returns `True` if all strings can be represented by one token, else returns `False`
    """
    string_list = []
    for item in list_to_check:
        string_list.append(str(item))
    
    encodings = []
    
    for string in string_list:
        encoding = get_encodings_for_string(string)
        encodings.append(encoding)
    
    
    length_over_one = 0
    
    for token in encodings:
        if len(token) > 1:
            length_over_one += 1
    
    if length_over_one:
        print(f"Strings with token length over 1: {length_over_one}")
        return False
    else:
        return True
        

def get_token_list(strings: list) -> list:
    """
    If returns more than one token for string, raises ValueError.
    """
    tokens = []
    for string in strings:
        encodings = get_encodings_for_string(str(string))
        if len(encodings) > 1:
            raise ValueError(f"More than one token returned for string {string}")
        tokens.append(encodings[0])
    return tokens


def get_string_from_token(token):
    token_list = [token]
    encoding = tiktoken.encoding_for_model(MODEL)
    string = encoding.decode(token_list)
    return string


def get_encodings_for_string(string):
    encoding = tiktoken.encoding_for_model(MODEL)
    return encoding.encode(string)

        
def num_tokens_from_string(text: str) -> int:
    encoding = tiktoken.encoding_for_model(MODEL)
    num_tokens = len(encoding.encode(text))
    return num_tokens
    

# HANDLING LISTS ON TOKENS
def get_token_counts(string_list):
    token_counts = [num_tokens_from_string(item) for item in string_list]
    return token_counts


def split_list_to_batches(string_list, token_limit=1000, randomize_order=False):
    if randomize_order:
        string_list = string_list.copy()  # Create a copy to avoid shuffling the original list
        random.shuffle(string_list)
        
    batches = []
    batch = []
    current_token_count = 0

    token_counts = get_token_counts(string_list)

    for i, token_count in enumerate(token_counts):
        if (current_token_count + token_count) <= token_limit:
            batch.append(string_list[i])
            current_token_count += token_count
        else:
            batches.append(batch)
            batch = [string_list[i]]
            current_token_count = token_count

    # Append the last batch if it is not empty
    if batch:
        batches.append(batch)

    return batches


def split_list_to_batches_overlap(string_list, token_limit=1000, randomize_order=False):
    if randomize_order:
        string_list = string_list.copy()  # Create a copy to avoid shuffling the original list
        random.shuffle(string_list)
        
    batches = []
    batch = []
    current_token_count = 0

    token_counts = get_token_counts(string_list)

    for i, token_count in enumerate(token_counts):
        if (current_token_count + token_count) <= token_limit:
            batch.append(string_list[i])
            current_token_count += token_count
        else:
            batches.append(batch)
            # Start a new batch with the current string
            batch = [string_list[i]]
            # Reset current_token_count to the token count of the current string
            current_token_count = token_count

        # If this is not the first batch and the current string is not already in the previous batch,
        # add it to the previous batch
        if batches and batches[-1][-1] != string_list[i]:
            batches[-1].append(string_list[i])

    # Append the last batch if it is not empty
    if batch:
        batches.append(batch)

    return batches



# --------------- APPLICATIONS ---------------- #

def choose_tool(tools, query, task="the user's query", goal=""):
    """
    Chooses best tool for given task and returns key for tool from `tools` dict. `tools` should be dict with single (?) integers as keys.
    """
    messages = [
        {"role": "system", "content": f"Your goal is to recommend the best tool for {task}.\n- Respond with the index of the best tool to use: {tools}"},
        {"role": "user", "content": query}
    ]
    
    token_list = get_token_list(tools.keys())

    response = token_list_request(messages, token_list)
    content = response.choices[0].message["content"]
    return content


def true_or_false(query):
    """Feeds prompt to model with directive to return true or false. Responds `True` if true, else `False`"""
    messages = [
        {"role": "system", "content": "Respond true or false to the user's query"},
        {"role": "user", "content": query}
    ]
    response = logic_gate_request(messages)
    content = response.choices[0].message["content"]
    if content == "true":
        return True
    elif content == "false":
        return False
    else:
        raise ValueError("Response other than true or false")


def format_dictionary_for_select_token(
    d, 
    enclose_keys_in_quotations: bool = False,
    enclose_values_in_quotations: bool = False,
) -> str:
    """
    Format a dictionary for use with select token. Optionally, keys and/or values can be enclosed in quotations.

    Args:
        d (Dict[str, Union[str, int, float]]): Dictionary to format.
        enclose_keys_in_quotations (bool, optional): If True, keys are enclosed in quotations. Defaults to False.
        enclose_values_in_quotations (bool, optional): If True, values are enclosed in quotations. Defaults to False.

    Raises:
        ValueError: If any key in the dictionary is not a single token.

    Returns:
        str: Formatted string representation of the dictionary.
    """
    keys = d.keys()
    all_one_token = check_list_each_one_token(keys)
    if not all_one_token:
        raise ValueError("Dict key must be one token, use `check_list_each_one_token` first before calling")

    formatted = ""
    for key, value in d.items():
        formatted_key = f'"{key}"' if enclose_keys_in_quotations else key
        formatted_value = f'"{value}"' if enclose_values_in_quotations else value
        formatted += f'{formatted_key}: {formatted_value}\n'
    
    return formatted


def create_dictionary_with_number_key(options_list: list) -> dict:
    values = [str(item) for item in options_list]
    keys = range(len(options_list))

    options_dict = dict(zip(keys, values))
    return options_dict


def get_options_string_and_dict(options_list: list) -> str:
    options_dict = create_dictionary_with_number_key(options_list)
    options_string = format_dictionary_for_select_token(options_dict)
    return options_string, options_dict


# DEFAULT FOR GET_OPTION_FOR_QUERY_FROM_LIST
# Must contain `{options_string}` and `{query}` somewhere in text. 
DEFAULT_PROMPT = """From these options:
'''
{options_string}
'''
Which is best to answer this query:
Query: {query}
Index of best option:"""


def get_option_for_query_from_list(
    query: str, 
    options_list: list,
    system_prompt: str = "You are a research expert.",
    template_prompt: str = DEFAULT_PROMPT,
    debug: bool = False,
    model = "gpt-3.5-turbo",
    temperature = 0,
    ) -> str:
    """
    This function is used to identify the most appropriate option for a given user query from a list of options.

    The function uses a system prompt and a template prompt to generate a user prompt. It then extracts tokens from 
    the user query and matches these with options from the provided list. The function returns the option that 
    best matches the user query.

    Parameters:
    query (str): The user query for which an appropriate option is to be identified.
    options_list (list): A list of options from which the function selects the most appropriate option.
    system_prompt (str, optional): A system prompt that aids in generating the user prompt. Default is "You are a research expert.".
    template_prompt (str, optional): A template prompt that is used to structure the user prompt. Default is DEFAULT_PROMPT.
    debug (bool, optional): If True, the function prints debugging information. Default is False.

    Returns:
    str: The chosen option from the options_list that best matches the user query.

    Note:
    The function assumes the existence of the following functions: `get_options_string_and_dict`, `get_token_list`, 
    `token_list_request`, and `get_content_from_response`. Make sure these functions are defined and working as expected.
    The `template_prompt` must contain `{options_string}` and `{query}` somewhere in it.
    The `system_prompt` can have a significant effect on results.
    """
    options_string, options_dict = get_options_string_and_dict(options_list)

    prompt = template_prompt.format(options_string=options_string, query=query)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    token_list = get_token_list(options_dict.keys())

    response = token_list_request(messages, token_list, model=model, temperature=temperature)
    if debug:
        print(f"\nResponse:\n{response}")

    content = get_content_from_response(response)

    chosen_option = options_dict[int(content)]

    return chosen_option


# ------------------------ TESTS --------------------------- #
# ------------------------ Logit Bias ---------------------- #
def run_logit_bias_tests():
    test_token_list_request()
    test_logic_gate_request()
    test_choose_tool()
    test_true_or_false()


def test_choose_tool():
    tools = {
        "1": "Google",
        "2": "Wikipedia",
        "3": "The New York Times"
    }
    query = "I'm looking for the current weather"
    tool_index = choose_tool(tools, query)
    print(tool_index)
    print(tools[tool_index])
    

def test_token_list_request():
    strings = ["happy", "sad", "mad"]
    token_list = get_token_list(strings)

    messages = [
        {"role": "user", "content": "Classify this text as happy, sad, or mad:\nI hate Twitter!"}
    ]

    response = token_list_request(messages, token_list)
    content = get_content_from_response(response)
    print(content)


def test_logic_gate_request():
    messages = [
        {"role": "user", "content": "Is 5 greater than 4?"}
    ]
    print(messages)
    
    response = logic_gate_request(messages)
    content = response.choices[0].message["content"]
    
    print(content)


def test_true_or_false():
    query = "Five is greater than four"
    answer = true_or_false(query)
    print(answer)



def test_check_list_each_one_token():
    """
    For example, shows that the numbers 1 to 1000 are all one token, but every number above that is more than one
    """
    list = range(1, 1000)
    list_is_one_token = check_list_each_one_token(list)
    print(f"List is of one token items: {list_is_one_token}")


def test_format_dictionary_for_select_token():
    test_format = {
        "1": "New York Times",
        "2": "Wikipedia",
        "300": "Google",
    }

    formatted = format_dictionary_for_select_token(test_format)
    print(formatted)

    keys_quotations = format_dictionary_for_select_token(test_format, enclose_keys_in_quotations=True)
    print(keys_quotations)

    values_quotations = format_dictionary_for_select_token(test_format, enclose_values_in_quotations=True)
    print(values_quotations)

    both_quotations = format_dictionary_for_select_token(test_format, enclose_keys_in_quotations=True, enclose_values_in_quotations=True)
    print(both_quotations)