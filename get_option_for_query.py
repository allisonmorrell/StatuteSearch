import random
import os

from typing import List
import math

import openai
import tiktoken
from tenacity import retry, wait_random_exponential, stop_after_attempt

# Used only for token count presently
MODEL = "gpt-3.5-turbo"
# Used for retry
ATTEMPTS = 3

openai.api_key = os.environ['OPENAI_API_KEY']

@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(ATTEMPTS))
def token_list_request(
    messages,
    token_list,
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
            max_tokens=1
        )
        # print(response)
        # print(response["usage"])
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e


@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(ATTEMPTS))
def limited_tokens_request(
    messages,
    token_list,
    max_tokens=500,
    model="gpt-3.5-turbo",
    temperature=0,
    stop: list[str]=None,
):
    logit_bias = {}
    if len(token_list) > 300:
        raise ValueError("`token_list` must not exceed 300")
    for token in token_list:
        logit_bias[str(token)] = 100
    try:
        if stop:
            response = openai.ChatCompletion.create(
            model=model,
            temperature=temperature,
            messages=messages,
            logit_bias=logit_bias,
            max_tokens=max_tokens,
            stop=stop,
        )
        else:
            response = openai.ChatCompletion.create(
                model=model,
                temperature=temperature,
                messages=messages,
                logit_bias=logit_bias,
                max_tokens=max_tokens,
            )
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e


@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(ATTEMPTS))
def stop_sequence_request(
    messages,
    max_tokens=1000,
    model="gpt-3.5-turbo",
    temperature=0,
    stop: list[str]=None,
):
    try:
        response = openai.ChatCompletion.create(
        model=model,
        temperature=temperature,
        messages=messages,
        max_tokens=max_tokens,
        stop=stop,
        )
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

# ------------- TOKEN RELATED FUNCTIONS ------------ #

def check_list_each_one_token(list_to_check: list) -> bool:
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


def test_get_option_for_query_from_list():
    query = "Who's the president of the United States?"

    options_list = [
        "Google",
        "Wikipedia",
        "IMDB"
    ]
    chosen_option = get_option_for_query_from_list(query, options_list, debug=True)
    print(chosen_option)

# UNCOMMENT TO RUN
# test_get_option_for_query_from_list()





DEFAULT_TEMPLATE_PROMPT_MULTIPLE = """Consider these options:
{options_string}

Which options are most relevant to this query:
{query}

Options by greatest relevance:"""


DEFAULT_SYSTEM_PROMPT_MULTIPLE = """You are a research expert.

Return index numbers of chosen options separated by " " and ending with "."."""

# TODO
# implement use stop
# implement appending instruction to system prompt for delimeter and stop or not. 
def get_multiple_options_for_query_from_list(
    query: str,
    options_list: List[str],
    system_prompt: str = DEFAULT_SYSTEM_PROMPT_MULTIPLE,
    template_prompt: str = DEFAULT_TEMPLATE_PROMPT_MULTIPLE,
    debug: bool = False,
    model: str = "gpt-3.5-turbo",
    temperature: float = 0,
    results_ratio: float = 1,
    use_stop = True,
) -> List[str]:
    # TODO parameterize stop sequences and delimeters.
    options_string, options_dict = get_options_string_and_dict(options_list)
    prompt = template_prompt.format(options_string=options_string, query=query)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    # DEBUG
    #for message in messages:
        #print(f"**{message['role']}:** {message['content']}\n")

    token_list = get_token_list(options_dict.keys())
    token_list.append("220")  # Adding the token for " "
    token_list += get_encodings_for_string(".") # Adding stop token
    max_tokens = math.ceil(2*len(options_list)*results_ratio - 1)

    response = limited_tokens_request(messages, token_list, model=model, temperature=temperature, max_tokens=max_tokens, stop=["."])
    if debug:
        print(f"\nResponse:\n{response}")

    content = get_content_from_response(response)

    # DEBUG
    #print(f"**assistant:** {content}")

    indices = content.strip().split(" ")  # Splitting the returned string into a list of indices
    chosen_options = [options_dict[int(index)] for index in indices if index.strip()]


    return chosen_options

# ------------------ TESTS --------------- #


def test_get_multiple_options_for_query_from_list():
    # Tests
    options_list = ["apple", "banana", "orange", "grapefruit", "mango", "strawberry", "blueberry", "pineapple", "watermelon", "kiwi", "pear", "peach", "plum", "cherry", "raspberry", "blackberry", "pomegranate", "lemon", "lime", "grape"]
    options_list_detailed = [
        "apple: Its crisp texture contrasts well with softer fruits like bananas and peaches. The slightly tart flavor pairs well with sweeter fruits, like strawberries and pears. Use as a main base component.",
        "banana: With its soft and creamy texture, it pairs well with crisp fruits such as apples and pears. Its sweet flavor complements tart fruits like oranges and strawberries. Best used as a secondary base.",
        "orange: The juicy and slightly tart flavor pairs perfectly with sweet fruits like mango and strawberries. Its citrus note can also enhance the overall flavor of the fruit salad.",
        "grapefruit: With its unique balance of sweet, sour and bitter, it complements sweet fruits like bananas and pineapples. Best used sparingly due to its strong flavor.",
        "mango: The sweet, tropical flavor makes it a standout in any fruit salad. Pairs well with the tartness of berries and citrus fruits like oranges and strawberries.",
        "strawberry: Its sweet yet mildly tart flavor pairs well with most fruits, making it versatile. They're great with bananas, apples, and citrus fruits.",
        "blueberry: Adds a nice pop of tartness that balances sweeter fruits like bananas and peaches. Its small size also adds textural diversity.",
        "pineapple: Its sweet and slightly tart flavor is a great complement to all other fruits. Adds a tropical feel when combined with mango and banana.",
        "watermelon: Very hydrating with a subtle sweetness. Pairs well with tart fruits like citrus or berries. Due to its high water content, add just before serving.",
        "kiwi: With its tangy sweetness and unique texture, it pairs well with sweet fruits like strawberries and mango. It can add a colorful pop to your fruit salad.",
        "pear: It's sweet, juicy, and slightly grainy texture pairs well with tart fruits like raspberries and blueberries. Use as a base or secondary component.",
        "peach: Its sweet and slightly tangy flavor makes it a great pairing with berries, cherries, and pears. Best added just before serving to prevent browning.",
        "plum: Sweet yet slightly tart, it complements the flavor of both berries and citrus fruits. Their soft texture contrasts well with crunchier fruits like apples.",
        "cherry: Its sweet-tart flavor pairs well with almost any fruit, but especially with peaches and berries. Pit before adding to the salad.",
        "raspberry: Their sweet-tart flavor and soft texture pairs well with apples, peaches, and pears. Can be used sparingly for a pop of flavor and color.",
        "blackberry: Similar to raspberries, they pair well with sweeter fruits like peaches and bananas. Their slightly tart flavor can balance the overall sweetness.",
        "pomegranate: Their tiny, juicy seeds add a sweet-tart flavor and a unique crunch. They work well with citrus fruits and apples. Use sparingly due to their strong flavor.",
        "lemon: Its tart flavor can balance the sweetness of other fruits. Use the juice to prevent browning of fruits like apples and pears, or the zest to add a fresh flavor note.",
        "lime: Similar to lemon, its tart flavor balances sweetness. Its juice can be used to prevent browning or to add a tangy twist, especially in tropical-themed salads with mango and pineapple.",
        "grape: Their sweetness pairs well with tart fruits like citrus and berries. Their small size and crunchy texture add variety. Use red, green, or a mix for visual interest."
    ]


    query = "Choose a reasonable number of fruits to make a fruit salad with"
    # Test 1: Select one option

    simple_system = ""

    run_ratio_tests(query, options_list, simple_system)

    run_ratio_tests(query, options_list_detailed, simple_system)


def run_ratio_tests(query, options_list, system):
    chosen_options_one = get_multiple_options_for_query_from_list(query, options_list, system_prompt=system, results_ratio=0.1)
    print(chosen_options_one)

    # Test 2: Select two options
    chosen_options_two = get_multiple_options_for_query_from_list(query, options_list, system_prompt=system, results_ratio=1)
    print(chosen_options_two)

    # Test 3: Select all options
    chosen_options_three = get_multiple_options_for_query_from_list(query, options_list, system_prompt=system, results_ratio=.5)
    print(chosen_options_three)

    results = [chosen_options_one, chosen_options_two, chosen_options_three]
    for result in results:
        print(len(result))
        for item in result:
            print(f"\n{item}")


# test_get_multiple_options_for_query_from_list()