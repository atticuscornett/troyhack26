import os
SKIP_LLM = os.getenv("SKIP_LLM") == "1"

#OLLAMA_MODEL = "gemma4:12b"
OLLAMA_MODEL = "qwen3.5:4b"
SIMILARITY_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

SIMILARITY_THRESHOLD: float = 0.25
WINDOW_SIZE: int = 1

from sentence_transformers import SentenceTransformer, util
from transformers import AutoModel, AutoTokenizer
import re
import ollama

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def find_similar_sentences(sentences: str, topic_sentence: str, threshold: float = SIMILARITY_THRESHOLD) -> list:
    """
    Compare given text to a topic sentence and return sentences that are similar to the topic sentence.
    Input: text to search, topic sentence to compare against
    Output: list of dictionaries containing the target sentence, context window, and similarity score
    """

    # Compute the vectors for the sentences
    anchor_vector = model.encode(topic_sentence, convert_to_tensor=True)
    sentence_vectors = model.encode(sentences, convert_to_tensor=True)
    
    # Compute cosine similarities instantly using the built-in util function
    similarities = util.cos_sim(sentence_vectors, anchor_vector).squeeze(-1).tolist()
    
    matched_windows = []

    for idx, (sentence, score) in enumerate(zip(sentences, similarities)):
        if score >= SIMILARITY_THRESHOLD:
            start = max(0, idx - WINDOW_SIZE)
            end = min(len(sentences), idx + WINDOW_SIZE + 1)
            context = " ".join(sentences[start:end])
            
            matched_windows.append({
                "target_sentence": sentence,
                "context_window": context,
                "similarity_score": round(score, 3)
            })
            
    return matched_windows

def threshold_cut_or_keyword(vector_output, keyword_list, threshold=0.3):
    """
    Cuts or keywords to filter a list of sentences based on a similarity threshold and a list of keywords.
    """

    relavent_sentences = []
    reasons = []
    context_windows = []

    for item in vector_output:
        if item['similarity_score'] >= threshold:
            relavent_sentences.append(item['target_sentence'])
            reasons.append(f"Sentence is similar to topic above. (Similarity score: {item['similarity_score']})")
            context_windows.append(item['context_window'])
        else:
            for keyword in keyword_list:
                if keyword.lower() in item['target_sentence'].lower():
                    relavent_sentences.append(item['target_sentence'])
                    reasons.append(f"Sentence contains keyword '{keyword}'.")
                    context_windows.append(item['context_window'])
                    break
    return [relavent_sentences, reasons, context_windows]
        
def llm_semantic_analysis(filtered_semantic_matches, task_description, flag_name):
    if SKIP_LLM:
        print("Skipping LLM semantic analysis due to SKIP_LLM environment variable.")
        return filtered_semantic_matches

    context_windows = filtered_semantic_matches[2]
    print(f"Context windows for LLM analysis: {context_windows}")
    # Build text blocks mapped to indices
    xml_items = []
    for idx, win in enumerate(context_windows):
        xml_items.append(f'<window id="{idx}">\n{win}\n</window>')
    
    formatted_windows = "\n\n".join(xml_items)

    prompt = f"""You are a data validation engine designed to identify "{task_description}".
        Analyze each text sequence block provided inside the <windows> tags below.

        <windows>
        {formatted_windows}
        </windows>

        Return your final evaluations as a strict JSON array of objects. Do not write markdown, code blocks, or conversational preambles. Follow this structural format exactly:
        [
        {{"id": 0, "is_{flag_name}": true, "reasoning": "A brief sentence why."}},
        {{"id": 1, "is_{flag_name}": false, "reasoning": "A brief sentence why."}}
        ]"""

    print("Sending prompt to LLM for semantic analysis...")
    print(prompt)

    try:
        response = ollama.generate(
            model=OLLAMA_MODEL, 
            prompt=prompt,
            format='json', 
            options={
                "temperature": 0.0,
                "num_predict": 300,
                "num_ctx": 4096,
            }
        )
        print("LLM response received.")
        print(response['response'])
        print("PLEASE IMPLEMENT PLEASE AAAAAA")
        return filtered_semantic_matches
    except Exception as e:
        print(f"Error processing batch: {e}")
        return filtered_semantic_matches
    