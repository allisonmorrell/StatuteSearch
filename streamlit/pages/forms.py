# TODO - EVERYTHING!! Clumsy implementations below all around. 
# improvements include: 
#     - just getting the appendices with the forms
#     - caching the forms info
#     - saving various stuff
#     - modularizing code relating to retrieving forms



from bs4 import BeautifulSoup
import streamlit as st
import streamlit.components.v1 as components
import requests
import re

def get_forms(soup):
    """
    Takes in soup object derived from XML of document containing forms
    Returns a dictionary where key is name concatenated with form header
    and value is id of form
    """
    # Find all form titles in the soup object
    form_title_tags = soup.find_all("bcl:formtitle")
    forms_dict = {}

    # Iterate over each form title and extract the form header and form ID
    for title_tag in form_title_tags:
        form_id = title_tag.parent["id"]
        header = get_form_header_by_id(soup, form_id)  # Get the header for the current form
        
        # Iterate over each child of the form title and extract the name
        for name_tag in title_tag.contents:
            if name_tag.string is not None:
                name = str(name_tag.string)
                
                # Concatenate the name with the header, title-cased to form the key for the dictionary
                key = f"{name} - {str(header).title()}"
                
                # Add the key-value pair to the dictionary
                forms_dict[key] = form_id

    return forms_dict


def get_form_by_id(soup, form_id):
    """
    Takes as input soup which contains forms, and id of form
    Returns string of xml content of that form
    """
    # Find the form tag with the specified ID in the soup object and return its XML content as a string
    form_tag = soup.find("bcl:form", {"id": form_id})
    return str(form_tag)


def get_form_header_by_id(soup, form_id):
    # Get the XML content of the form with the specified ID
    form = get_form_by_id(soup, form_id)
    
    # Parse the XML content into a BeautifulSoup object and find the first occurrence of the "strong" tag
    form_soup = BeautifulSoup(form, "xml")
    header_object = form_soup.find("strong", recursive=True)
    
    # Return the text of the "strong" tag if it exists, or None if it doesn't
    return header_object.get_text() if header_object else None


def get_xml_document(document_id, index_id="statreg"):
    url = f"http://www.bclaws.ca/civix/document/id/complete/{index_id}/{document_id}/xml"
    response = requests.get(url)
    return response.content


def parse_element(element):
    if element is None or not element.name:
        return {}

    tag_map = {
        "form": ("div", "form"),
        "formtitle": ("h1", ""),
        "a": ("a", ""),
        "em": ("em", ""),
        "strong": ("strong", ""),
        "righttext": ("div", "righttext"),
        "centertext": ("div", "centertext"),
        "lefttext": ("div", "lefttext"),
        "indent1": ("div", "indent1"),
        "indent2": ("div", "indent2"),
        "table": ("table", ""),
        "colgroup": ("colgroup", ""),
        "colspec": ("col", ""),
        "tbody": ("tbody", ""),
        "trow": ("tr", ""),
        "entry": ("td", ""),
    }


    css = {
        "righttext": "text-align: right;",
        "centertext": "text-align: center;",
        "lefttext": "text-align: left;",
        "indent1": "margin-left: 2em;",
        "indent2": "margin-left: 4em;",
    }

    if element.name in tag_map:
        new_tag, class_name = tag_map[element.name]
        element.name = new_tag
        if class_name:
            element["class"] = class_name

    for child in element.children:
        if child.name:
            css.update(parse_element(child))

    return css



def get_rule_xml(document_id, rule, index_id="statreg"):
    """
    Using xpath, find the rule given a string in format 1-1
    TODO change to use document ID? need to add function for get URL by ID? or just pass in statreg? 
    """
    url = f"http://www.bclaws.ca/civix/document/id/complete/{index_id}/{document_id}/xml/xpath///bcl:rule[bcl:num='{rule}']"
    print(url)
    response = requests.get(url)
    print(response)
    return response.content


def get_rule_html(document_id, rule, index_id="statreg"):
    """
    Using xpath, find the rule given a string in format 1-1
    TODO change to use document ID? need to add function for get URL by ID? or just pass in statreg? 
    """
    url = f"http://www.bclaws.ca/civix/document/id/complete/{index_id}/{document_id}/xpath///bcl:rule[bcl:num='{rule}']"
    print(url)
    response = requests.get(url)
    content = response.content
    if content:
        soup = BeautifulSoup(content)
        html_content = soup.prettify()
        return html_content
    else:
        return None



form_sources = {
    "bcsc_civil": "168_2009_04",
    "bcsc_probate": "168_2009_04_1",
    "bcsc_family": "169_2009_04",
    "fla_regulation": "347_2012",
    "patients_property": "311_76"
}

form_sources_rules = {
    "168_2009_04": "168_2009_00_multi",
    "168_2009_04_1": "168_2009_00_multi",
    "169_2009_04": "169_2009_00_multi",
    "347_2012": "347_2012",
    "311_76": "311_76"
}


# CHECK if this works with dictionary
selected_source = st.selectbox("Select source", form_sources)


if selected_source:
    source_id = form_sources[selected_source]
    st.write(source_id)
    source_xml = get_xml_document(source_id)
    source_soup = BeautifulSoup(source_xml, "xml")

    # Extract the forms from the soup object and save them as a dictionary
    forms = get_forms(source_soup)

    # Extract the keys of the dictionary and save them as a list
    forms_list = list(forms.keys())

    form = st.selectbox("Select form", forms_list)

    get_form = st.button("Get form")

    if get_form:
        form_id = forms[form]
        header = get_form_header_by_id(source_soup, form_id)
        selected_form_xml = get_form_by_id(source_soup, form_id)

        form_soup = BeautifulSoup(selected_form_xml, "xml")

        root = form_soup.find("form")

        css = parse_element(root)

        html_with_css = "<style>{}</style>{}".format("\n".join([".{}{{{}}}".format(k, v) for k, v in css.items()]), str(root))
            
        components.html(html_with_css)

      
        document_id = form_sources_rules[source_id]


        match = re.search(r"Rule\s*(\d+-\d+)", form)
        rule = match.group(1)

        content = get_rule_html(document_id, rule)

        if content:
            components.html(content)
        else:
            print("nothing found")