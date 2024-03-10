import requests
import random

from pprint import pprint

import pandas as pd

from termcolor import colored
from bs4 import BeautifulSoup, NavigableString

from get_option_for_query import get_encodings_for_string, get_content_from_response, limited_tokens_request

from streamlit.civix.embeddings_search.new_search import TextRanker


# THIS CONTAINS IN PROGRESS CODE FOR HYBRID OF SIMILARITY SEARCH AND OPTIONS RANKING.


def main():
    id = "02078_01"
    act_name = "Residential Tenancy Act"
    query = "When are a tenants rights for access to the property?"
    
    # df = get_top_average_df(id, act_name, query)
    # print(df)

    test_retrieve_section_by_id()


def test_retrieve_section_by_id():
    section_id = "d2e1640"
    html_document = get_html_document("02078_01")
    html_soup = BeautifulSoup(html_document)
    section_html = retrieve_section_by_id(section_id, html_soup)
    
# IMPLEMENTING RETRIEVAL BY ID 
def retrieve_section_by_id(section_id, html_soup):

    tag = html_soup.find("a", attrs={'name': section_id})

    if tag:
        text_tag = tag.parent
        # Find the nearest enclosing <div> tag
        div_tag = None
        parent = tag.find_parent()
        while parent is not None:
            if parent.name == 'div':
                div_tag = parent
                break
            parent = parent.find_parent()
        
        # Print the <div> tag
        print(div_tag)

    if not tag:
        tag = html_soup.find("p", id=section_id)
        if not tag:
            raise ValueError("Tag not found in a or p tags")
        text_tag = tag

    
    print(text_tag)


    section_html = ""
    return section_html






def get_top_average_df(id, act_name, query):
    """Retrieves html and xml from statute, gets a list of section numbers and headings, and retrieves a subset using vector search. Then that subset reversed in order, and passed to a prompt to return the section numbers of most relevant sections. That data combined and a weighted average taken, returning a dataframe with all data."""
    html_document = get_html_document(id)
    html_soup = BeautifulSoup(html_document)
    contents_list = get_contents_list(html_soup)
    
    sections_list = get_sections_list(contents_list)
            
    strings, relatedness = get_top_by_similarity(id, sections_list, query, top_n=20)
    strings = list(strings)
    strings.reverse()
    # TODO TODO Note that doing this with the actual section text would probably be better
    # See get_query_results function in statute_app.py
    best_sections = get_best_sections(act_name, strings, query, randomize=False, limit=len(strings) * 2)

    # print("Running weighted average")
    relatedness_weight = 0.1
    df = weighted_average(strings, relatedness, best_sections, weight=relatedness_weight)
    return df


def normalize_min_max(data):
    return (data - data.min()) / (data.max() - data.min())


def weighted_average(strings, relatedness, relevance_order, weight=.5):
    # Convert relevance rank into relevance score
    relevance_scores = [1 - normalize_min_max(pd.Series(range(len(relevance_order))))[i] for i in range(len(relevance_order))]

    # Create a dictionary of strings and their relevance scores
    relevance_dict = dict(zip(relevance_order, relevance_scores))

    # Prepare a dataframe
    df = pd.DataFrame({
        'String': strings,
        'Relatedness': normalize_min_max(pd.Series(relatedness)),
        'Relevance': [relevance_dict.get(s, 0) for s in strings],  # 0 relevance for strings not found in relevance_ranked
    })

    # Calculate Weighted Average
    df['Weighted_Average'] = weight * df['Relatedness'] + (1 - weight) * df['Relevance']
    # Sort by Weighted Average and return the sorted dataframe
    return df.sort_values('Weighted_Average', ascending=False)


def get_top_by_similarity(id, contents_list, query, top_n=10):

    text_ranker = TextRanker(embedding_filename=f"{id}-section_headings.csv", strings=contents_list)

    strings, relatedness = text_ranker.execute_query(query, top_n=top_n)
    # print(f"Strings: {strings}\nRelatedness: {relatedness}")
    
    return strings, relatedness


def get_best_sections(act_name, contents_list, query, limit=None, randomize=True):

    # print(contents_list)
    print(f"\n\nRunning on contents_list length {len(contents_list)}")
    if randomize:
        random.shuffle(contents_list)
        print("Randomized")
        print(f"Randomized contents list:")
        pprint(contents_list)
        # print(f"randomized: {contents_list}")

    # add, if length over certain, or if contains parts/divisions, choose from those first.
    
    contents_indices = []
    for item in contents_list:
        first = item.split()[0]
        if (first.lower() == "part" or first.lower() == "division" or first.lower() == "contents"):
            # print("first was part or division or contents")
            continue
        contents_indices.append(item.split()[0])

    # print(f"Contents indices: {contents_indices}")

    sections_string = ""
    for item in contents_indices:
        sections_string += f"{item} "

    # print(sections_string)

    section_encodings = list(set(get_encodings_for_string(sections_string)))
    # print(section_encodings)
    # print(f"Length of section_encodings: {len(section_encodings)}")
    
    stop = ["END"]

    for item in stop:
        section_encodings += get_encodings_for_string(item)

    contents_string = ""
    for item in contents_list:
        contents_string += f"{item}\n"
    

    system_prompt = "You are an expert lawyer in British Columbia. Respond with a list of section numbers separated by ' ', then 'END':"
    
    prompt = f"""Review these sections of the {act_name}:

{contents_string}

Choose the most relevant sections for this query: 
{query}

Return a list of only the most relevant section numbers. Separate each section number with a space (" "), and end the list with 'END'. List:"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    if limit:
        response = limited_tokens_request(messages=messages, token_list=section_encodings, stop=stop, max_tokens=limit)
    elif not limit:
        response = limited_tokens_request(messages=messages, token_list=section_encodings, stop=stop)
    #response = stop_sequence_request(messages, stop=stop)
    
    content = get_content_from_response(response)


    print(colored(f"Content from model: {content}", "red"))
    
    
    contents_dict = {}
    for item in contents_list:
        contents_dict[item.split()[0]] = item

    # print(contents_dict)

    results = []
    print(f"Getting results for query: {query}")
    # print(f"Content: {content}")
    section_results = content.split()
    for item in section_results:
        try:
            if item.endswith("."):
                print(f"stripped period from {item}")
                item = item[:-1]
            result = contents_dict[item]
            # print(result)
            results.append(result)
        except KeyError:
            print(f"{item} not in contents_dict")
    
    return results
    

def test_batch_section_picking():
    id = "02078_01"
    act_name = "Act Name"

    html_content = get_html_document(id)
    html_soup = BeautifulSoup(html_content)

    contents_list = get_contents_list(html_soup)
    pprint(contents_list)

    random.shuffle(contents_list)

    batches = split_into_batches(contents_list, int(len(contents_list)/8))

    query = "What are tenants rights?"

    results = []
    
    for batch in batches:
        content = get_best_sections(act_name, batch, query, limit=20)
        print(f"Content: {content}")
        results.append(content)
     
    # pprint(results)
    
    flattened_results = [item for sublist in results for item in sublist]
    print(f"Flattened: {flattened_results}")
    random.shuffle(flattened_results)

    summary_content = get_best_sections(act_name, flattened_results, query, limit=40)

    print(f"Summary: {summary_content}")




# ------ STATUTE GETTING AND FORMATTING ------ #


def get_contents_list(html_soup):
    """Returns list of strings representing table of contents items. 
    Parts start with "Part", divisions with "Division", else a section with number separated by space from heading. 
    Note number can include range of spent provisions.
    """
    content_div = html_soup.find("div", id="contents")
    table = content_div.find("table")
    # print(table)

    contents_list = []
    for row in table.children:
        string = ""
        for column in row.children:
            string += column.text
            string += " "
        contents_list.append(string.strip())

    return contents_list



def get_sections_list(contents_list):
    sections_list = []
    n_removed = 0
    for item in contents_list:
        first = item.split()[0]
        # print(first)
        to_remove = ["contents", "part", "division"]
        if first.lower().strip() in to_remove:
            # print(f"Removed {first}")
            n_removed += 1
            continue
        if "-" in first:
            # print(f"Removed {first}")
            n_removed += 1
            continue
        else:
            sections_list.append(item)
    print(f"get_sections_list removed {n_removed} items")
    return sections_list



# TODO TODO 
def get_data_from_contents_item(item: str):
    first = item.split()[0]

    type = None
    
    if first.lower == "part":
        type = "part"
        num = item.split()[1]
    elif first.lower == "division":
        type = "division"
        num = item.split()[1]
    else:
        type = "section"
        num = first

    return type, num


# ----- BELOW THIS IS NOT USED ABOVE I THINK

def test_get_statute_data():
    id = "02078_01"
    name = "SBC 2002, c 1"

    xml_content = get_xml_document(id)
    xml_soup = BeautifulSoup(xml_content, "xml")
    act_num_id_dicts, act_num_lists = get_act_xml_data(xml_soup)

    html_content = get_html_document(id)
    html_soup = BeautifulSoup(html_content)

    type = "section"
    number = "1"
    item_id = act_num_id_dicts[type][number]
    print(f"Section id: {item_id}")

    
    # SECTION - RETURN RESULT.PARENT FOR HTML
    # result = html_soup.find("p", id=item_id)
    # section_html = result.parent
    # print(section_html)
    
    # PART - RETURN RESULT FOR HTML OF JUST HEADING
    # item_id = act_num_id_dicts["part"]["1"]
    # result = html_soup.find("p", id=item_id)
    # print(result)

    # DIVISION - RETURN RESULT FOR HTML OF JUST HEADING
    # item_id = act_num_id_dicts["division"]["1"]
    # result = html_soup.find("p", id=item_id)
    # print(result)

    contents_list = get_contents_list(html_soup)
    pprint(contents_list)

    split = get_data_from_contents_item(contents_list[5])
    print(split)


def get_act_xml_data(soup):
    parts_dict = get_num_id_dict(soup.act, "part", {})
    print("PARTS")
    pprint(parts_dict)
    print("")

    part_nums_list = get_nums_list(soup.act, "part", [])
    print(part_nums_list)

    divisions_dict = get_num_id_dict(soup.act, "division", {})
    print("DIVISIONS")
    pprint(divisions_dict)
    print("")

    division_nums_list = get_nums_list(soup.act, "division", [])
    print(division_nums_list)
    
    sections_dict = get_num_id_dict(soup.act, "section", {})
    print("SECTIONS")
    pprint(sections_dict)
    print("")

    section_nums_list = get_nums_list(soup.act, "section", [])
    print(section_nums_list)

    act_num_id_dicts = {
        "part": parts_dict,
        "division": divisions_dict,
        "section": sections_dict,
    }

    act_num_lists = {
        "part": part_nums_list,
        "division": division_nums_list,
        "section": section_nums_list,
    }

    return act_num_id_dicts, act_num_lists


def get_nums_list(tag, name, nums_list):
    if tag.name == name:
        num = get_num(tag)

        if num:
            nums_list.append(num)

    for child in tag.children:
        if isinstance(child, NavigableString):
            continue

        get_nums_list(child, name, nums_list)

    return nums_list

    
# Could alter name to get lower sections, go along list
def get_num_id_dict(tag, name, num_id_dict):
    if tag.name == name:
        id = tag.get("id")
        num = get_num(tag)

        if id is not None and num is not None:
            num_id_dict[num] = id

    for child in tag.children:
        if isinstance(child, NavigableString):
            continue

        get_num_id_dict(child, name, num_id_dict)

    return num_id_dict

# Exists in other
def get_num(tag):
    for child in tag.children:
            if isinstance(child, NavigableString):
                continue

            if child.name == "num":
                num = child.string
                break
    return num


# Exists in other
def get_xml_document(id):
    url = f"http://www.bclaws.ca/civix/document/id/complete/statreg/{id}/xml"
    response = requests.get(url)
    return response.content

# Exists in other
def get_html_document(id):
    url = f"http://www.bclaws.ca/civix/document/id/complete/statreg/{id}"
    response = requests.get(url)
    return response.content


def split_into_batches(lst, batch_size):
    return [lst[i:i+batch_size] for i in range(0, len(lst), batch_size)]



if __name__ == "__main__":
    main()