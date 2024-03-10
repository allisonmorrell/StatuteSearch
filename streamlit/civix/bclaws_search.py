import requests
from bs4 import BeautifulSoup

# Don't know if any of this works

def get_search_content(q, s = 0, e = 20, nfrag = 5, lfrag = 100):
  
  # Check parameters within permitted bounds
  if e - s > 100:
    raise ValueError("Difference between s and e may not be greater than 100")
          
  if nfrag > 9:
    raise ValueError("nfrag may not be greater than 9")
          
  if lfrag > 199: 
    raise ValueError("lfrag may not be greater than 199")

  # Structure search
  root = "http://www.bclaws.ca/civix/search/complete"
  url = f'{root}/fullsearch?q={q}&s={s}&e={e}&nFrag={nfrag}&lFrag={lfrag}'
  print(url)

  # Get requests
  response = requests.get(url)
  content = response.content
  if content:
    print("Response received")

  return content


# -------------- TODO --------------- #
# revise this to return a different format
def print_search_results(content):
    soup = BeautifulSoup(content, "xml")

    results = soup.find("results")
    query = results["query"]
    hits = results["allHits"]

    print(f"Query: {query}")
    print(f"Hits: {hits}")


    docs = soup.find_all("doc")

    for doc in docs:
        for child in doc.children:
            print(child.name)
            print(child.contents)
    print(doc.contents)
    print(doc.descendants)