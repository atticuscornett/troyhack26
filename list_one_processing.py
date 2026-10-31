# List One Processing

import pymupdf
import re
import json

located_flags: list[dict] = []

def scan_file(pdf_file_name):
    global located_flags
    doc = pymupdf.open(pdf_file_name)

    page_num = 0
    for page in doc:
        located_on_this_page = []
        page_num += 1
        page_text = page.get_text()
        #print("Page " + str(page_num) + ": ")
        #print(page_text)

        sentence_endings = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
        sentences = re.split(sentence_endings, page_text)

        # Quick and dirty stage
        located_on_this_page += find_classified(sentences, page_num)

        located_flags += located_on_this_page

    return located_flags
        

def find_classified(sentences, page_num) -> list:
    # Get all the pieces in parentheses
    matches = []
    for sentence_num, sentence in enumerate(sentences):
        pattern = r"\((.*?)\)"
        results = re.findall(pattern, sentence)

        classifiers = ["C", "S", "TS", "CUI"]
        
        possible_classifiers = []
        for i in results:
            result = re.split(r'[, /]+', i)
            possible_classifiers += result

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