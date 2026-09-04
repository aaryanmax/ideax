import numpy as np
from scipy.spatial.distance import cosine
from typing import Dict, Any, Union

def evaluate_sfas_change(
    e_t1: Union[np.ndarray, list], 
    e_t2: Union[np.ndarray, list], 
    threshold: float = 0.15,
    scale: float = 1.0
) -> Dict[str, Any]:
    """
    Semantic False-Alarm Suppression (SFAS) Gate.
    Calculates the cosine similarity between vector embeddings of two tiles to determine
    if a fundamental change occurred, ignoring seasonal/phenological changes.
    
    Args:
        e_t1 (np.ndarray): Embedding vector for Tile T1 (e.g., Winter)
        e_t2 (np.ndarray): Embedding vector for Tile T2 (e.g., Summer)
        threshold (float): Threshold (tau) for the cosine distance.
        scale (float): Scaling factor for the confidence score.

    Returns:
        dict: A dictionary containing the suppression/change flags.
    """
    # Ensure numpy arrays
    v1 = np.asarray(e_t1, dtype=np.float32)
    v2 = np.asarray(e_t2, dtype=np.float32)

    # Scipy's cosine function calculates Cosine *Distance* (1 - cosine_similarity)
    # distance = 0 means identical (similarity 1)
    # distance = 2 means exactly opposite (similarity -1)
    distance = cosine(v1, v2)
    
    if distance > threshold:
        # Distance is high -> Similarity is low -> Confirmed Change
        return {
            "is_change": True,
            "confidence": float(distance * scale),
            "flag": "Confirmed Change"
        }
    else:
        # Distance is low -> Similarity is high -> Suppressed (e.g. just snow melting)
        return {
            "is_change": False,
            "reason": "Semantic similarity indicates environmental/phenological shift",
            "flag": "Suppressed"
        }
