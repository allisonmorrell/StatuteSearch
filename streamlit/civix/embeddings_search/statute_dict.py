import re
import requests
from bs4 import BeautifulSoup, Tag
from typing import Dict, List, Tuple
from markdownify import markdownify as md

class Section:
    """Class to represent a section of the statute."""
    def __init__(self, number: str, html: str):
        self.number = number
        self.html = html
        self.part = None
        self.division = None

class Part:
    """Class to represent a part of the statute."""
    def __init__(self, title: str):
        self.title = title
        self.sections = []
        self.divisions = []

class Division:
    """Class to represent a division of a part of the statute."""
    def __init__(self, title: str):
        self.title = title
        self.sections = []

def parse_statute(contentsscroll: Tag) -> Tuple[Dict[str, Section], List[Part], str, str, str]:
    """
    Parse the HTML and create a hierarchical structure.
    
    Parameters:
    contentsscroll (Tag): The contentsscroll div from the parsed HTML.
    
    Returns:
    Tuple[Dict[str, Section], List[Part], str, str, str]: A tuple containing a dictionary of sections, 
    a list of parts, the title of the statute, the citation, and the neutral citation.
    """
    # Get the title and citation
    title_div = contentsscroll.find(id='title')
    title = title_div.find('h2').get_text(strip=True)
    citation = ' '.join(title_div.find('h3').get_text(strip=True).split())

    # Generate the neutral citation
    neutral_citation = re.sub(r'\[(.*)\] CHAPTER', r'\1, c', citation)

    # Create a dictionary to store the sections and lists to store the current part and division
    section_dict = {}
    parts = []
    current_part = Part("Default Part")  # Create a default Part object
    current_division = None

    # Parse the HTML and create the hierarchical structure
    for element in contentsscroll.children:
        if element.name == 'div' and element.get('class') == ['section']:
            # This is a section, so create a new Section object
            section_number = element.find('a').get('name').replace('section', '')
            section = Section(section_number, str(element))
            section.part = current_part

            # Add the section to the current part and division (if any), and to the section dictionary
            if current_division:
                current_division.sections.append(section)
                section.division = current_division
            else:
                current_part.sections.append(section)
            section_dict[section_number] = section
        elif element.name == 'p' and element.get('class') == ['part']:
            # This is a part, so create a new Part object and add it to the list of parts
            current_part = Part(element.get_text(strip=True))
            parts.append(current_part)
            # A new part means no current division
            current_division = None
        elif element.name == 'p' and element.get('class') == ['division']:
            # This is a division, so create a new Division object and add it to the current part
            current_division = Division(element.get_text(strip=True))
            current_part.divisions.append(current_division)

    # If there are no parts, add the default part to the list of parts
    if not parts:
        parts.append(current_part)
    
    return section_dict, parts, title, citation, neutral_citation

def create_statute_dict(section_dict: Dict[str, Section], parts: List[Part], title: str, citation: str, neutral_citation: str):
    """
    Create a dictionary to store all the information about the statute.
    
    Parameters:
    section_dict (Dict[str, Section]): A dictionary of Section objects.
    parts (List[Part]): A list of Part objects.
    title (str): The title of the statute.
    citation (str): The citation of the statute.
    neutral_citation (str): The neutral citation of the statute.
    
    Returns:
    Dict[str, Union[str, Dict[str, Union[str, List[Union[str, Dict[str, Union[str, List[str]]]]]]]]: 
    A dictionary with all the information about the statute.
    """
    if len(parts) == 1 and parts[0].title == "Default Part":
        # If there's only the default part, just include the sections
        statute_dict = {
            'title': title,
            'citation': citation,
            'neutral_citation': neutral_citation,
            'sections': {section_number: section.html for section_number, section in section_dict.items()},
        }
    else:
        # Otherwise, include the parts and divisions as well
        statute_dict = {
            'title': title,
            'citation': citation,
            'neutral_citation': neutral_citation,
            'sections': {section_number: section.html for section_number, section in section_dict.items()},
            'parts': [{
                'part_number': part.title.split(' — ')[0],
                'part_title': part.title.split(' — ')[1],
                'sections': [section.number for section in part.sections],
                    # If division is repealed, doesn't include split
                    'divisions': [{
                    'division_number': division.title.split(' — ')[0],
                    # Safely handle division title split
                    'division_title': division.title.split(' — ')[1] if ' — ' in division.title else division.title,
                    'sections': [section.number for section in division.sections]
                } for division in part.divisions]
            } for part in parts]
        }
    return statute_dict

def get_html_from_url(url: str) -> str:
    """
    Retrieve the HTML content from a URL. This function needs to be implemented using requests 
    or a similar library in your own environment.
    
    Parameters:
    url (str): The URL to retrieve the HTML from.
    
    Returns:
    str: The HTML content of the URL.
    """
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception if the GET request was not successful
    return response.text

def process_statute(soup: BeautifulSoup):
    """
    Process a statute from a BeautifulSoup object.
    
    Parameters:
    soup (BeautifulSoup): The BeautifulSoup object containing the HTML of the statute.

    Returns:
    Dict[str, Union[str, Dict[str, Union[str, List[Union[str, Dict[str, Union[str, List[str]]]]]]]]: 
    A dictionary with all the information about the statute.
    """
    # Find the div with id='contentsscroll'
    contentsscroll = soup.find(id='contentsscroll')

    # Parse the HTML and create the hierarchical structure
    section_dict, parts, title, citation, neutral_citation = parse_statute(contentsscroll)

    # Create a dictionary to store all the information about the statute
    statute_dict = create_statute_dict(section_dict, parts, title, citation, neutral_citation)

    return statute_dict


def get_statute_dict_by_id(id):
    url = f"http://www.bclaws.ca/civix/document/id/complete/statreg/{id}"
    soup = BeautifulSoup(html, 'html.parser')
    statute_dict = process_statute(soup)
    return statute_dict
    

def get_statute_dict_from_url(url):
    html = get_html_from_url(url)
    soup = BeautifulSoup(html, 'html.parser')
    statute_dict = process_statute(soup)
    return statute_dict
    

def create_section_markdown(section_html: str) -> str:
    """
    Converts a section's HTML to Markdown, removing line breaks within paragraph tags, 
    making all links absolute, and adding Markdown formatting for bold text.
    
    Parameters:
    section_html (str): The HTML of the section.

    Returns:
    str: The section in Markdown format.
    """
    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(section_html, 'html.parser')
    
    # Prepend the base URL to the href attribute of all a tags
    base_url = 'https://www.bclaws.gov.bc.ca'
    for a in soup.find_all('a', href=True):
        a['href'] = base_url + a['href']

    # Wrap the text within all span tags with class "normal-bold-style" with **
    for span in soup.find_all('span', class_='normal-bold-style'):
        new_tag = soup.new_tag('b')
        new_tag.string = span.get_text()
        span.replace_with(new_tag)


    # Convert the modified HTML back to a string
    section_html = str(soup)
    
    # Remove line breaks within paragraph tags using a regular expression
    no_breaks_html = re.sub(r'(<p[^>]*>)(.*?)(</p>)',
                            lambda match: match.group(1) + match.group(2).replace('\n', ' ') + match.group(3),
                            section_html,
                            flags=re.DOTALL)
    
    # Convert the modified HTML to Markdown
    markdown = md(no_breaks_html, width=float('inf'))
    
    return markdown



def create_title_markdown(statute_dict):
    title_md = f'# {statute_dict["title"]}, {statute_dict["neutral_citation"]}\n\n'
    return title_md


def create_statute_markdown(statute_dict):
    statute_md = create_title_markdown(statute_dict)
    
    if "parts" in statute_dict:
        for part in statute_dict["parts"]:
            statute_md += f'## {part["part_number"]} {part["part_title"]}\n\n'
            if part["divisions"]:
                for division in part["divisions"]:
                    statute_md += f'### {division["division_number"]} {division["division_title"]}\n\n'
                    for section_number in division["sections"]:
                        statute_md += f'{create_section_markdown(statute_dict["sections"][section_number])}\n\n'
            else:
                for section_number in part["sections"]:
                    statute_md += f'{create_section_markdown(statute_dict["sections"][section_number])}\n\n'
    else:
        for section_number, section_content in statute_dict["sections"].items():
            statute_md += f'{create_section_markdown(section_content)}\n\n'
            
    return statute_md


def test_get_and_markdown():
    statute_dict = get_statute_dict_from_url("https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/96253_01")
    print(statute_dict)
    statute_md = create_statute_markdown(statute_dict)
    print(statute_md)
    
    section_number = "1"
    
    section_html = statute_dict["sections"][section_number]
    
    section_md = create_section_markdown(section_html)
    
    print(section_md)