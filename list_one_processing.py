# List One Processing

import pymupdf
import re
import json
import time
import bisect


located_flags: list[dict] = []

from transformers import pipeline

print("Initializing privacy classifier...")
privacy_classifier = pipeline(
    task="token-classification",
    model="openai/privacy-filter",
    aggregation_strategy="simple"
)

print("Initializing semantic similarity model...")
import shared_functions as sf


def scan_file(pdf_file_name):
    global located_flags
    doc = pymupdf.open(pdf_file_name)


    # Measure performance
    overall_time_start = time.perf_counter()

    
    page_num = 0
    for page in doc:
        located_on_this_page = []
        page_num += 1
        page_text = page.get_text()

        print("Processing page " + str(page_num) + "...")
        page_time_start = time.perf_counter()

        # Split into individual sentences (for highlighting)
        sentence_endings = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
        sentences = re.split(sentence_endings, page_text)

        located_on_this_page += find_classified(sentences, page_num)
        located_on_this_page += find_personal_privacy(page_text, page_num)
        located_on_this_page += find_internal_deliberations_legal_advice(sentences, page_num)

        located_flags += located_on_this_page

        page_time_end = time.perf_counter()
        page_time = page_time_end - page_time_start
        print(f"Page {page_num} execution time: {page_time:.6f} seconds")

    overall_time_end = time.perf_counter()
    overall_time = overall_time_end - overall_time_start
    print(f"Scan file execution time: {overall_time:.6f} seconds")

    return located_flags
        
def find_classified(sentences, page_num) -> list:
    """
    This function searches for markers of classified information.
    Input: list of sentences, current page number
    Output: list of issue structures
    """

    # Get all the pieces in parentheses
    matches = []
    for sentence_num, sentence in enumerate(sentences):
        # Find items in parentheses
        pattern = r"\((.*?)\)"
        results = re.findall(pattern, sentence)

        classifiers = ["C", "S", "TS", "CUI"]

        # Split items in parentheses by commas, slashes, and spaces
        possible_classifiers = []
        for i in results:
            result = re.split(r'[, /]+', i)
            possible_classifiers += result

        # Search for classifiers
        for i in possible_classifiers:
            if i in classifiers:
                print("Classifier found: " + i)
                matches.append({
                    "text": sentences[sentence_num],
                    "flag": "List 1 - Classified Information",
                    "page": page_num,
                    "color": "red",
                    "explanation": "Detected classifier: " + i
                })
    return matches

def find_protected_by_law(page_text):
    print("Not yet implemented")

def find_business_secrets(page_text):
    print("Not yet implemented")

def find_internal_deliberations_legal_advice(sentences, page_num):
    keywords = ["deliberation", "draft", "legal", "predecision", "risk", "evaluation", "advice", "counsel", "attorney", "attorneys", "lawyer", "lawyers"]

    print("Finding similar sentences to 'internal deliberation':")
    semantic_matches = sf.find_similar_sentences(sentences, "An agency was reviewing a draft policy and weighing possible courses of action.")
    filtered_semantic_matches = sf.threshold_cut_or_keyword(semantic_matches, keywords, threshold=0.3)

    issues = []
    for index, sentence in enumerate(filtered_semantic_matches[0]):
        print(f"Filtered semantic match {index + 1}: {sentence}")
        print(f"Reason: {filtered_semantic_matches[1][index]}")
        issues.append({
            "text": sentence,
            "flag": "List 1 - Internal Deliberation or Legal Advice",
            "page": page_num,
            "color": "red",
            "explanation": filtered_semantic_matches[1][index]
        })
    
    return issues
                
def find_personal_privacy(page_text, page_num):
    """
    This function searches for personal privacy information.
    Input: page text, current page number
    Output: list of issue structures
    """
    
    # TODO: Compare with Presidio
    # TODO: Be influenced by the confidence value

    sentence_pattern = r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=[.?!])\s+"

    matches = list(re.finditer(sentence_pattern, page_text))

    sentences = []
    sentence_start_points = []

    start = 0

    # Calculate sentence start points for bisecting later
    for match in matches:
        end = match.start()
        sentences.append(page_text[start:end])
        sentence_start_points.append(start)
        start = match.end()

    if start < len(page_text):
        sentences.append(page_text[start:])
        sentence_start_points.append(start)

    global privacy_classifier
    pii_found = privacy_classifier(page_text)  
    
    chunk_assembler = ""

    pii_issues = {}
    
    for chunk in pii_found:
        chunk_assembler += chunk["word"]

        # Figure out which sentence is the issue
        sentence_id = bisect.bisect_right(sentence_start_points, chunk["start"]) - 1

        # Initialize a new PII issue entry if it doesn't exist, otherwise add the reason to the existing entry
        if not str(sentence_id) in pii_issues:
            pii_issues[str(sentence_id)] = {
                "text": sentences[sentence_id],
                "flag": "red",
                "reasons": set([chunk["entity_group"]]),
                "page": page_num,
                "color": "red",
                "explanation": "PII detected: "
            }
        else:
            pii_issues[str(sentence_id)]["reasons"].add(chunk["entity_group"])

    # Add reasons to explanation and remove the reasons set from the final output
    for i in pii_issues:
        pii_issues[i]["explanation"] += ", ".join(pii_issues[i]["reasons"])
        del pii_issues[i]["reasons"]

    # Return the values of the dictionary as a list
    return pii_issues.values()

def find_law_enforcement_records(page_text):
    print("Not yet implemented")

def find_financial_regulation(page_text):
    print("Not yet implemented")

def find_wells(page_text):
    print("Not yet implemented")

def ai_confirm():
    print("Not yet implemented")





if __name__ == "__main__":
    file_name = input("File Name: ")
    print(scan_file(file_name))