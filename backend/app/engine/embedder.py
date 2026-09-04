import os
import torch
from transformers import CLIPProcessor, CLIPVisionModelWithProjection
import onnxruntime as ort
import numpy as np
from PIL import Image

from dotenv import load_dotenv
load_dotenv()

class Embedder:
    def __init__(self, model_dir: str = None):
        if model_dir is None:
            local_ai = os.getenv("LOCAL_AI_DIR")
            if local_ai:
                model_dir = os.path.join(local_ai, "clip-vit-large-patch14")
            else:
                model_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "models", "clip-vit-large-patch14"))
        self.model_dir = model_dir
        
        if not os.path.exists(self.model_dir):
            raise FileNotFoundError(f"Model directory {self.model_dir} not found. Please run download_and_export_model.py first.")
        
        # Load processor (handles tokenization and image preprocessing)
        self.processor = CLIPProcessor.from_pretrained(self.model_dir, local_files_only=True)
        
        # Load vision model in FP16 to GPU (if available)
        print("Loading Vision Model (GPU/FP16)...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.vision_model = CLIPVisionModelWithProjection.from_pretrained(
            self.model_dir, 
            local_files_only=True,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
        ).to(self.device)
        self.vision_model.eval()
        
        # Load text model via ONNX runtime on CPU
        print("Loading Text Model (ONNX/CPU)...")
        onnx_path = os.path.join(self.model_dir, "text_model_with_projection.onnx")
        if not os.path.exists(onnx_path):
            raise FileNotFoundError(f"ONNX text model not found at {onnx_path}")
            
        self.text_session = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        
    def embed_text(self, text: str) -> np.ndarray:
        """Embeds text into a vector using the ONNX CPU runtime."""
        inputs = self.processor(text=[text], return_tensors="np", padding=True, truncation=True)
        
        ort_inputs = {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64)
        }
        
        outputs = self.text_session.run(None, ort_inputs)
        text_features = outputs[0]
        
        # Normalize
        text_features = text_features / np.linalg.norm(text_features, axis=-1, keepdims=True)
        return text_features[0]

    def embed_image(self, image: Image.Image) -> np.ndarray:
        """Embeds an image into a vector using the FP16 GPU model."""
        inputs = self.processor(images=image, return_tensors="pt")
        
        # Move to GPU and convert to proper dtype
        pixel_values = inputs.pixel_values.to(self.device, dtype=self.vision_model.dtype)
        
        with torch.no_grad():
            outputs = self.vision_model(pixel_values=pixel_values)
            image_features = outputs.image_embeds
            
            # Normalize
            image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
            
        return image_features.cpu().numpy()[0]
