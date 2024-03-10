import requests
import xmltodict
import re

# TODO
# add external reference section ID
# fix parsing of external/internal references if possible (section 1 of...)


class Document:

    def __init__(self, document_id):
        self.document_id = document_id
        xml_content = self.get_xml_document()
        self.dictionary = xmltodict.parse(xml_content)
        self.html = self.get_html_document()
        self.definitions_list = self.extract_all_definitions()

    
    def get_html_document(self, index_id="statreg"):
        url = f"http://www.bclaws.ca/civix/document/id/complete/{index_id}/{self.document_id}"
        response = requests.get(url)
        return response.content

    
    def get_xml_document(self):
        url = f"http://www.bclaws.ca/civix/document/id/complete/statreg/{self.document_id}/xml"
        response = requests.get(url)
        return response.content

    
    def get_definition_xpath(self, term, index_id="statreg", xml = False):
        """
        Get definition of term, note that default type argument is html but xml is also available
        """
        # TODO implement XML handling amd rest
        url = f"http://www.bclaws.ca/civix/document/id/complete/statreg/{self.document_id}/xpath///bcl:definition[bcl:text/in:term='{term}']"
        # NOTE that can use //bcl:definition[bcl:text/in:term='{term}']/ancestor::*[1] to get immediate parent
        response = requests.get(url)
        return response.content

    # TODO address issue where external reference isn't saved into definition list    
    def extract_all_definitions(self):
        # Initialize an empty list to store the definitions
        definitions_list = []
        
        # Extract the content of the document
        content = self.dictionary.get("act:act", {}).get("act:content", {})
        
        # Check if the content is a list of items
        if isinstance(content, list):
            # Iterate over each item and extract the sections
            for item in content:
                # Check if the item contains "bcl:part"
                if "bcl:part" in item:
                    parts = item.get("bcl:part", {})
                    # Check if "bcl:part" is a list of parts
                    if isinstance(parts, list):
                        for part in parts:
                            sections = part.get("bcl:section", [])
                            definitions_list += self.extract_definitions_from_sections(sections)
                    else:  # "bcl:part" is a single dictionary
                        sections = parts.get("bcl:section", [])
                        definitions_list += self.extract_definitions_from_sections(sections)
                else:
                    # Item does not contain "bcl:part", so extract sections directly
                    sections = item.get("bcl:section", [])
                    definitions_list += self.extract_definitions_from_sections(sections)
        elif isinstance(content, dict):
            # If the content is a dictionary, directly extract the sections
            sections = content.get("bcl:section", [])
            definitions_list = self.extract_definitions_from_sections(sections)
        
        return definitions_list

    
    def extract_definitions_from_sections(self, sections):
        # Helper function to extract definitions from a list of sections
        definitions_list = []
        if isinstance(sections, dict):
            sections = [sections]  # Ensure sections is a list for consistent processing
        for section in sections:
            # Extract the section number
            section_num = section.get("bcl:num", "")
            # Extract the definitions within the section
            definitions = section.get("bcl:definition", [])
            if isinstance(definitions, dict):
                definitions = [definitions]  # Ensure definitions is a list for consistent processing
            # Iterate through the definitions
            for definition in definitions:
                # Extract the definition ID
                definition_id = definition.get("@id", "")
                # Extract the term and text from the definition
                definition_text = definition.get("bcl:text", {})
                if isinstance(definition_text, dict):
                    term = definition_text.get("in:term", "")
                    text = definition_text.get("#text", "")
                    # Append the extracted information to the definitions_list
                    definitions_list.append({
                        "section": section_num,
                        "term": term,
                        "text": text.strip(),  # Remove leading/trailing whitespaces
                        "id": definition_id
                    })
        return definitions_list

    
    def get_definition(self, term, index_id="statreg", xml=False):
        # Use the extracted definitions_list to find and return the definition of the given term
        # instead of making an HTTP request.
        for definition in self.definitions_list:
            if definition['term'] == term:
                return definition
        return None  # Return None if the term is not found

    
    def get_all_definitions(self):
        # Return the entire list of definitions
        return self.definitions_list

    
    def get_definitions_by_section(self, section_num):
        # Return definitions from a specific section number
        return [definition for definition in self.definitions_list if definition['section'] == section_num]
