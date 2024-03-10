import requests
from bs4 import BeautifulSoup

from civix.utils import fetch_and_parse_xml_data


def extract_document_info(directory_url, exclude_repealed = True):
    """
    Extracts document information from XML data and returns a dictionary where the keys
    are the document titles (with "(Repealed)" appended if applicable) and the values
    are tuples containing the corresponding document IDs and a boolean indicating if the
    document is repealed.
    Args:
        directory_url (str): The URL of the directory containing XML data with document information.
        exclude_repealed (bool): If True, documents with a status of "Repealed" will be excluded
                                 from the output. Defaults to True.
    Returns:
        Dict[str, Tuple[str, bool]]: A dictionary mapping document titles to tuples containing
                                      document IDs and a boolean indicating if the document is repealed.
    """
    # Extract document information from XML data, create the output dictionary.
    response = requests.get(directory_url)
    xml_data = response.content

    soup = BeautifulSoup(xml_data, "xml")
    document_info = {}
    for dir_tag in soup.find_all("dir"):
        status_tag = dir_tag.find("CIVIX_DOCUMENT_STATUS")
        if exclude_repealed and status_tag and status_tag.text == "Repealed":
            continue
        title = dir_tag.find("CIVIX_DOCUMENT_TITLE").text
        doc_id = dir_tag.find("CIVIX_DOCUMENT_ID").text
        repealed = status_tag and status_tag.text == "Repealed" if status_tag else False
        document_info[title] = (doc_id, repealed)
    return document_info


def get_act_id(document_id):
    """
    Takes a document ID as input.
    Returns the act ID corresponding to the input document ID.
    """
    # Get the act ID corresponding to the input document ID.
    directory_url = f"https://www.bclaws.gov.bc.ca/civix/content/complete/statreg/{document_id}"
    soup = fetch_and_parse_xml_data(directory_url)

    act_dir_element = soup.find(lambda tag: tag.name == 'dir' and tag.find('CIVIX_DOCUMENT_TITLE', string='Act'))
    if act_dir_element is not None:
        act_document_id = get_civix_document_id(act_dir_element)

        if act_document_id is not None:
            act_directory_url = f"{directory_url}/{act_document_id}"
            act_soup = fetch_and_parse_xml_data(act_directory_url)
            first_act_document = act_soup.find('document')
            act_id = get_civix_document_id(first_act_document)
            # for one instance, this returned none, so added this
            if not act_id:
                return f"{document_id}"
            return f"{act_id}_multi"
    else:
        first_document = soup.find('document')
        return get_civix_document_id(first_document)


def get_civix_document_id(element):
    """
    Takes a BeautifulSoup element as input.
    Returns the CIVIX_DOCUMENT_ID of the element as a string, or None if not found.
    """
    # Extract the CIVIX_DOCUMENT_ID from the input element.
    if element is not None:
        return element.find('CIVIX_DOCUMENT_ID').text.strip()
    return None


def get_directory_by_letter(letter):
    print("running get_directory_by_letter")
    if not len(letter) == 1 or not letter.isalpha():
        raise ValueError("Input must be a single alphabetic character")

    letter = letter.upper()
    directory_url = "https://www.bclaws.gov.bc.ca/civix/content/complete/statreg/"

    soup = fetch_and_parse_xml_data(directory_url)

    # Define a function to filter elements based on the content of CIVIX_DOCUMENT_TITLE
    def filter_by_title(element):
        if element.name == 'dir':
            title_element = element.find('CIVIX_DOCUMENT_TITLE')
            if title_element and title_element.text == f'-- {letter} --':
                return True
        return False

    # Find the <dir> element where the <CIVIX_DOCUMENT_TITLE> matches the input letter
    matching_dir = soup.find(filter_by_title)

    if matching_dir is not None:
        # Get the document ID from the matching <dir> element
        document_id = matching_dir.find('CIVIX_DOCUMENT_ID').text

        # Construct the URL using the extracted document ID
        url = f"http://www.bclaws.gov.bc.ca/civix/content/complete/statreg/{document_id}/"
        return url
    else:
        return None