import pandas
import math
import time

from pprint import pprint

from typing import Any

from streamlit.civix.data import load_statute_dataframe
from question_answering.openai_api import format_dictionary_for_select_token, token_list_request, get_content_from_response, get_token_list, limited_tokens_request, split_list_to_batches, split_list_to_batches_overlap

# ------------- TODO -------------- #
# Handle batch token limits/logit bias limit more intelligently (so don't have to guess)
# Can have user x out irrelevant ones from list
# Could have smaller list of "core" statutes to pick from


def main():
    print("Starting tests")
    # test_choose_multiple_bc_statutes()
    # test_choose_bc_statute()
    # test_different_strategies_tenancy()
    # test_choose_statute_from_all_statutes()
    # test_choose_statute_from_overlapping_batches(batch_token_size)
    # test_overlapping_batch_token_size()
    # test_queries_for_choose_multiple_limit_len()
    # test_get_narrowed_down_statute_options()
    # test_get_narrowed_down_statute_options_ratios_times()
    # run_test_system_prompts_for_queries()
    
    print("Ending Tests")



def choose_bc_statute(
    query: str, 
    statutes: list, 
    system_prompt: str="You are an expert British Columbia lawyer experienced in all areas of the law. You communicate only in single numbers. Choose **only** the **most likely** statute.",
    model="gpt-3.5-turbo",
    temperature=0,
) -> Any:
    values = [str(item) for item in statutes]
    keys = range(len(statutes))
    
    statute_choice_dict = dict(zip(keys, values))
    # print(statute_choice_dict)

    formatted = format_dictionary_for_select_token(statute_choice_dict)
    # print(formatted)

    prompt = f"""
Here is a list of British Columbia Statutes by index number:
{formatted}

Return the index of the statute that should be queried in order to answer the following question:
{query}

Index:
"""

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    token_list = get_token_list(statute_choice_dict.keys())
    response = token_list_request(messages, token_list)
    # print(response)
    
    content = get_content_from_response(response)

    statute = statute_choice_dict[int(content)]

    return statute


def choose_multiple_bc_statutes(
    query: str, 
    statutes: list, 
    system_prompt: str="You are an expert British Columbia lawyer experienced in all areas of the law. You communicate only in single numbers separated by spaces, representing the indices of statutes. Choose **only** the **most likely** statutes.",
    model: str="gpt-3.5-turbo",
    temperature: float=0,
    results_ratio: float=.1
) -> list:
    values = [str(item) for item in statutes]
    keys = range(len(statutes))
    
    statute_choice_dict = dict(zip(keys, values))
    # print(statute_choice_dict)

    formatted = format_dictionary_for_select_token(statute_choice_dict)
    # print(formatted)

    prompt = f"""
Here is a list of British Columbia Statutes by index number:
{formatted}

Return the index(es) of the statute(s) that should be queried in order to answer the following question:
{query}

Index(es) separated by " ":
"""

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    # Append 220, token for " ", to the list
    token_list = get_token_list(statute_choice_dict.keys())
    token_list.append("220")
    if not token_list:
        raise ValueError("`token_list` must not be none")

    max_tokens = math.ceil((2*len(statutes) - 1)*results_ratio)
    response = limited_tokens_request(messages, token_list, max_tokens=max_tokens)
    content = get_content_from_response(response)
    indices = content.strip().split(" ")
    statutes = []

    for index in indices:
        statutes.append(statute_choice_dict[int(index)])
    
    return statutes

    
# ---------------- APPLICATIONS ----------------- #
def get_narrowed_down_statute_options(
    query: str,
    model: str="gpt-3.5-turbo",
    temperature: float=0,
    initial_results_ratio: float=.2,
    final_results_ratio: float=.2,
    batch_token_size: int=300,
    batch_overlap=False,
    randomize_order=True,
    time_function=False,
    debug=False,
):
    # NO MORE CHANGES TO DEFAULTS! RETURNS ABOUT 5
    batches = get_statute_batches(
        token_limit=batch_token_size, 
        randomize_order=randomize_order, 
        overlap=batch_overlap,
    )

    narrowed_options_all = []

    if time_function == True:
        start_all_time = time.time()
        start_interim_narrowed_time = time.time()
        choose_multiple_times = []
    
    for batch in batches:
        if time_function == True:
            start_choose_multiple_time = time.time()
        
        statutes = choose_multiple_bc_statutes(
            query=query, 
            statutes=batch, 
            results_ratio=initial_results_ratio, 
            temperature=temperature,
            model=model,
        )
        if time_function == True:
            choose_multiple_times.append(time.time() - start_choose_multiple_time)
        narrowed_options_all += statutes

    if time_function == True:
        interim_narrowed_time = time.time() - start_interim_narrowed_time

    narrowed_options = set(narrowed_options_all)
    
    if debug:
        print(f"Interim narrowed options: {narrowed_options}\nNumber: {len(narrowed_options)}")

    if len(narrowed_options) > 300:
        raise ValueError("Narrowed options length must be less than 300. Adjust initial_result_ratio")

    if time_function == True:
        start_final_narrowed_time = time.time()
    
    final_options = choose_multiple_bc_statutes(
        query, 
        narrowed_options,
        model=model,
        temperature=temperature,
        results_ratio=final_results_ratio,
    )
    if time_function == True:
        final_narrowed_time = time.time() - start_final_narrowed_time
        all_time = time.time() - start_all_time
        times = {
            "all_time": all_time, 
            "interim_narrowed_time": interim_narrowed_time, 
            "choose_multiple_times": choose_multiple_times, 
            "final_narrowed_time": final_narrowed_time
        }
        pprint(times)
        
    return set(final_options)


def choose_statute_from_overlapping_batches(query, batch_token_size=800, randomize_order=True, debug=False):
    """Gets overlapping batches, gets top pick from each, gets top pick from those options."""
    statute_batches = get_statute_batches(overlap=True, token_limit=batch_token_size, randomize_order=True)
    
    statute_options = []
    
    for statutes in statute_batches:
        option = choose_bc_statute(query, statutes)
        if debug:
            print(f"Query: {query}\nOption: {option}")
        statute_options.append(option)

    # DEBUG
    if debug:
        print(f"Options (no dedup): {statute_options}")
    options_set = set(statute_options)
    if debug:
        print(f"Options (set): {options_set}")
    chosen_statute = choose_bc_statute(query, options_set)
    if debug:
        print(f"Chosen statute: {chosen_statute}")

    return chosen_statute, set(statute_options)


def choose_statute_from_all_statutes(query, batch_token_size=500):
    """From regular batches of `batch_token_size`, applies `choose_bc_statute` to all to create list, and then picks top in list"""
    # IDEAS: use overlapping batches
    statute_batches = get_statute_batches(token_limit=batch_token_size)
    # pprint(statute_batches)
    # print(f"Number of batches: {len(statute_batches)}")

    statute_options = []
    
    for statutes in statute_batches:
        option = choose_bc_statute(query, statutes)
        print(f"Query: {query}\nOption: {option}")
        statute_options.append(option)

    chosen_statute = choose_bc_statute(query, statute_options)
    print(f"Chosen statute: {chosen_statute}")

    return chosen_statute, statute_options


def choose_multiple_then_one_bc_statute(query: str, statutes: list) -> str:
    chosen_statutes = choose_multiple_bc_statutes(query, statutes)
    final_statute = choose_bc_statute(query, chosen_statutes)
    return final_statute


# TODO MOVE ALL TO MORE APPROPRIATE PLACE
# --------------- UTILITIES ---------------- #

def get_statute_batches(token_limit=500, overlap=False, randomize_order=True):
    statutes = load_statutes()
    if overlap:
        batches = split_list_to_batches_overlap(statutes, token_limit=token_limit, randomize_order=True)
    else:
        batches = split_list_to_batches(statutes, token_limit=token_limit, randomize_order=True)
    
    return batches
    

def load_statutes():
    statute_df = load_statute_dataframe()
    statutes_all = statute_df["name"].tolist()
    statutes = [item for item in statutes_all if item is not None and item != ""]
    return statutes

    



# ------------------- TESTS ----------------------- #

def test_choose_bc_statute():
    statutes = ["Access to Abortion Act", "Residential Tenancy Act"]
    query = "I want to know about rent"
    statute = choose_bc_statute(query, statutes)
    print(statute)
    

def test_choose_multiple_bc_statutes():
    statutes = [
        "Commercial Tenancy Act", 
        "Residential Tenancy Act",
        "Strata Property Act",
        "Land Title Act",
        "Access to Abortion Act",
        "Land Title Act",
        "Property Law Act",
        "Land Title Registry Regulations",
        "Law and Equity Act",
        "Residential Tenancy Dispute Resolution Regulations"
    ]

    query = "I want to know about my rights as a renter in a residential property"

    statutes = choose_multiple_bc_statutes(query, statutes)
    print(statutes)


def test_choose_statutes_non_string():
    # TODO - include description of statutes
    pass

    

def test_different_strategies_tenancy():
    statutes = [
        "Commercial Tenancy Act", 
        "Residential Tenancy Act",
        "Strata Property Act",
        "Land Title Act",
        "Access to Abortion Act",
        "Land Title Act",
        "Property Law Act",
        "Land Title Registry Regulations",
        "Law and Equity Act",
        "Residential Tenancy Dispute Resolution Regulations"
    ]

    # List of tuples with query first then correct answer (some subjectivity)
    query_pairs = [
        ("I want to know my rights as a renter", "Residential Tenancy Act"),
        ("I want to know my rights as a renter of a commercial property", "Commercial Tenancy Act"),
        ("I own a property and I'm in a fight with a renter who lives there", "Residential Tenancy Dispute Resolution Regulations"),
        ("I need to access health care but my doctor is refusing to help", "Access to Abortion Act"),
        ("I just bought a property and there's an issue with an easement", "Land Title Act"),]

    log = test_statutes_query_pairs(statutes, query_pairs)
    pprint(log, indent=2)


def test_statutes_query_pairs(statutes, query_pairs):
    log = {}
    log["statutes"] = statutes
    log["query_pairs"] = query_pairs
    
    results = []

    functions_to_test = choose_bc_statute, choose_multiple_bc_statutes, choose_multiple_then_one_bc_statute
    
    for query in query_pairs:
        result = {}
        query, answer = query
        result["query"] = query
        result["answer"] = answer

        function_results = {}
        for function in functions_to_test:
            function_results[function.__name__] = function(query, statutes)
        # function_results["choose_bc_statute"] = choose_bc_statute(query, statutes)
        # function_results["choose_multiple_bc_statutes"] = choose_multiple_bc_statutes(query, statutes)
        # function_results["choose_multiple_then_one_bc_statute"] = choose_multiple_then_one_bc_statute(query, statutes)

        result["function_results"] = function_results
        pprint(result)
        results.append(result)

    log["results"] = results

    return log  




def test_overlapping_batch_token_size():
    sizes = [200]
    query = "How do I register an easement"

    query_pair = (query, "Land Title Act")

    log = {}
    log["query_pair"] = query_pair

    for size in sizes:
        log[size] = {}
        log[size]["size"] = size
        result = test_choose_statute_from_overlapping_batches(query=query_pair[0], batch_token_size=size, randomize_order=True)
        log[size]["result"] = result

    pprint(log)



def test_choose_statute_from_overlapping_batches(query, batch_token_size, randomize_order=True):
    print(f"running test_choose_statute_from_overlapping_batches for batch_token_size {batch_token_size}")
    
    statute, statute_options = choose_statute_from_overlapping_batches(query, batch_token_size=batch_token_size, randomize_order=randomize_order)

    # result_string = f"\nQuery: {query}\nStatute: {statute}\nOptions: {statute_options}\n\n"
    
    # print(result_string)
    result = {}
    result["statute"] = statute
    result["statute_options"] = statute_options
    return result



def test_choose_statute_from_all_statutes(query):

    # Display as recommendation
    statute, statute_options = choose_statute_from_all_statutes(query)

    print(f"\nQuery: {query}\nStatute: {statute}\nOptions: {statute_options}\n\n")

    return statute, statute_options



def test_queries_for_choose_multiple_limit_len():
    queries = [
        "How do I register an easement?"
    ]

    for query in queries:
        all_options = test_choose_multiple_bc_statutes_limit_len(query)
        print(f"Query:{query}\nAll options: {all_options}")



def test_choose_multiple_bc_statutes_limit_len(query):
    batches = get_statute_batches(token_limit=500, randomize_order=True)

    all_options = []
    
    for batch in batches:
        statutes = choose_multiple_bc_statutes(query, batch)
        all_options += statutes

    return all_options


def test_get_narrowed_down_statute_options_ratios_times():
    # TODO can make it so that has to pass multiple options being in returned list
    query_pairs = [
        ("If I'm the executor of an estate, what do I have to do?", "Wills, Estates and Succession Act"),
        ("How can I remove an easement from title to my property?", "Property Law Act"),
        
    ]

    ratios = [
        # {"initial_results_ratio": .05, "final_results_ratio": .5},
        # {"initial_results_ratio": .1, "final_results_ratio": .3},
        # {"initial_results_ratio": .2, "final_results_ratio": .2},
        # {"initial_results_ratio": .3, "final_results_ratio": .1},
        {"initial_results_ratio": .2, "final_results_ratio": .3},
    ]

    log_data = []

    for pair in query_pairs:
        query, answer = pair
        for ratio in ratios:
            start_time = time.time()
            statutes = get_narrowed_down_statute_options(query, time_function=True, **ratio)
            time_taken = time.time() - start_time
            correct_in_statutes = answer in statutes

            log_entry = {
                'Query': query,
                'Answer': answer,
                'Ratios': ratio,
                'Statutes': statutes,
                'Correct In Statutes': correct_in_statutes,
                'Time': time_taken,
            }

            log_data.append(log_entry)

    pprint(log_data)


def test_get_narrowed_down_statute_options():
    query_pairs = [
        ("What are my rights as a renter?", "Residential Tenancy Act"),
        ("If I'm the executor of an estate, what do I have to do?", "Wills, Estates and Succession Act"),
    ]
    
    for pair in query_pairs:
        query, answer = pair
        statute_options = get_narrowed_down_statute_options(query, time_function=True)
        print("")
        print(f"Pair: {pair}\nNarrowed options: {statute_options}")
        if answer not in statute_options:
            print("Answer not in options, test FAILED")
        else:
            print("Answer is in options, test PASSED")
        print("")

def run_test_system_prompts_for_queries():
    query_pairs = [
        ("When can my landlord raise my rent?", "Residential Tenancy Act"),
    ]

    for pair in query_pairs:
        test_system_prompts(pair)
    

def test_system_prompts(query_pair):
    
    system_prompts = [
        # "You are an expert legal researcher familiar with the laws of British Columbia. You will return the indices of the statutes which are most closely related to the user's query.",
        # "You are a helpful assistant",
        # "You are an expert legal researcher familiar with the laws of British Columbia. Return statutes indices, in order of the highest likelihood of containing the answer to the user's query.",
        # "You are an expert legal researcher. You communicate only in single numbers separated by spaces, representing the indices of statutes. Choose only the most likely statutes.",
        # "You are an expert legal researcher. You communicate only in single numbers separated by spaces, representing the indices of statutes. Choose **only** the **most likely** statutes.",
        "You are an expert British Columbia lawyer experienced in all areas of the law. You communicate only in single numbers separated by spaces, representing the indices of statutes. Choose **only** the **most likely** statutes."
    ]

    query, answer = query_pair
    
    batches = get_statute_batches(overlap=False, token_limit=500, randomize_order=True)

    result = {}

    result["query"] = query
    result["answer"] = answer
    
    common_answer = None
    for index, prompt in enumerate(system_prompts):
        statute_lists = []
        all_statutes = []
        for batch in batches:
            statutes = choose_multiple_bc_statutes(query, statutes=batch, system_prompt=prompt, results_ratio=.1)
            statute_lists.append(statutes)
            all_statutes += statutes
    
        result[index] = {
            "prompt": prompt,
            # "statutes": all_statutes,
            "includes_answer": answer in all_statutes,
            "statute_lists": statute_lists
        }
    
        if common_answer is None:
            common_answer = set(all_statutes)
        else:
            common_answer = common_answer.intersection(all_statutes)
    
    result["common_answer"] = list(common_answer)

    
    pprint(result)
    return result

    
if __name__ == "__main__":
    main()