"""
shared_functions.py
This module contains shared functions used across multiple processing modules, primarily for semantic similarity analysis.
Sharing these functions not only reduces code duplication, but also ensures consistency.
It also allows the semantic similarity model to be initialized only once, improving startup time.
"""

# import os
# SKIP_LLM = os.getenv("SKIP_LLM") == "1" # Once implemented, allow skipping of LLM analysis to speed up testing and development.
SKIP_LLM = True  # Set to True to skip LLM semantic analysis until integration is complete


# Ollama model used to reduce false positives in semantic similarity analysis
# Model must be installed locally and available to Ollama.
#OLLAMA_MODEL = "gemma4:12b"
OLLAMA_MODEL = "qwen3.5:4b"

# Hugging Face text embedding model used for semantic similarity
# (Note: Changing this model may require adjustments to the similarity threshold and window size)
SIMILARITY_MODEL = "BAAI/bge-base-en-v1.5"

# Set global constants for similarity threshold and context window size
# Similarity threshold when a keyword is present in the sentence (medium confidence)
SIMILARITY_THRESHOLD: float = 0.5
# Similarity threshold when no keyword is present in the sentence (high confidence)
SIMILARITY_THRESHOLD_NO_KEYWORD: float = 0.6
WINDOW_SIZE: int = 1

from sentence_transformers import SentenceTransformer, util
import ollama

model = SentenceTransformer(SIMILARITY_MODEL)

def find_similar_sentences(sentences: str, topic_sentence: str, threshold: float = SIMILARITY_THRESHOLD) -> list:
    """
    Compare given text to a topic sentence and return sentences that are similar to the topic sentence.
    Input: text to search, topic sentence to compare against
    Output: list of dictionaries containing the target sentence, context window, and similarity score
    """

    # Compute the vectors for the sentences
    anchor_vector = model.encode(topic_sentence, convert_to_tensor=True, normalize_embeddings=True)
    sentence_vectors = model.encode(sentences, convert_to_tensor=True, normalize_embeddings=True)
    
    # Compute cosine similarities instantly using the built-in util function
    similarities = util.cos_sim(sentence_vectors, anchor_vector).squeeze(-1).tolist()
    
    matched_windows = []

    # Filter out sentences that are below the similarity threshold and create context windows for those that meet the threshold
    for idx, (sentence, score) in enumerate(zip(sentences, similarities)):
        if score >= threshold:
            start = max(0, idx - WINDOW_SIZE)
            end = min(len(sentences), idx + WINDOW_SIZE + 1)
            context = " ".join(sentences[start:end])
            
            matched_windows.append({
                "target_sentence": sentence,
                "context_window": context,
                "similarity_score": round(score, 3)
            })
            
    return matched_windows

def threshold_cut_or_keyword(vector_output, keyword_list, threshold=SIMILARITY_THRESHOLD_NO_KEYWORD):
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
    """
    Uses an LLM to analyze the filtered semantic matches and provide a final evaluation to reduce false positives.
    [Not yet implemented, will always be skipped at this time.]
    """

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
        return filtered_semantic_matches
    except Exception as e:
        print(f"Error processing batch: {e}")
        return filtered_semantic_matches