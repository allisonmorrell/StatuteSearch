import ast  # for converting embeddings saved as strings back to arrays
import os
import time

# from generate_embeddings import generate_embeddings


import openai  # for calling the OpenAI API
import pandas as pd  # for storing text and embeddings data
# import tiktoken  # for counting tokens
from scipy import spatial  # for calculating vector similarities for search


# Following tutorial from here: https://github.com/openai/openai-cookbook/blob/main/examples/Question_answering_using_embeddings.ipynb


EMBEDDING_MODEL = "text-embedding-ada-002"  # OpenAI's best embeddings as of Apr 2023
GPT_MODEL = "gpt-3.5-turbo"


def main():
    # TODO move from other file in here?
    # test_generate_embeddings()
    pass



def test_get_law_names_by_relatedness():
    query = "I'm a contractor. I want to register something to make sure I get paid."

    strings, relatedness = get_law_names_by_relatedness(query)

    print(strings)
    print(relatedness)


    

def get_law_names_by_relatedness(
    query: str, 
    top_n=10):
    df = get_df_by_filename("statute_name_embeddings.csv")
    
    strings, relatedness = strings_ranked_by_relatedness(
        query=query,
        df=df,
        top_n=top_n)

    return strings, relatedness

# TODO combine so can check for embedding existing and if it doesn't exist, create it, run the query, and return the result of strings_ranked_by_relatedness

def get_df_by_filename(filename):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    embeddings_dir = os.path.join(current_dir, "data")
    embeddings_path = os.path.join(embeddings_dir, filename)

    try:
        df = load_embeddings(embeddings_path)
        return df
    except Exception:
        raise ValueError(f"Filepath {embeddings_path} does not exist in {current_dir}")


def load_embeddings(path):
    df = pd.read_csv(path)
    df['embedding'] = df['embedding'].apply(ast.literal_eval)
    return df


def strings_ranked_by_relatedness(
    query: str,
    df: pd.DataFrame,
    relatedness_fn=lambda x, y: 1 - spatial.distance.cosine(x, y),
    top_n: int = 100,
    print_time = False
) -> tuple[list[str], list[float]]:
    """Returns a list of strings and relatednesses, sorted from most related to least."""
    start_embedding_time = time.time()
    query_embedding_response = openai.Embedding.create(
        model=EMBEDDING_MODEL,
        input=query,
    )
    query_embedding = query_embedding_response["data"][0]["embedding"]
    end_embedding_time = time.time()
    
    start_search_time = time.time()
    strings_and_relatednesses = [
        (row["text"], relatedness_fn(query_embedding, row["embedding"]))
        for i, row in df.iterrows()
    ]
    strings_and_relatednesses.sort(key=lambda x: x[1], reverse=True)
    end_search_time = time.time()

    if print_time:
        print(f"Embedding time: {end_embedding_time - start_embedding_time}\nSearch time: {end_search_time - start_search_time}")
    strings, relatednesses = zip(*strings_and_relatednesses)
    return strings[:top_n], relatednesses[:top_n]

if __name__ == "__main__":
    main()