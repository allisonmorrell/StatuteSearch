import streamlit as st
import streamlit.components.v1 as components


from civix.data import load_statute_dataframe, get_statute_currency_date

from civix.document import Document

from civix.retrieve_statute import get_statute_dict_by_info

st.title("Get Document")

st.write("Enter the full name, citation, or act_id of a statute to retrieve full information.")
document_info = st.text_input("")

if document_info:
    statute_dict = get_statute_dict_by_info(document_info)
    if statute_dict:
        st.write(statute_dict)
        document_id = statute_dict["act_id"]
        statute = Document(document_id)
    
        definition = st.text_input("Definition")
        if definition:
            components.html(statute.get_definition_xpath(definition))
    
        show_definitions = st.checkbox("Show definitions")
        if show_definitions:
            st.write(statute.get_all_definitions())
        
        show_html = st.checkbox("Show HTML")
        if show_html:
            components.html(statute.html)
    
        show_data = st.checkbox("Show data")
        if show_data:
            st.write(statute.dictionary)


st.title("Statute Filter")

include_repealed = st.checkbox("Include repealed")

currency_date = get_statute_currency_date()
st.write(f"Statutes retrieved: {currency_date}")
df = load_statute_dataframe(include_repealed=include_repealed, exclude_act_id = False)


name_filter = st.text_input('Filter by name', '')
citation_filter = st.text_input("Filter by citation", "")

if name_filter:
    filtered_df = df.loc[df['name'].str.contains(name_filter, case=False)]
else:
    filtered_df = df

if citation_filter:
    filtered_df = df.loc[df["citation"].str.contains(citation_filter, case=False)]


st.dataframe(filtered_df)
    


