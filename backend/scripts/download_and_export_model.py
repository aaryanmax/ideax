import os
import sys
import torch
from transformers import CLIPModel, CLIPProcessor
import argparse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv()

def get_default_save_dir() -> str:
    local_ai = os.getenv("LOCAL_AI_DIR")
    if local_ai:
        return os.path.join(local_ai, "clip-vit-large-patch14")
    # Portable fallback for any other system or repository clone
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "models", "clip-vit-large-patch14"))

def main():
    parser = argparse.ArgumentParser(description="Download and export CLIP model.")
    parser.add_argument("--model-id", type=str, default="openai/clip-vit-large-patch14", help="HuggingFace Model ID")
    parser.add_argument("--save-dir", type=str, default=get_default_save_dir(), help="Local directory to save the models")
    args = parser.parse_args()

    os.makedirs(args.save_dir, exist_ok=True)
    
    hf_token = os.getenv("HF_TOKEN")
    print(f"Downloading model {args.model_id}...")
    model = CLIPModel.from_pretrained(args.model_id, token=hf_token)
    processor = CLIPProcessor.from_pretrained(args.model_id, token=hf_token)
    
    print(f"Saving standard model and processor to {args.save_dir}...")
    model.save_pretrained(args.save_dir)
    processor.save_pretrained(args.save_dir)
    
    print("Exporting text encoder with projection to ONNX...")
    class TextEncoderWithProjection(torch.nn.Module):
        def __init__(self, clip_model):
            super().__init__()
            self.text_model = clip_model.text_model
            self.text_projection = clip_model.text_projection
            
        def forward(self, input_ids, attention_mask):
            text_outputs = self.text_model(input_ids=input_ids, attention_mask=attention_mask)
            pooled_output = text_outputs[1]
            text_features = self.text_projection(pooled_output)
            return text_features

    wrapper = TextEncoderWithProjection(model)
    wrapper.eval()
    
    # Dummy inputs for tracing
    dummy_text = processor(text=["a sample text"], return_tensors="pt", padding=True, truncation=True)
    input_ids = dummy_text.input_ids
    attention_mask = dummy_text.attention_mask
    
    onnx_path = os.path.join(args.save_dir, "text_model_with_projection.onnx")
    
    with torch.no_grad():
        torch.onnx.export(
            wrapper,
            (input_ids, attention_mask),
            onnx_path,
            export_params=True,
            opset_version=18,
            do_constant_folding=True,
            input_names=["input_ids", "attention_mask"],
            output_names=["text_features"],
            dynamic_axes={
                "input_ids": {0: "batch_size", 1: "sequence_length"},
                "attention_mask": {0: "batch_size", 1: "sequence_length"},
                "text_features": {0: "batch_size"}
            }
        )
        
    print(f"ONNX export successful: {onnx_path}")
    print("Model download and export complete. You can now use the model completely offline.")

if __name__ == "__main__":
    main()
