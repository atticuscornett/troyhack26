import pymupdf
import json
import re
import time
from ollama import chat
from ollama import ChatResponse

located_flags: list[dict] = []

def scan_file(pdf_file_name):
    global located_flags
    doc = pymupdf.open(pdf_file_name)

    # Measure performanc
    overall_time_start = time.perf_counter()

    page_num = 0
    for page in doc:
        located_on_this_page = []
        page_num += 1
        page_text = page.get_text()

        print("Processing page " + str(page_num) + "...")
        page_time_start = time.perf_counter()

        # Split into sentences for highlighting
        sentence_endings = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
        sentences = re.split(sentence_endings, page_text)

        # Quick and dirty stage
        located_on_this_page += find_keyword(sentences, page_num)

        located_flags += located_on_this_page

        page_time_end = time.perf_counter()
        page_time = page_time_end - page_time_start
        print(f"Page {page_num} execution time: {page_time:.6f} seconds")

    overall_time_end = time.perf_counter()
    overall_time = overall_time_end - overall_time_start
    print(f"Scan file execution time: {overall_time:.6f} seconds")

    return located_flags

def find_keyword(sentences, page_num) -> list:
    # Get all the pieces in parentheses
    matches = []
    keywords = ["animal testing", "directed energy", "weapon", "unamanned", "aerial", "remotely", "cyber", "physiologic", "oxygen", "hypobaria", "hypopoxia", "laser", "particle", "space", "nuclear", "research", 
              "operation", "exercise", "security", "chemical", "biological", "toxin", "current", "vulnerability", "training", "air", "tactics", "procedures", "deploy", "washington", "national", "international", "president", "secretary",
              "foreign", "dod", "data", "information", "traffic", "dopsr", "wing", "unit", "sensitive", "perfuoroalkyl", "pfas", "perfluorooctanoic", "pfoa", "perfoluorooctance", "pfos"]

    # Split sentences into individual words
    for sentence_num, sentence in enumerate(sentences, start=1):

        # Normalize sentence
        sentence_lower = sentence.lower()

        # Search for keywords
        for keyword in keywords:

            # Match whole words or phrases
            pattern = r'\b' + re.escape(keyword) + r'\b'

            if re.search(pattern, sentence_lower):

                print(f"Keyword found: {keyword}")

                matches.append({
                    "page": page_num,
                    "sentence_number": sentence_num,
                    "text": sentence.strip(),
                    "Keyword": keyword
                })

    return matches

def ollama_compare(page_text, page_num):
    conditions = ["Does the text discuss weapons, military systems, and emerging technologies?",
                  "Does the text discuss cybersecurity, intelligence, and operational security?",
                  "Does the text discuss medical, physiological, chemical, and biological research?",
                  "Does the text discuss national security, policy, and sensitive government information?",
                  "Does the text discuss interagency and interservice coordination?"]

    
    
if __name__ == "__main__":
    file_name = input("File Name: ")
    print(scan_file(file_name))