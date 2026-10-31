# List One Processing

import pymupdf
import re
import json
import time

located_flags: list[dict] = []

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

        # Quick and dirty stage
        located_on_this_page += find_classified(sentences, page_num)

        located_flags += located_on_this_page

        page_time_end = time.perf_counter()
        page_time = page_time_end - page_time_start
        print(f"Page {page_num} execution time: {page_time:.6f} seconds")

    overall_time_end = time.perf_counter()
    overall_time = overall_time_end - overall_time_start
    print(f"Scan file execution time: {overall_time:.6f} seconds")

    return located_flags
        

def find_classified(sentences, page_num) -> list:
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

def find_internal_deliberations_legal_advice(page_text):
    print("Not yet implemented")

def find_personal_privacy(page_text):
    print("Not yet implemented")

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