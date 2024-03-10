from typing import List, Optional
# Very CLUNKY and needs to be fixed so can be run from anywhere
try:
    from civix.data import load_statute_dictionary
except Exception:
    from data import load_statute_dictionary


def get_statute_dict_by_info(info: str, exclude_repealed: bool=False) -> Optional[dict]:
    """
    Retrieves a statute dictionary from a list of statute dictionaries by searching for a match in the 'name', 'citation', 
    or 'act_id' fields. The match is case-insensitive. If exclude_repealed is True, only statutes that have not been repealed will be returned.

    Parameters:
    info (str): The information (name, citation, or act_id) to be matched.
    exclude_repealed (bool): Whether to exclude repealed statutes. Default is False.

    Returns:
    dict: A dictionary containing the matched statute's information.
          If no matching statute is found, returns None.
    """
    data = load_statute_dictionary()
    statute = get_dictionary(data, info, exclude_repealed)
    if statute:
        return statute
    else:
        return None
        

def get_dictionary(data: List[dict], value: str, exclude_repealed: bool=False) -> Optional[dict]:
    """
    Retrieves a dictionary from a list of dictionaries by searching for a case-insensitive match in the 'name', 'citation', 
    or 'act_id' fields. If exclude_repealed is True, only dictionaries that have not been repealed will be returned.

    Parameters:
    data (List[dict]): The list of dictionaries to search.
    value (str): The value to be matched.
    exclude_repealed (bool): Whether to exclude repealed dictionaries. Default is False.

    Returns:
    dict: A dictionary containing the matched information.
          If no match is found, returns None.
    """
    lower_case_value = value.lower()
    for item in data:
        try:
            if item['name'].lower() == lower_case_value or item['citation'].lower() == lower_case_value or item['act_id'].lower() == lower_case_value:
                if exclude_repealed and item['repealed']:
                    continue
                print(item)
                return item
        except AttributeError as e:
            print(f"{e}\nFor item: {item}")
            continue
    return None
    

if __name__ == "__main__":
    # Example usage:
    # Retrieves and prints the dictionary that matches the name 'Water Act'
    get_statute_dict_by_info("Water Act", True)
