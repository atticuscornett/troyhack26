import pymupdf
import json
import re
import time
import bisect

located_flags: list[dict] = []

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

        # Split into sentences for highlighting
        sentence_endings = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
        sentences = re.split(sentence_endings, page_text)

        # Quick and dirty stage
        #located_on_this_page += find_keyword(sentences, page_num)
        located_on_this_page += find_weapons(sentences, page_num)
        located_on_this_page += find_cyber(sentences, page_num)
        located_on_this_page += find_medical(sentences, page_num)
        located_on_this_page += find_policy(sentences, page_num)
        located_on_this_page += find_inter(sentences, page_num)

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
    matching_sentences = []
    keywords = ["animal testing", "directed energy", "weapon", "cyber", "physiologic", "oxygen", "hypobaria", "hypopoxia", "aerial", "unamanned", "space", "laser", "research", "particle",
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
                matching_sentences.append({
            "text": sentence,
            "flag": "List 2 - Keywords",
            "page": page_num,
            "color": "red", # Change color to depend on confidence
            "explanation": "Keyword"
        })
    return matching_sentences


def find_weapons(sentences, page_num):
    condition = "weapons, military systems, and emerging technologies?"
    keywords = ["weapon", "unamanned", "animal testing", "aerial", "drone", "remotely", "nuclear", "laser", "particle", "directed energy"]

    print("Finding similar sentences to 'weapons, military systems, and emerging technologies':")
    semantic_matches = sf.find_similar_sentences(sentences, condition)
    filtered_semantic_matches = sf.threshold_cut_or_keyword(semantic_matches, keywords)

    #semantic_matches = []    

    issues = []
    for index, sentence in enumerate(filtered_semantic_matches[0]):
        print(f"Filtered semantic match {index + 1}: {sentence}")
        print(f"Reason: {filtered_semantic_matches[1][index]}")
        issues.append({
            "text": sentence,
            "flag": "List 2 - Weapons, Military Systems, and Emerging Technologies",
            "page": page_num,
            "color": "yellow", # Change color to depend on confidence
            "explanation": filtered_semantic_matches[1][index]
        })

    return issues

def find_cyber(sentences, page_num):
    condition = "cybersecurity, intelligence, and operational security?"
    keywords = ["cyber", "traffic", "vulnerabilities", "detail", "description"]

    print("Finding similar sentences to 'cybersecurity, intelligence, and operational security':")
    semantic_matches = sf.find_similar_sentences(sentences, condition)
    filtered_semantic_matches = sf.threshold_cut_or_keyword(semantic_matches, keywords)

    issues = []
    for index, sentence in enumerate(filtered_semantic_matches[0]):
        print(f"Filtered semantic match {index + 1}: {sentence}")
        print(f"Reason: {filtered_semantic_matches[1][index]}")
        issues.append({
            "text": sentence,
            "flag": "List 2 - Cybersecurity, Intelligence, and Operational Security",
            "page": page_num,
            "color": "yellow", # Change color to depend on confidence
            "explanation": filtered_semantic_matches[1][index]
        })

    return issues

def find_medical(sentences, page_num):
    condition = "medical, physiological, chemical, and biological research"
    keywords = ["physiologic", "oxygen", "research", "hypobaria", "hypopoxia", "chemical", "biological", "fatigue", "deshydration", "toxin", "perfuoroalkyl", "pfas", "perfluorooctanoic", "pfoa", "perfoluorooctance", "pfos"]
    
    print("Finding similar sentences to 'medical, physiological, chemical, and biological research':")
    semantic_matches = sf.find_similar_sentences(sentences, condition)
    filtered_semantic_matches = sf.threshold_cut_or_keyword(semantic_matches, keywords)
    
    issues = []
    for index, sentence in enumerate(filtered_semantic_matches[0]):
        print(f"Filtered semantic match {index + 1}: {sentence}")
        print(f"Reason: {filtered_semantic_matches[1][index]}")
        issues.append({
            "text": sentence,
            "flag": "List 2 - Medical, Physiological, Chemical, and Biological Research",
            "page": page_num,
            "color": "yellow", # Change color to depend on confidence
            "explanation": filtered_semantic_matches[1][index]
        })

    return issues

def find_policy(sentences, page_num):
    condition = "national security, policy, and sensitive government information?"
    keywords = ["operation", "dopsr", "exercise", "security", "current", "training", "tactics", "procedures", "deploy", "wing", "unit", "sensitive"]

    print("Finding similar sentences to 'national security, policy, and sensitive government information':")
    semantic_matches = sf.find_similar_sentences(sentences, condition)
    filtered_semantic_matches = sf.threshold_cut_or_keyword(semantic_matches, keywords)
        
    issues = []
    for index, sentence in enumerate(filtered_semantic_matches[0]):
        print(f"Filtered semantic match {index + 1}: {sentence}")
        print(f"Reason: {filtered_semantic_matches[1][index]}")
        issues.append({
            "text": sentence,
            "flag": "List 2 - National Security, Policy, and Sensitive Government Information",
            "page": page_num,
            "color": "yellow", # Change color to depend on confidence
            "explanation": filtered_semantic_matches[1][index]
        })

    return issues

def find_inter(sentences, page_num):
    condition = "interagency and interservice coordination?"
    keywords = ["washington", "national", "international", "president", "secretary", "dod", ]

    print("Finding similar sentences to 'national security, policy, and sensitive government information':")
    semantic_matches = sf.find_similar_sentences(sentences, condition)
    filtered_semantic_matches = sf.threshold_cut_or_keyword(semantic_matches, keywords)
            
    issues = []
    for index, sentence in enumerate(filtered_semantic_matches[0]):
        print(f"Filtered semantic match {index + 1}: {sentence}")
        print(f"Reason: {filtered_semantic_matches[1][index]}")
        issues.append({
            "text": sentence,
            "flag": "List 2 - National Security, Policy, and Sensitive Government Information",
            "page": page_num,
            "color": "yellow", # Change color to depend on confidence
            "explanation": filtered_semantic_matches[1][index]
        })
    
    return issues
    
if __name__ == "__main__":
    file_name = input("File Name: ")
    print(scan_file(file_name))