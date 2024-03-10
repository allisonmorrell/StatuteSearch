
import string
import re
import json
from datetime import datetime
import requests
import pandas as pd

import streamlit as st
from bs4 import BeautifulSoup

from civix.content import get_directory_by_letter, extract_document_info, get_act_id
from civix.data import get_statute_currency_date


# ----------------------- TODO --------------------------- #


# Move get all statutes to its own file, not on this page so it can be called from elsewhere if necessary. 


# ----------------------- END TODO ------------------------ #
# OLD FROM WHEN THIS WAS STREAMLIT PAGE
def main():

    st.title("Get All Statutes")

    st.write(
        """
        This page controls the 'get_all_statutes' function, which collects information necessary to retrieve statutes and saves it to the civix/data folder in json and csv format. 
        
        This function loops through each statreg directory, and collects data concerning the statute name, citation, directory id and id of the full act text. This function takes a few minutes to run, as it makes around 1000 calls to the CIVIX API. 
        
        The statute data is not expected to change frequently, and so this function need not be run except where new statutes are added or statutes are repealed.
        """)
    
    currency_date = get_statute_currency_date()
    st.write(f"Date retrieved: {currency_date}")
    
    if st.button("Get all statutes"):
        all_statutes = get_all_statutes()
        st.write(all_statutes)
        


def get_all_statutes():
    """
    Iterates through every letter, calls get_directory_by_letter for each letter, extracts the document
    information using extract_document_info, and processes the extracted data using process_document_info.
    Returns a list of dictionaries with the following format:
                                           [{"name": ..., "citation": ..., "directory_id": ..., "act_id": ..., "repealed": ..., "url": ...}]
    """

    all_statutes = []

    for letter in string.ascii_uppercase:
        print(letter)
        directory_url = get_directory_by_letter(letter)
        if directory_url is not None:
            document_info = extract_document_info(directory_url, exclude_repealed=False)
            processed_info = process_document_info(document_info)
            all_statutes.extend(processed_info)
        else:
            print(None)
    save_all_statutes(all_statutes)
    return all_statutes


def save_all_statutes(all_statutes):
    # Get the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Get the number of records
    num_records = len(all_statutes)

    # Create the filename
    json_filename = f"civix/data/all_statutes_{timestamp}_{num_records}records.json"

    # Dump the all_statutes list of dictionaries to a json file
    with open(json_filename, 'w') as f:
        json.dump(all_statutes, f)

    
    # Convert to dataframe and save to CSV
    csv_filename = f"civix/data/all_statutes_{timestamp}_{num_records}records.csv"
    df = pd.DataFrame(all_statutes)
    df.to_csv(csv_filename, index=False)
    
    print(f"Data saved to {json_filename}, {csv_filename}")

# NOTE and TODO added skipping of None items with code
# Hasn't been tested
# Reason that items with no Act ID (one instance, which had regs) are of no use for the purposes I'm using this for
def process_document_info(document_info):
    """
    Processes the document information dictionary and returns a list of dictionaries with the desired format.
    Args:
         A dictionary mapping document titles to tuples containing document IDs and repealed status.
    Returns:
        A list of dictionaries with the following format:
                                           [{"name": ..., "citation": ..., "directory_id": ..., "act_id": ..., "repealed": ..., "url": ...}]
    """
    # Process document_info dictionary and create the output list of dictionaries.
    output = []
    for title, (doc_id, repealed) in document_info.items():
        
        name, citation = extract_name_and_citation(title)
        print(name, end=", ")
        act_document_id = get_act_id(doc_id)
        # Skip this item if the act_document_id is None
        if act_document_id is None:
            continue
        output.append({"name": name, "citation": citation, "directory_id": doc_id, "act_id": act_document_id, "repealed": repealed, "url": f"http://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/{act_document_id}"})
    print()
    return output



def extract_name_and_citation(title):
    match = re.match(r'(.*?)\s*\[([\w\s]+)\]\s*(.*)', title)
    if match:
        name = match.group(1).strip()
        # Add a comma after the year and replace "c." with "c"
        citation = f"{match.group(2)}, {match.group(3).replace('.', '')}"
        return name, citation
    return title, ""


if __name__ == "__main__":
    main()

