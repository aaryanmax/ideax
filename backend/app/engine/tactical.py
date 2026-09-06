import numpy as np
from typing import Dict, Any

TACTICAL_CLASSES = [
    "paved asphalt road or military runway",
    "reinforced concrete bunker or prefabricated shelter",
    "earthen defensive berm or trench excavation",
    "cleared forest or deforested terrain",
    "parked heavy vehicles or mechanized convoy",
    "seasonal agricultural crop growth or barren ground"
]

class TacticalClassifier:
    def __init__(self, embedder):
        """
        Initializes the TacticalClassifier.
        Embeds the TACTICAL_CLASSES text prompts once at startup into text vectors.
        
        Args:
            embedder: An instance of Embedder that provides `embed_text`.
        """
        self.embedder = embedder
        self.classes = TACTICAL_CLASSES
        self.text_embeddings = self._precompute_text_embeddings()
        
    def _precompute_text_embeddings(self) -> np.ndarray:
        """
        Embeds all text prompts into a matrix of shape (num_classes, embedding_dim).
        The embeddings returned by embedder.embed_text are already normalized.
        """
        embeddings = []
        for cls_text in self.classes:
            emb = self.embedder.embed_text(cls_text)
            embeddings.append(emb)
        return np.array(embeddings)
        
    def classify(self, patch_embedding: np.ndarray, tau: float = 0.07) -> Dict[str, Any]:
        """
        Performs zero-shot tactical classification on an anomaly patch.
        
        Args:
            patch_embedding: The image embedding of the anomaly patch (1D numpy array).
                             Expected to be already normalized.
            tau: Temperature parameter for the softmax scaling.
            
        Returns:
            A dictionary containing the top prediction's classification and confidence.
        """
        # Ensure patch_embedding is a 1D array
        patch_embedding = patch_embedding.flatten()
        
        # Handle dimension mismatch (e.g. text is 768 but patch is 512)
        text_dim = self.text_embeddings.shape[1]
        if patch_embedding.shape[0] != text_dim:
            if patch_embedding.shape[0] > text_dim:
                patch_embedding = patch_embedding[:text_dim]
            else:
                patch_embedding = np.pad(patch_embedding, (0, text_dim - patch_embedding.shape[0]))
            norm = np.linalg.norm(patch_embedding)
            if norm > 0:
                patch_embedding = patch_embedding / norm
                
        # Calculate cosine similarities.
        # Since text_embeddings and patch_embedding are normalized L2 vectors, 
        # their dot product is equivalent to cosine similarity.
        # similarities shape: (num_classes,)
        similarities = np.dot(self.text_embeddings, patch_embedding)
        
        # Scale by temperature tau
        scaled_similarities = similarities / tau
        
        # Softmax computation
        # Subtract max for numerical stability before exp
        exp_sims = np.exp(scaled_similarities - np.max(scaled_similarities))
        probs = exp_sims / np.sum(exp_sims)
        
        # Get the top prediction
        top_idx = np.argmax(probs)
        
        distribution = {cls: float(p) for cls, p in zip(self.classes, probs)}
        
        return {
            "classification": self.classes[top_idx],
            "confidence": float(probs[top_idx]),
            "distribution": distribution
        }
