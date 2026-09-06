import os
import sys
import argparse

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from backend.app.engine.ingestion import DataIngestor

def main():
    parser = argparse.ArgumentParser(description="Ingest Sentinel-2 datasets into IdeaX.")
    parser.add_argument("--mode", choices=["safe", "patch", "raw"], required=True, help="Ingestion mode: 'safe' for raw SAFE dirs, 'patch' for pre-cropped patch package, 'raw' for standalone JP2s")
    parser.add_argument("--dataset", type=str, default="mumbai", help="Dataset name to partition index/metadata. e.g., 'delhi', 'mumbai'")
    
    # Safe mode args
    parser.add_argument("--t1", type=str, help="Path to T1 SAFE directory")
    parser.add_argument("--t2", type=str, help="Path to T2 SAFE directory")
    parser.add_argument("--lat", type=float, help="Target latitude")
    parser.add_argument("--lon", type=float, help="Target longitude")
    parser.add_argument("--site", type=str, default="Unknown", help="Site name")
    parser.add_argument("--label", type=str, default="", help="Optional ground truth label")
    
    # Patch mode args
    parser.add_argument("--input", type=str, help="Path to pre-cropped patch package directory")
    
    args = parser.parse_args()
    
    ingestor = DataIngestor(dataset_name=args.dataset)
    
    if args.mode in ["safe", "raw"]:
        if not all([args.t1, args.t2, args.lat, args.lon]):
            print(f"Error: --t1, --t2, --lat, --lon are required for {args.mode} mode.")
            sys.exit(1)
        if args.mode == "safe":
            ingestor.ingest_safe_pair(args.t1, args.t2, args.lat, args.lon, args.site, args.label)
        elif args.mode == "raw":
            ingestor.ingest_raw_pair(args.t1, args.t2, args.lat, args.lon, args.site, args.label)
        
    elif args.mode == "patch":
        if not args.input:
            print("Error: --input is required for patch mode.")
            sys.exit(1)
        ingestor.ingest_patch_package(args.input)

if __name__ == "__main__":
    main()
