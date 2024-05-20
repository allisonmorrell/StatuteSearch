import re

import random

import chainlit as cl

from choose_law import choose_bc_statute, choose_multiple_bc_statutes

from get_option_for_query import get_multiple_options_for_query_from_list

from streamlit.civix.data import load_statute_dataframe
from streamlit.civix.embeddings_search.search import get_law_names_by_relatedness
from streamlit.civix.embeddings_search.statute_dict import get_statute_dict_from_url, create_statute_markdown, create_section_markdown
from streamlit.civix.embeddings_search.new_search import TextRanker

from question_answering.openai_api import get_content_from_response

from question_answering.conversation import Conversation

from question_answering.chat_completion import chat_completion_request

# --------------
# TODO TODO TODO
# - BUG doesn't work with statutes that have divisions? Or some other issue. list index out of range (e.g. strata property act, residential property act). Something to do with markdown rendering possibly?
# - BUG chat times out
# - fix ordering of items in retrieval so it not alphabetical
# - add recommended questions to "what question" dialogue
# - implement streaming in chat


# ------------ SETTINGS------------ #
# Parameters for retrieving statutes
NUMBER_OPTIONS_TO_RETRIEVE = 10
NUMBER_OPTIONS_TO_SHOW = 5


@cl.on_chat_start
async def start():
    await cl.Message(
        content=
        "Input a query about British Columbia law. Then, the system will get a list of statutes which could help with your query and give you a choice of which to search first."
    ).send()


@cl.on_message
async def on_message(message):
    if not cl.user_session.get("query"):
        cl.user_session.set("query", message)

    query = cl.user_session.get("query")

    if not cl.user_session.get("statute_options"):
        await cl.Message(
            content="Getting statute options, this may take several seconds."
        ).send()
        statute_options = get_statute_options_from_query(query)
        cl.user_session.set("statute_options", statute_options)
    else:
        statute_options = cl.user_session.get("statute_options")

    statute_options_message = get_statute_options_message(statute_options)
    await statute_options_message.send()


@cl.action_callback("load")
async def load_button(action):
    print("running load_button")

    query = await cl.AskUserMessage(content=f"Provide your {action.value}:",
                                    author="Load",
                                    timeout=10000).send()
    print(f"Query: {query}")

    if query:
        if action.value == "name":
            print(f"Running load_statute_by_name on query: {query['content']}")
            await load_statute_by_name(query["content"])
            return
        elif action.value == "citation":
            await cl.Message(content="Lookup by citation not implemented")
            return
        else:
            raise ValueError("load_button action.value invalid")


@cl.action_callback("query_statutes")
async def query_statutes_button(action):
    cl.user_session.set("query", None)
    cl.user_session.set("statute_options", None)

    await cl.Message(content="Enter your search question",
                     author="Query Statutes").send()
    return


def get_statute_options_message(statute_options):
    actions = [
        cl.Action(name="choose_from_options",
                  value="choose_from_options",
                  label="Choose from options"),
        cl.Action(name="recommend_option",
                  value="recommend_option",
                  label="Recommend option"),
        cl.Action(name="change_options",
                  value="rerank_options",
                  label="Rerank options"),
        cl.Action(name="query_statutes",
                  value="search_statutes",
                  label="New search"),
        #cl.Action(name="change_options", value="get_more_options", label="Get more options"),
        # cl.Action(name="load", value="citation", label="Load (citation)"),
        cl.Action(name="load", value="name", label="Load by statute name")
    ]

    statute_list = format_markdown_statute_list(statute_options)

    # TODO make this not display alphabetically
    message = cl.Message(
        content=f"The system retrieved these options:\n{statute_list}",
        actions=actions,
    )

    return message


# ---------- HANDLE STATUTE OPTIONS ------- #


@cl.action_callback("choose_from_options")
async def choose_from_options_button(action):
    options_message = get_options_message()
    await options_message.send()


@cl.action_callback("recommend_option")
async def recommend_from_options_button(action):
    statute_options = cl.user_session.get("statute_options")
    query = cl.user_session.get("query")
    chosen_option = choose_bc_statute(query, statute_options)

    actions = [
        cl.Action(name="statute_choice",
                  value=chosen_option,
                  label="Choose this statute"),
    ]

    await cl.Message(
        content=
        f"The system recommends starting with this option: {chosen_option}.",
        actions=actions).send()


@cl.action_callback("change_options")
async def statute_options_button(action):

    current_options = cl.user_session.get("statute_options")
    query = cl.user_session.get("query")
    change_type = action.value

    new_options = change_options(query, current_options, change_type)
    cl.user_session.set("statute_options", new_options)

    statute_options_message = get_statute_options_message(new_options)
    await statute_options_message.send()



@cl.action_callback("back_to_options")
async def back_to_options_button(action):
    statute_options = cl.user_session.get("statute_options")
    message = get_statute_options_message(statute_options)
    await message.send()


# ---------- Formatting messages ------- #
def get_options_message():
    statute_options = cl.user_session.get("statute_options")

    actions = []
    for index, option in enumerate(statute_options):
        if index < NUMBER_OPTIONS_TO_SHOW:
            actions.append(
                cl.Action(name="statute_choice", value=option, label=option))
        else:
            break

    actions.append(
        cl.Action(name="back_to_options", value="back", label="Back"))

    message = cl.Message(content="Choose from these options:", actions=actions)
    return message


# ---------- AFTER STATUTE IS CHOSEN --------- #


@cl.action_callback("statute_choice")
async def statute_choice_button(action):
    cl.user_session.set("chosen_statute", action.value)
    await load_statute_by_name(action.value)


async def load_statute_by_name(name):
    cl.user_session.set("chosen_statute", name)
    df = load_statute_dataframe()
    citations = get_citations_by_name(name, df)

    try:
        if len(citations) > 1:
            actions = []
            for citation in citations:
                actions.append(
                    cl.Action(name="citation_choice",
                              value=citation,
                              label=citation))
            await cl.Message(
                content=
                "More than one citation exists for this act name, please choose from the citations",
                actions=actions).send()
            return
        else:
            await cl.Message(content=f"You have chosen {name}, {citations[0]}."
                             ).send()
            cl.user_session.set("citation", citations[0])
            await get_and_handle_query()
    # For when no statutes found
    except TypeError:
        await cl.Message(content="Nothing found. Please use the buttons above to try again.")

# TODO suggested questions from query


@cl.action_callback("citation_choice")
async def citation_choice_button(action):
    cl.user_session.set("citation", action.value)
    await get_and_handle_query()


async def get_and_handle_query():
    query = await cl.AskUserMessage(
        content="What question do you have about this statute?",
        timeout=10000,
    ).send()

    if query:
        cl.user_session.set("statute_query", query)
        name = cl.user_session.get("chosen_statute")
        citation = cl.user_session.get("citation")
        section_results = get_query_results(name, citation, query)
        cl.user_session.set(f"section_results", section_results)
        # Add function to add to user session list the list of results in this or equivalent format
        statute_md = section_results["statute_md"]
        statute_sections_string = section_results["statute_sections_string"]
        top_headings_string = section_results["top_headings_string"]

    # Format actions
    actions = [
        #cl.Action(name="section_actions",
        #value="see_more_sections",
        #label="See more sections"),
        # cl.Action(name="section_actions", value="view_part_and_division_headings", label="View part and division headings"),
        # cl.Action(name="section_actions",
        #value="recommend_section",
        #label="Recommend section"),
        #cl.Action(name="section_actions",
        #value="order_by_relevance",
        #label="Order by relevance"),
        cl.Action(name="section_actions", value="chat_with_these_provisions", label="Chat with Most Responsive"),
        cl.Action(name="section_actions",
                  value="ask_another",
                  label="Ask another"),
        cl.Action(name="section_actions",
                  value="end_this_query",
                  label="End this query"),
    ]

    # Format elements
    side_elements = [
        cl.Text(name="Statute Markdown", 
                content=statute_md, 
                display="side"),
        cl.Text(name="Most Reponsive",
                content=statute_sections_string,
                display="side"),
    ]
    inline_elements = [
        cl.Text(name="Top Headings",
                content=top_headings_string,
                display="inline"),
    ]
    elements = side_elements + inline_elements

    # Format message content including element names
    appended_text = "Results:\n"
    for element in side_elements:
        appended_text += f"* {element.name}\n"

    base_text = "The search results are below."
    content = f"{base_text}\n\n{appended_text}"

    # Send message
    sections_message = cl.Message(content=content,
                                  elements=elements,
                                  actions=actions)
    await sections_message.send()


# ---------- AFTER SECTIONS DISPLAYED ------- #
@cl.action_callback("section_actions")
async def section_actions_button(action):
    # TODO create these
    await cl.Message(content="Running...",
                     author="section_actions",
                     indent=True).send()

    if action.value == "ask_another":
        await get_and_handle_query()
        return

    action_function_pairs = {
        "see_more_sections": see_more_sections,
        "recommend_section": recommend_section,
        "order_by_relevance": order_by_relevance,
        "chat_with_these_provisions": chat_with_these_provisions,
        "ask_another": ask_another,
        "end_this_query": end_this_query,
    }

    section_function = action_function_pairs[action.value]

    await cl.Message(content="Running function",
                     author=action.value,
                     indent=True).send()

    # Can adapt this to get back other routing information, like returning a function.
    # TODO Or do it to get back message with actions in it
    # results_message = section_function(statute_query, section_results)
    # FOR TESTING
    await section_function()
    return


async def ask_another():
    await get_and_handle_query
    return


async def see_more_sections():
    await cl.Message(content="Not implemented", author="see_more_sections").send()
    return


async def recommend_section():
    await cl.Message(content="Not implemented", author="recommend_section").send()
    return


async def order_by_relevance():
    await cl.Message(content="Not implemented", author="order_by_relevance").send()
    return


async def chat_with_these_provisions():
    statute_query = cl.user_session.get("statute_query")
    print(statute_query)
    
    section_results = cl.user_session.get("section_results")
    statute_sections_string = section_results["statute_sections_string"]

    name = cl.user_session.get("chosen_statute")
    citation = cl.user_session.get("citation")

    conversation = Conversation()
    conversation.add_message('system', "You are an expert lawyer in British Columbia. Review the statutory provisions below, then answer the user's queries.")

    formatted_prompt = f"""Review these statutory provisions from the {name}, {citation}:

'''
{statute_sections_string}
'''

Provide your cautious and informative response to user queries, relying solely on the {name}, {citation} provisions above. Include any limitations to your response due to any information which may be missing."""

    # DEBUG
    print(formatted_prompt)

    conversation.add_message("system", formatted_prompt)

    cl.user_session.set("chat_ended", False)
    
    
    while True:
        if cl.user_session.get("chat_ended") == True:
            break
        # raise timeout error, if timeout break
        
        try:
            user_message = await cl.AskUserMessage(content="Your next message:", author="Chat", timeout=20, raise_on_timeout=True).send()
        except Exception as e:
            print(f'timeout: {e}')
            await end_this_query()
            break
        if user_message:
            conversation.add_message("user", user_message["content"])

            
            response = chat_completion_request(messages = conversation.messages, model="gpt-4")
            content = get_content_from_response(response)
            conversation.add_message("assistant", content)
            actions = [
                cl.Action(name="end_chat", value="end_chat", label="End chat"),
            ]
            await cl.Message(content=content, author="Chat with provisions", actions=actions).send()

    return


@cl.action_callback("end_chat")
async def end_chat_button(action):
    cl.user_session.set("chat_ended", True)
    await end_this_query()
    return


async def end_this_query():
    options_message =  get_options_message()
    await options_message.send()
    return



# ----------- QUERYING DATA AND API CALLS -------- #
# ------------- for all statutes ---------------- #


def get_statute_options_from_query(query):
    statute_options, _ = get_law_names_by_relatedness(
        query=query, top_n=NUMBER_OPTIONS_TO_RETRIEVE)
    return statute_options


# ------------- change options functions --------- #
def change_options(query, current_options, change_type):
    functions = {
        "rerank_options": rerank_options,
        "get_more_options": get_more_options,
    }

    change_function = functions[change_type]
    # DEBUG
    print(f"Change function: {change_function}")

    new_options = change_function(query, current_options)
    # DEBUG
    print(f"New options: {new_options}")
    return new_options


def get_more_options(query, statute_options):
    new_options = ["New option 1", "New option 2"]
    return new_options


def rerank_options(query, statute_options):
    reranked_options = choose_multiple_bc_statutes(
        query,
        statute_options,
        results_ratio=1,
        system_prompt=
        "You are an expert lawyer in British Columbia. You are prioritizing the order of your search. The below statutes have been identified as relevant. You will rerank them. Return all of the provided options, but reorder them so that the most applicable laws are first, and the least applicable last"
    )
    # DEBUG
    print(
        f"Original options: {statute_options}\nReranked options: {reranked_options}"
    )
    return reranked_options


# ---------- disambiguate by citation ---------- #
def get_citations_by_name(name, df):
    df = load_statute_dataframe()
    filtered_df = df[df['name'] == name]
    if not filtered_df.empty:
        citations = filtered_df['citation'].tolist()
        return citations


# --------- for specific statute questions --------- #
def get_query_results(name, citation, query):
    statute_dict = get_statute_dict(name, citation)
    statute_md = create_statute_markdown(statute_dict)
    statute_sections = get_statute_sections(statute_dict)

    text_ranker = TextRanker(
        f"{statute_dict['title']}, {statute_dict['neutral_citation']}.csv",
        statute_sections)

    strings, relatedness = text_ranker.execute_query(
        query["content"], top_n=len(statute_sections))

    top_headings_string = get_top_headings_string(query, strings)
    statute_sections_string = get_statute_sections_string(strings)

    results = {
        "name": name,
        "citation": citation,
        "query": query,
        "statute_dict": statute_dict,
        "statute_md": statute_md,
        "statute_sections": statute_sections,
        "text_ranker": text_ranker,
        "strings": strings,
        "relatedness": relatedness,
        "top_headings_string": top_headings_string,
        "statute_sections_string": statute_sections_string
    }

    return results


def get_text_ranker_for_statute(name, citation):
    df = load_statute_dataframe()
    # Lookup heading url by chosen name
    url = get_url(name, citation, df)
    statute_dict = get_statute_dict_from_url(url)

    statute_sections = []

    for key, value in statute_dict["sections"].items():
        section_md = create_section_markdown(value)
        statute_sections.append(section_md)

    text_ranker = TextRanker(
        f"{statute_dict['title']}, {statute_dict['neutral_citation']}.csv",
        statute_sections)

    return text_ranker


def get_top_headings_string(query, strings):
    number_heading_list = get_number_heading_list(strings)
    # print(number_heading_list)

    # headings = get_headings(number_heading_list)
    headings = []
    for _, heading in number_heading_list:
        headings.append(heading)

    selected_headings = get_selected_headings(headings)
    # Could also reverse, this should be parameter to choose from
    random.shuffle(selected_headings)

    # TODO decide
    # TODO craft promopt for this, remove stop sequence so can be reordering
    top_headings = get_multiple_options_for_query_from_list(query,
                                                            selected_headings,
                                                            results_ratio=1)
    # DEBUG
    # print(f"Top heading: {top_headings}")

    top_headings_list = get_top_headings_list(top_headings,
                                              number_heading_list)
    print(f"Top headings list: {top_headings_list}")
    # DECIDE WHAT TO DO WITH THIS
    top_headings_string = ""
    for item in top_headings_list:
        top_headings_string += f"{item}\n"

    return top_headings_string


# ------------- DATA FORMATTING UTILITIES ------------ #
def get_url(name, citation, df):
    filtered_df = df[(df['name'] == name) & (df['citation'] == citation)]
    if not filtered_df.empty:
        url = filtered_df.iloc[0]['url']
        return url
    else:
        return None


def get_statute_dict(name, citation):
    df = load_statute_dataframe()
    url = get_url(name, citation, df)

    statute_dict = get_statute_dict_from_url(url)
    return statute_dict


def get_name_url_list_for_statutes(statutes: list):
    df = load_statute_dataframe()

    filtered_list = [
        (name, citation, url)
        for name, citation, url in zip(df['name'], df['citation'], df['url'])
        if name in statutes
    ]
    return filtered_list


def format_markdown_statute_list(statutes):
    data = get_name_url_list_for_statutes(statutes)
    statute_list = ""
    for name, citation, url in data:
        statute_list += f"[{name}, {citation}]({url})\n"
    return statute_list


def get_statute_sections(statute_dict):
    statute_sections = []

    for key, value in statute_dict["sections"].items():
        section_md = create_section_markdown(value)
        statute_sections.append(section_md)

    return statute_sections


def get_number_heading_list(strings):
    number_heading_list = []
    for item in strings:
        regex_pattern = r"\#* (.*)\n\n\*\*(\S{1,10})\*\*"
        match = re.search(regex_pattern, item)
        if match:
            heading = match.group(1)
            number = match.group(2)
            number_heading_list.append((number, heading))
        else:
            print("ERROR in number_heading_list: no match")
    return number_heading_list


def get_selected_headings(headings):
    headings_copy = headings.copy()
    number_of_selected_headings = 0
    if len(headings) > 100:
        number_of_selected_headings = 15
    else:
        number_of_selected_headings = int(len(headings) / 5)
    if number_of_selected_headings < 5:
        number_of_selected_headings = 5
    selected_headings = headings_copy[0:number_of_selected_headings - 1]
    return selected_headings


def get_statute_sections_string(strings):
    statute_sections_string = ""

    for string in strings:
        if len(statute_sections_string) + len(string) + 2 > 4000:
            break
        statute_sections_string += f"{string}\n\n"

    return statute_sections_string


def get_top_headings_list(top_headings, number_heading_list):
    # To format section number and heading as list of strings in reranked order
    top_headings_list = []
    for top_heading in top_headings:
        for number, heading in number_heading_list:
            if top_heading == heading:
                top_headings_list.append(f"{number}  {heading}")
    return top_headings_list
