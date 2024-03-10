import streamlit as st
import re
from collections import Counter
from urllib.parse import quote

def main():
    st.title("Legal Citation Search")

    user_input = st.text_area("Input text", '')

    if st.button("Search"):
        neutralPattern = r'(?:1|2)[0-9]{3} [A-Z]{2,8} [0-9]{1,8}'
        otherPattern = r'\[?[0-9]{1,5}\]? ?[0-9]{0,5} (?:BCLR|DLR|OR|WWR|CCC|CPR|Can Tax J|ALR|FCR|Sask LR|CBR|CHRR|CJFL|CLELJ|CLT|CRR|CR|MLB|RFL|SCR|SCJ|ACS|LAC|APR|B\.C\.L\.R\.|D\.L\.R\.|O\.R\.|W\.W\.R\.|C\.C\.C\.|C\.P\.R\.|Can Tax J|A\.L\.R\.|F\.C\.R\.|Sask\. L\.R\.|C\.B\.R\.|C\.H\.R\.R\.|C\.J\.F\.L\.|C\.L\.E\.L\.J\.|C\.L\.T\.|C\.R\.R\.|C\.R\.|M\.L\.B\.|R\.F\.L\.|S\.C\.R\.|S\.C\.J\.|A\.C\.S\.|L\.A\.C\.|A\.P\.R\.) \(?[0-9]{0,1}[a-z]{0,3}\)? ?[0-9]{1,6}'
        statutePattern = r'R?\.?[SC]\.?[A-Z\.]{0,5}[ ,]{1,2}[0-9\-]{0,10}[ ,]{0,2}c.? [0-9A-Z\-‑]{1,6}'
        regulationPattern = r'(?:BC Reg|Alta Reg|Sask Reg|Man Reg|O Reg|RLRQ|NB Reg|NS Reg|PEI Reg|NLR|SOR|CRC|YOIC|NWT Reg|NU Reg|NWT R\-|NU R\-|BC Reg\.|B\.C\. Reg\.|Alta\. Reg\.|Sask\. Reg\.|Man\. Reg\.|O\. Reg\.|RLRQ\.|NB Reg\.|NS Reg\.|PEI Reg\.|NLR\.|C\.R\.C\.|YOIC\.|NWT Reg\.|NU Reg\.) [0-9]{1,5}\/[0-9]{2,4}'

        neutralMatches = re.findall(neutralPattern, user_input)
        otherMatches = re.findall(otherPattern, user_input, re.I)
        statuteMatches = re.findall(statutePattern, user_input, re.I)
        regulationMatches = re.findall(regulationPattern, user_input, re.I)

        # Summary stats
        totalResults = len(neutralMatches) + len(otherMatches) + len(statuteMatches) + len(regulationMatches)
        wordCount = len(user_input.split())

        allMatches = neutralMatches + otherMatches + statuteMatches + regulationMatches
        allMatches.sort()

        # Group the matches and generate URLs
        groups = [allMatches[i:i+20] for i in range(0, len(allMatches), 20)]
        urls = [searchUrl(group) for group in groups]

        # Count court citations
        courtCounts = countCourts(neutralMatches)
        courtTable = "\n".join([f"Court: {court}, Count: {count}" for court, count in courtCounts])

        st.write(f"Total matches: {totalResults}")
        st.write(f"Word count: {wordCount}")
        st.write("Search links:")
        for i, url in enumerate(urls, start=1):
            st.write(f"{i}: {url}")
        st.write("All results:")
        for match in allMatches:
            st.write(match)
        st.write("Citation frequency:")
        st.write(courtTable)

        # Display the matches for each search
        st.write("Neutral Citations:")
        st.write('\n'.join(neutralMatches) if neutralMatches else "No neutral citations found.")
        st.write("Other Citations:")
        st.write('\n'.join(otherMatches) if otherMatches else "No other citations found.")
        st.write("Statutes:")
        st.write('\n'.join(statuteMatches) if statuteMatches else "No statutes found.")
        st.write("Regulations:")
        st.write('\n'.join(regulationMatches) if regulationMatches else "No regulations found.")

def searchUrl(arr):
    encodedTerms = '%20OR%20'.join(f'%22{quote(term)}%22' for term in arr)
    return f"https://www.canlii.org/en/#search/id={encodedTerms}"

def countCourts(matches):
    courtCounts = Counter(match.split(" ")[1] for match in matches)
    return sorted(courtCounts.items(), key=lambda x: x[1], reverse=True)

if __name__ == "__main__":
    main()

