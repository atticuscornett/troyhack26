OLLAMA_MODEL = "gemma4:12b"
SIMILARITY_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

SIMILARITY_THRESHOLD: float = 0.25
WINDOW_SIZE: int = 3

from sentence_transformers import SentenceTransformer, util
from transformers import AutoModel, AutoTokenizer
import re

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

    for item in vector_output:
        if item['similarity_score'] >= threshold:
            relavent_sentences.append(item['target_sentence'])
            reasons.append(f"Sentence is similar to topic above.")
        else:
            for keyword in keyword_list:
                if keyword.lower() in item['target_sentence'].lower():
                    relavent_sentences.append(item['target_sentence'])
                    reasons.append(f"Sentence contains keyword '{keyword}'.")
                    break
    return [relavent_sentences, reasons]
        
