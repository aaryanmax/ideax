import numpy as np
from scipy.spatial.distance import cosine
from typing import Dict, Any, Union, Optional

def evaluate_sfas_change(
    e_t1: Union[np.ndarray, list], 
    e_t2: Union[np.ndarray, list], 
    threshold: float = 0.15,
    scale: float = 1.0,
    scl_result_t1: Optional[Dict[str, Any]] = None,
    scl_result_t2: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Semantic False-Alarm Suppression (SFAS) Gate.
    Calculates the cosine similarity between vector embeddings of two tiles to determine
    if a fundamental change occurred, ignoring seasonal/phenological changes.
    Also incorporates SCL hard-gating to suppress clouds, snow, and shadows.
    
    Args:
        e_t1 (np.ndarray): Embedding vector for Tile T1 (e.g., Winter)
        e_t2 (np.ndarray): Embedding vector for Tile T2 (e.g., Summer)
        threshold (float): Threshold (tau) for the cosine distance.
        scale (float): Scaling factor for the confidence score.
        scl_result_t1 (dict): Optional SCL analysis result for T1.
        scl_result_t2 (dict): Optional SCL analysis result for T2.

    Returns:
        dict: A dictionary containing the suppression/change flags.
    """
    scl_evidence = {"t1": scl_result_t1, "t2": scl_result_t2}
    
    # Hard Gate: SCL
    if scl_result_t2 and scl_result_t2.get("is_masked"):
        return {
            "is_change": False,
            "reason": scl_result_t2.get("suppression_reason", "Suppressed: SCL Mask"),
            "flag": scl_result_t2.get("suppression_reason", "Suppressed: SCL Mask"),
            "scl_evidence": scl_evidence
        }
    if scl_result_t1 and scl_result_t1.get("is_masked"):
        return {
            "is_change": False,
            "reason": scl_result_t1.get("suppression_reason", "Suppressed: SCL Mask (T1)"),
            "flag": scl_result_t1.get("suppression_reason", "Suppressed: SCL Mask (T1)"),
            "scl_evidence": scl_evidence
        }

    # Ensure numpy arrays
    v1 = np.asarray(e_t1, dtype=np.float32)
    v2 = np.asarray(e_t2, dtype=np.float32)

    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return {
            "is_change": False,
            "reason": "Suppressed: Zero embedding vector",
            "flag": "Suppressed: Zero Embedding",
            "scl_evidence": scl_evidence
        }

    # Scipy's cosine function calculates Cosine *Distance* (1 - cosine_similarity)
    # distance = 0 means identical (similarity 1)
    # distance = 2 means exactly opposite (similarity -1)
    distance = cosine(v1, v2)
    
    if distance > threshold:
        # Distance is high -> Similarity is low -> Confirmed Change
        return {
            "is_change": True,
            "confidence": float(distance * scale),
            "flag": "Confirmed Change",
            "scl_evidence": scl_evidence
        }
    else:
        # Distance is low -> Similarity is high -> Suppressed (e.g. just snow melting)
        return {
            "is_change": False,
            "reason": "Semantic similarity indicates environmental/phenological shift",
            "flag": "Suppressed: Semantic Phenology",
            "scl_evidence": scl_evidence
        }
