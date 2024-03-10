import requests

from bs4 import BeautifulSoup


def fetch_and_parse_xml_data(url: str) -> BeautifulSoup:
    """
    Fetches the XML data from the given URL and parses it using BeautifulSoup.
    Args:
        url (str): The URL to fetch the XML data from.
    Returns:
        BeautifulSoup: A BeautifulSoup object representing the parsed XML data.
    """
    # Fetch and parse XML data from the URL.
    response = requests.get(url)
    xml_data = response.content
    return BeautifulSoup(xml_data, 'xml')