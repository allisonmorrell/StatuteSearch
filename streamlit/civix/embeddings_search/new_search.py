import ast
import os
import time
import numpy as np
import openai
import pandas as pd
from scipy import spatial
from typing import List, Tuple


EMBEDDING_MODEL = "text-embedding-ada-002"  # OpenAI's best embeddings as of Apr 2023
GPT_MODEL = "gpt-3.5-turbo"


class TextRanker:
    def __init__(self, embedding_filename: str, strings: List[str], embedding_model: str=EMBEDDING_MODEL):
        self.strings = strings
        self.embedding_model = embedding_model
        self.embedding_filename = embedding_filename
        self.embeddings_df = self.generate_or_load_embeddings()

    
    def generate_or_load_embeddings(self):
        embeddings_path = f"/home/runner/StatuteSearch/streamlit/civix/embeddings_search/data/{self.embedding_filename}"
    
        if os.path.exists(embeddings_path):
            df = self.get_df_by_filename(embeddings_path)
        else:
            generate_embeddings_and_save(self.strings, self.embedding_filename)
            df = self.load_embeddings(embeddings_path)
    
        return df

    def get_df_by_filename(self, embeddings_path):
    
        try:
            df = self.load_embeddings(embeddings_path)
            return df
        except Exception:
            raise ValueError(f"Filepath {embeddings_path} does not exist")
    
    
    def load_embeddings(self, path: str):
        data_path = "/home/runner/StatuteSearch/streamlit/civix/embeddings_search/data/"
        path = os.path.join(data_path, path)
        df = pd.read_csv(path)
        df['embedding'] = df['embedding'].apply(ast.literal_eval)
        return df

    def strings_ranked_by_relatedness(
        self,
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

    
    def execute_query(self, query: str, top_n: int = 10) -> Tuple[List[str], List[float]]:
        strings, relatedness = self.strings_ranked_by_relatedness(
            query=query,
            top_n=top_n,
            df=self.embeddings_df
        )

        return strings, relatedness


def generate_embeddings_and_save(string_list: List[str], filename: str, embedding_model=EMBEDDING_MODEL):
    BATCH_SIZE = 5  # adjust as needed
    embeddings = []
    
    for batch_start in range(0, len(string_list), BATCH_SIZE):
        batch_end = batch_start + BATCH_SIZE
        batch = string_list[batch_start:batch_end]
        print(f"Batch {batch_start} to {batch_end-1}")
        response = openai.Embedding.create(model=EMBEDDING_MODEL, input=batch)
        for i, be in enumerate(response["data"]):
            assert i == be["index"]  # double check embeddings are in same order as input
        batch_embeddings = [e["embedding"] for e in response["data"]]
        embeddings.extend(batch_embeddings)
    
    df = pd.DataFrame({"text": string_list, "embedding": embeddings})
    save_path = f"/home/runner/StatuteSearch/streamlit/civix/embeddings_search/data/{filename}"

    # Create the directory if it doesn't exist
    # TODO: getting FileNotFoundError
    # Write DataFrame to the file
    df.to_csv(save_path, index=False)

