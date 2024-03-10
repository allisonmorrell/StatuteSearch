import os
import json
import re

import pandas as pd

# ================= TODO ===================== #

# can get rules of court index, by replacing statreg with roc - contains rules of court and related statutes. But then still access them through document statreg index

# ================= END TODO ================= #


def load_statute_dataframe(include_repealed = False, exclude_directory_id = True, exclude_act_id = True, exclude_url = False):
    """
    Loads statutes as dataframe for display, default to not including repealed statutes, ids
    """

    statute_dictionary = load_statute_dictionary()

    # TODO better error handline here
    if not statute_dictionary:
        return None

    df = pd.DataFrame(statute_dictionary)

    if not include_repealed:
        df = df.loc[df['repealed'] == False]
        df = df.drop(['repealed'], axis=1)

    if exclude_directory_id:
        df = df.drop("directory_id", axis=1)

    if exclude_act_id:
        df = df.drop("act_id", axis=1)

    if exclude_url:
        df = df.drop("url", axis=1)

    return df


def load_statute_dictionary():
    """
    Loads the most recent all_statutes json file from data, returns dictionary
    """

    statute_filepath = get_statute_json_filepath()
    
    with open(statute_filepath, "r") as f:
        dictionary = json.load(f)

    return dictionary


def get_statute_currency_date():
    """
    Returns the date on which the most recent all_statutes json file was created. 
    """
    filepath = get_statute_json_filepath()

    pattern = r"all_statutes_([0-9]{8})"
    match = re.search(pattern, filepath)
    if match:
        date_str = match.group(1)
        year = date_str[:4]
        month = date_str[4:6]
        day = date_str[6:8]
        return f"{year}-{month}-{day}"
    else:
        return None



def get_statute_json_filepath():
    """
    Returns the filepath of the most recent all_statutes json file
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, 'data')
    
    json_files = [filename for filename in os.listdir(data_dir) if filename.endswith('.json') and 'all_statutes' in filename]
    json_files.sort()
    
    if json_files:
        most_recent_file = json_files[-1]
        statute_filepath = os.path.join(data_dir, most_recent_file)
        return statute_filepath



    else:
        return None