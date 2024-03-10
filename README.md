This is a hodgepodge of code from different projects thrown together to create a Chainlit chatbot application for question-answering over BC Statutes. WARNING it is messy and disorganized! Not intending to develop further at this time but hope to use code from here to work on a package for working with the (BC Laws API)[https://www.bclaws.gov.bc.ca/civix/template/complete/api/index.html]. Also contains code relating to using logit bias on OpenAI API to rank options.

# Running the app(s)

To set up, add an OpenAI API key to `.env` as `OPENAI_API_KEY` (or to Secrets if running in Replit). (You may also need to fix other issues, such as the file paths where statute embeddings are stored.)

From top directory in shell run:

```
chainlit run statute_app.py
```

There is also a Streamlit app originally used when I was pulling the statute lists and which can be used to update them. To view statute info, navigate to `/streamlit` and run `streamlit run app.py`.

# How things work

(as far as I recall)

## Chainlit app

Uses a somewhat convoluted logic to search and drill down on sections, then offers an opportunity to ask questions to GPT-4 about the set of sections that are returned.

The initial statute list is pulled by embedding the user query and comparing similarity to statute names.

The statute re-ranking uses the `logit_bias` parameter of the OpenAI API to force the model to return only given tokens, and uses the prompts in `choose_law.py` to rank or choose appropriate statutes for a given question.

Once you choose a statute, you input your query and the system returns a batch of sections considered most responsive to the query using section headings (imperfect). [NOTE this is confusing and needs fixing, ideally should filter section text for responsiveness to query]

Usefully, the entire statute you're searching is converted to Markdown and can be shown in a side panel and searched with Ctrl + F. 

## CIVIX API

There is a bunch of code and previous work of progress (not in use in the main chatbot app) in `streamlit/civix` for working with the BC Laws API.

The app needs the list of all statutes found at `streamlit/civix/data` to work - this is pulled from the BC Laws API in a somewhat time-consuming function `get_all_statutes` found in `streamlit/civix/get_statutes`. It would need to be rerun in order to add any new statutes. It is included in this repo so you don't need to run it.

## Embeddings search

Within `streamlit/civix/embeddings_search` is the main logic for generating embeddings and similarity search. Statute embeddings are stored in `streamlit/civix/embeddings_search/data`. Once created, the app will use the previous versions. If they need to be updated, delete the statute so it gets rerun next time.

The search itself is a very basic implementation. 

## Other things
`section_retrieval.py` contains code related to retrieving sections from statutes by ID and also in progress work on hybrid similarity search and logit bias-based ranking.