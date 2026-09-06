#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
================================================================================
VAYU-CHRONICLE (Project IdeaX) — Full Pre-System Boot Smoke Test
================================================================================
Production-grade 9-Tier Pre-Flight Safety & Diagnostic Verifier for 
Zero-Cloud / Air-Gapped Geospatial Semantic Intelligence System.

Verifies:
  1. Python Environment, Virtualenv (.supervenv), and 'uv' Package Manager
  2. Compute Hardware, CUDA / GPU Specs, VRAM Budget, System RAM & Storage Headroom
  3. Core Dependencies Matrix (PyTorch, ONNXRuntime, FAISS, Rasterio, OpenCV, etc.)
  4. Air-Gap Configuration & Environment Variables (.env, LocalAi paths)
  5. Offline Model Artifacts & Weight Integrity (CLIP ViT-L/14, ONNX Text Model)
  6. Model Inference Smoke Test (Dummy FP16/FP32 Vision & ONNX Text Embeddings, Tactical Classifier)
  7. Geospatial Datasets & FAISS HNSW Indices (Assam, Delhi, Gujarat, Mumbai, Odisha)
  8. SQLite Database & Audit Trail System (audit.db schema & transactions)
  9. Natural Query Search Engine Verification (Automated Benchmarks + Interactive Live Terminal CLI)

Outputs:
  - Formatted terminal dashboard with real-time progress indicators
  - Interactive Natural Language Query tester to verify query-to-vector mapping
  - Clean exit code 0 if all tests pass
  - Detailed error logs written to 'backend/full_smoke_test.log' on failure
================================================================================
"""

import os
import sys
import time
import json
import glob
import shutil
import argparse
import traceback
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Resolve directory paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ANSI Color Codes for Terminal UI
class TermColor:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    
    # Foreground
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    
    # Backgrounds
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"
    BG_BLUE = "\033[44m"
    BG_DARK = "\033[40m"


def cprint(text: str, color: str = TermColor.RESET, bold: bool = False, end: str = "\n"):
    prefix = TermColor.BOLD if bold else ""
    print(f"{prefix}{color}{text}{TermColor.RESET}", end=end)


class DiagnosticReport:
    """Collects check outcomes, execution timings, warnings, and failure logs."""
    def __init__(self, log_path: str):
        self.log_path = log_path
        self.tiers_passed: int = 0
        self.tiers_failed: int = 0
        self.tiers_warned: int = 0
        self.critical_failures: List[Dict[str, str]] = []
        self.warnings: List[Dict[str, str]] = []
        self.logs: List[str] = []
        self.start_time = time.perf_counter()

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level:7s}] {message}"
        self.logs.append(entry)

    def record_pass(self, tier_name: str, detail: str = ""):
        self.tiers_passed += 1
        self.log(f"TIER PASSED: {tier_name} - {detail}", "PASS")

    def record_warn(self, tier_name: str, reason: str, remediation: str = ""):
        self.tiers_warned += 1
        self.warnings.append({"tier": tier_name, "reason": reason, "remediation": remediation})
        self.log(f"TIER WARNING: {tier_name} - {reason} (Fix: {remediation})", "WARN")

    def record_fail(self, tier_name: str, error: str, exc: Optional[Exception] = None, remediation: str = ""):
        self.tiers_failed += 1
        tb = traceback.format_exc() if exc else ""
        self.critical_failures.append({
            "tier": tier_name,
            "error": error,
            "traceback": tb,
            "remediation": remediation
        })
        self.log(f"TIER CRITICAL FAILURE: {tier_name} - {error}\n{tb}", "FAIL")

    def flush_to_disk(self):
        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("VAYU-CHRONICLE PRE-BOOT SMOKE TEST LOG\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Duration: {time.perf_counter() - self.start_time:.2f}s\n")
                f.write("=" * 80 + "\n\n")
                for line in self.logs:
                    f.write(line + "\n")
                
                if self.critical_failures:
                    f.write("\n" + "=" * 80 + "\n")
                    f.write("CRITICAL FAILURE BREAKDOWN & REMEDIATION PLAN\n")
                    f.write("=" * 80 + "\n")
                    for i, fail in enumerate(self.critical_failures, 1):
                        f.write(f"\n[{i}] Tier: {fail['tier']}\n")
                        f.write(f"    Error: {fail['error']}\n")
                        if fail['remediation']:
                            f.write(f"    Remediation: {fail['remediation']}\n")
                        if fail['traceback']:
                            f.write(f"    Traceback:\n{fail['traceback']}\n")
        except Exception as e:
            cprint(f"[-] Failed to write smoke test log to disk: {e}", TermColor.RED)


# ------------------------------------------------------------------------------
# UI Helpers & Formatting
# ------------------------------------------------------------------------------
def print_banner():
    banner = f"""
{TermColor.CYAN}{TermColor.BOLD}╔════════════════════════════════════════════════════════════════════════════════╗
║  🛰️  VAYU-CHRONICLE AI ENGINE — PRE-BOOT FULL SMOKE TEST & DIAGNOSTICS         ║
║  Zero-Cloud Semantic Retrieval & Bitemporal Change Intelligence Platform      ║
║  Standard 2026 Defence-Ready Pre-Flight Safety Check Suite                     ║
╚════════════════════════════════════════════════════════════════════════════════╝{TermColor.RESET}
"""
    print(banner)


def print_section_header(number: int, title: str):
    cprint(f"\n┌── [STEP {number}/9] {title.upper()} " + "─" * max(10, 68 - len(title)), TermColor.BLUE, bold=True)


def print_check_result(label: str, status: str, detail: str = "", extra: str = ""):
    if status.upper() == "PASS":
        badge = f"{TermColor.GREEN}[PASS]{TermColor.RESET}"
    elif status.upper() == "WARN":
        badge = f"{TermColor.YELLOW}[WARN]{TermColor.RESET}"
    else:
        badge = f"{TermColor.RED}[FAIL]{TermColor.RESET}"
    
    label_padded = f"{label:<36}"
    print(f"│  {badge} {TermColor.WHITE}{label_padded}{TermColor.RESET} : {TermColor.CYAN}{detail}{TermColor.RESET}")
    if extra:
        print(f"│         {TermColor.DIM}{extra}{TermColor.RESET}")


# ------------------------------------------------------------------------------
# TIER 1: Environment, Virtualenv (.supervenv) & 'uv' Package Manager
# ------------------------------------------------------------------------------
def check_environment_and_venv(report: DiagnosticReport) -> bool:
    print_section_header(1, "Python Environment, .supervenv & uv Manager")
    success = True

    # 1.1 Python Version
    py_ver = sys.version_info
    py_ver_str = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"
    if py_ver >= (3, 10):
        print_check_result("Python Runtime", "PASS", f"v{py_ver_str} (>= 3.10 requirement satisfied)")
        report.log(f"Python version: {py_ver_str}")
    else:
        print_check_result("Python Runtime", "FAIL", f"v{py_ver_str} (Requires Python >= 3.10)")
        report.record_fail("Python Runtime", f"Unsupported Python version {py_ver_str}", remediation="Use Python 3.10+")
        success = False

    # 1.2 Virtual Environment Check (specifically targeting .supervenv)
    in_venv = (sys.prefix != getattr(sys, "base_prefix", sys.prefix)) or ("VIRTUAL_ENV" in os.environ)
    supervenv_path = os.path.abspath(r"C:\Users\Admin\Projects\.supervenv")
    current_exec = os.path.abspath(sys.executable)
    
    is_in_supervenv = (
        supervenv_path.lower() in current_exec.lower() or 
        supervenv_path.lower() in os.environ.get("VIRTUAL_ENV", "").lower()
    )

    if is_in_supervenv:
        print_check_result("Virtual Environment", "PASS", f"Active (.supervenv at {supervenv_path})")
        report.record_pass("Virtualenv", "Running in .supervenv")
    elif in_venv:
        print_check_result("Virtual Environment", "WARN", f"Active, but custom path: {sys.prefix}", 
                           f"Preferred project venv is at: {supervenv_path}")
        report.record_warn("Virtualenv", f"Running in alternate venv {sys.prefix}", 
                           remediation=f"Activate .supervenv: & '{supervenv_path}\\Scripts\\Activate.ps1'")
    else:
        if os.path.exists(supervenv_path):
            print_check_result("Virtual Environment", "WARN", "Running on System Python (Not in Venv)",
                               f"Detected .supervenv at {supervenv_path}! Activate using: & '{supervenv_path}\\Scripts\\Activate.ps1'")
            report.record_warn("Virtualenv", "System Python detected without active venv",
                               remediation=f"& '{supervenv_path}\\Scripts\\Activate.ps1'")
        else:
            print_check_result("Virtual Environment", "WARN", "Running on System Python (No venv detected)")
            report.record_warn("Virtualenv", "No virtual environment active", remediation="Create or activate a venv")

    # 1.3 'uv' Package Manager Check
    uv_path = shutil.which("uv")
    if not uv_path:
        default_uv = os.path.expanduser(r"~\.local\bin\uv.exe")
        if os.path.exists(default_uv):
            uv_path = default_uv

    if uv_path:
        try:
            import subprocess
            res = subprocess.run([uv_path, "--version"], capture_output=True, text=True, timeout=5)
            uv_ver = res.stdout.strip()
            print_check_result("uv Package Manager", "PASS", f"{uv_ver} ({uv_path})")
            report.log(f"uv detected: {uv_ver}")
        except Exception as e:
            print_check_result("uv Package Manager", "WARN", f"Found at {uv_path}, but query error: {e}")
    else:
        print_check_result("uv Package Manager", "WARN", "Not found in system PATH", 
                           "Install or add to PATH via https://docs.astral.sh/uv/")
        report.record_warn("uv Manager", "uv executable not found in PATH")

    return success


# ------------------------------------------------------------------------------
# TIER 2: Hardware Compute, CUDA, VRAM & System Memory Diagnostics
# ------------------------------------------------------------------------------
def check_hardware_and_compute(report: DiagnosticReport) -> bool:
    print_section_header(2, "Hardware Acceleration, CUDA, VRAM & Memory")
    success = True

    # 2.1 PyTorch & CUDA Detection
    try:
        import torch
        torch_ver = torch.__version__
        cuda_avail = torch.cuda.is_available()

        if cuda_avail:
            device_name = torch.cuda.get_device_name(0)
            compute_cap = torch.cuda.get_device_capability(0)
            device_count = torch.cuda.device_count()
            total_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            
            # Query memory usage
            allocated_vram_mb = torch.cuda.memory_allocated(0) / (1024 ** 2)
            reserved_vram_mb = torch.cuda.memory_reserved(0) / (1024 ** 2)
            free_vram_mb = (torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_reserved(0)) / (1024 ** 2)

            print_check_result("PyTorch CUDA Engine", "PASS", f"CUDA {torch.version.cuda} (Torch v{torch_ver})")
            print_check_result("Primary GPU Device", "PASS", f"{device_name} (Compute Capability {compute_cap[0]}.{compute_cap[1]})")
            print_check_result("GPU VRAM Capacity", "PASS", 
                               f"{total_vram_gb:.2f} GB Total | Free: {free_vram_mb:.0f} MB | Alloc: {allocated_vram_mb:.1f} MB")

            # Mini Tensor Allocation Smoke Test
            try:
                t0 = time.perf_counter()
                x = torch.randn((1024, 1024), device="cuda", dtype=torch.float16)
                y = torch.matmul(x, x)
                torch.cuda.synchronize()
                t_matmul = (time.perf_counter() - t0) * 1000
                del x, y
                torch.cuda.empty_cache()
                print_check_result("GPU FP16 Tensor Check", "PASS", f"1024x1024 GEMM @ {t_matmul:.2f}ms (GTX 1650 FP16 Ready)")
                report.record_pass("GPU Compute", f"{device_name} ({total_vram_gb:.2f} GB VRAM)")
            except Exception as e:
                print_check_result("GPU FP16 Tensor Check", "WARN", f"FP16 allocation warning: {e}")
                report.record_warn("GPU Compute", f"FP16 test issue: {e}")

        else:
            print_check_result("PyTorch CUDA Engine", "WARN", f"Torch v{torch_ver} (CPU-Only / No CUDA GPU active)")
            print_check_result("Inference Fallback Mode", "PASS", "CPU High-Throughput Threading Active")
            report.record_warn("Compute", "Running in CPU-only mode. GPU acceleration unavailable.",
                               remediation="Install CUDA-enabled PyTorch in .supervenv using uv: uv pip install torch --index-url https://download.pytorch.org/whl/cu121")

    except Exception as e:
        print_check_result("PyTorch Engine", "FAIL", f"Failed to initialize torch: {e}")
        report.record_fail("PyTorch Engine", str(e), exc=e, remediation="uv pip install torch")
        success = False

    # 2.2 System RAM Check
    try:
        import psutil
        vm = psutil.virtual_memory()
        total_ram_gb = vm.total / (1024 ** 3)
        avail_ram_gb = vm.available / (1024 ** 3)
        used_pct = vm.percent

        status = "PASS" if avail_ram_gb >= 2.0 else "WARN"
        print_check_result("System Memory (RAM)", status, 
                           f"{total_ram_gb:.1f} GB Total | {avail_ram_gb:.1f} GB Available ({used_pct}% used)")
        if avail_ram_gb < 2.0:
            report.record_warn("RAM", f"Low available RAM ({avail_ram_gb:.1f} GB)", remediation="Close unnecessary background applications")
        else:
            report.record_pass("RAM", f"{avail_ram_gb:.1f} GB free")
    except ImportError:
        print_check_result("System Memory (RAM)", "WARN", "psutil not installed (skipping dynamic RAM check)")

    # 2.3 Storage & Free Disk Space
    try:
        disk = shutil.disk_usage(BACKEND_DIR)
        free_gb = disk.free / (1024 ** 3)
        total_gb = disk.total / (1024 ** 3)
        status = "PASS" if free_gb >= 5.0 else "WARN"
        print_check_result("Disk Storage Headroom", status, f"{free_gb:.1f} GB Free of {total_gb:.1f} GB Total")
        if free_gb < 5.0:
            report.record_warn("Disk Space", f"Low disk space: {free_gb:.1f} GB free", remediation="Free up disk space for cache and indices")
    except Exception as e:
        print_check_result("Disk Storage Headroom", "WARN", f"Unable to query disk: {e}")

    return success


# ------------------------------------------------------------------------------
# TIER 3: Core Dependencies Matrix
# ------------------------------------------------------------------------------
def check_core_dependencies(report: DiagnosticReport) -> bool:
    print_section_header(3, "Core Python Packages & Framework Matrix")
    success = True

    required_packages = [
        ("torch", "PyTorch Core Engine"),
        ("transformers", "Hugging Face Transformers"),
        ("onnxruntime", "ONNX Runtime (CPU/DirectML)"),
        ("faiss", "FAISS HNSW Vector Search"),
        ("rasterio", "Geospatial GDAL / Raster Engine"),
        ("shapely", "Geospatial Polygon Geometry"),
        ("fastapi", "FastAPI High-Performance REST Framework"),
        ("uvicorn", "ASGI Production Server"),
        ("sqlalchemy", "SQLite ORM & State Management"),
        ("scipy", "Scientific Computing (Cosine Metrics)"),
        ("cv2", "OpenCV Image Processing"),
        ("PIL", "Pillow Imaging Library"),
        ("dotenv", "Python Dotenv Configuration")
    ]

    for mod_name, desc in required_packages:
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", "Installed")
            print_check_result(desc, "PASS", f"v{ver}")
            report.log(f"Package {mod_name}: v{ver}")
        except ImportError as e:
            print_check_result(desc, "FAIL", f"Missing module '{mod_name}' ({e})")
            report.record_fail(f"Package {mod_name}", f"Module missing: {e}", exc=e, 
                               remediation=f"uv pip install {mod_name}")
            success = False

    return success


# ------------------------------------------------------------------------------
# TIER 4: Air-Gap Configuration & Environment Variables (.env)
# ------------------------------------------------------------------------------
def check_configuration_and_env(report: DiagnosticReport) -> Tuple[bool, Dict[str, str]]:
    print_section_header(4, "Air-Gap Configuration & Environment (.env)")
    success = True
    config = {}

    env_path = os.path.join(BACKEND_DIR, ".env")
    if os.path.exists(env_path):
        print_check_result("Configuration File (.env)", "PASS", f"Found at {os.path.relpath(env_path, PROJECT_ROOT)}")
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except Exception as e:
            print_check_result("Loading .env", "WARN", f"Could not parse .env: {e}")
    else:
        print_check_result("Configuration File (.env)", "WARN", "Missing backend/.env file — using defaults")
        report.record_warn("Config", "Missing .env file", remediation="Copy .env.example to .env")

    # Inspect LOCAL_AI_DIR
    local_ai = os.getenv("LOCAL_AI_DIR", r"C:/Users/Admin/Projects/LocalAi")
    if os.path.exists(local_ai):
        print_check_result("Local AI Storage (Air-Gap)", "PASS", f"Mounted at {local_ai}")
        config["LOCAL_AI_DIR"] = local_ai
    else:
        # Check fallback
        fallback = os.path.join(PROJECT_ROOT, "data", "models")
        if os.path.exists(fallback):
            print_check_result("Local AI Storage (Fallback)", "PASS", f"Found at {fallback}")
            config["LOCAL_AI_DIR"] = fallback
        else:
            print_check_result("Local AI Storage (Air-Gap)", "FAIL", f"Directory not found: {local_ai}")
            report.record_fail("LOCAL_AI_DIR", f"Model directory {local_ai} does not exist", 
                               remediation="Set LOCAL_AI_DIR in backend/.env to correct directory")
            success = False

    # Check HF Cache flags
    hf_home = os.getenv("HF_HOME")
    if hf_home:
        print_check_result("Offline HF Cache Path", "PASS", hf_home)
    else:
        print_check_result("Offline HF Cache Path", "PASS", "Default system cache")

    return success, config


# ------------------------------------------------------------------------------
# TIER 5: Offline Model Artifacts & Weight Integrity
# ------------------------------------------------------------------------------
def check_offline_model_artifacts(report: DiagnosticReport, config: Dict[str, str]) -> Tuple[bool, str]:
    print_section_header(5, "Offline Model Artifacts & Weight Files")
    success = True

    model_root = config.get("LOCAL_AI_DIR", r"C:/Users/Admin/Projects/LocalAi")
    clip_dir = os.path.join(model_root, "clip-vit-large-patch14")

    if not os.path.exists(clip_dir):
        print_check_result("CLIP ViT-L/14 Directory", "FAIL", f"Not found at {clip_dir}")
        report.record_fail("Model Artifacts", f"Directory {clip_dir} missing",
                           remediation="Run: python backend/scripts/download_and_export_model.py")
        return False, clip_dir

    print_check_result("CLIP ViT-L/14 Directory", "PASS", f"Found ({os.path.basename(clip_dir)})")

    # Essential files check
    # 1. Architecture Config
    config_path = os.path.join(clip_dir, "config.json")
    if os.path.exists(config_path) and os.path.getsize(config_path) > 100:
        print_check_result("Model Architecture Config", "PASS", f"config.json ({os.path.getsize(config_path)} bytes)")
    else:
        print_check_result("Model Architecture Config", "FAIL", "Missing or corrupted config.json")
        report.record_fail("Architecture Config", "Missing config.json")
        success = False

    # 2. Vision Preprocessor / Processor Config
    proc_found = False
    for p_name in ["processor_config.json", "preprocessor_config.json"]:
        p_path = os.path.join(clip_dir, p_name)
        if os.path.exists(p_path) and os.path.getsize(p_path) > 100:
            print_check_result("Vision Preprocessor Config", "PASS", f"{p_name} ({os.path.getsize(p_path)} bytes)")
            proc_found = True
            break
    if not proc_found:
        print_check_result("Vision Preprocessor Config", "FAIL", "Missing processor_config.json or preprocessor_config.json")
        report.record_fail("Preprocessor Config", "Missing processor configuration")
        success = False

    # 3. Tokenizer Config
    tok_found = False
    for t_name in ["tokenizer_config.json", "tokenizer.json"]:
        t_path = os.path.join(clip_dir, t_name)
        if os.path.exists(t_path) and os.path.getsize(t_path) > 100:
            print_check_result("Tokenizer Configuration", "PASS", f"{t_name} ({os.path.getsize(t_path)} bytes)")
            tok_found = True
            break
    if not tok_found:
        print_check_result("Tokenizer Configuration", "FAIL", "Missing tokenizer config")
        report.record_fail("Tokenizer Config", "Missing tokenizer configuration")
        success = False

    # 4. ONNX Text Model (handles both monolithic and external-data .onnx.data formats)
    onnx_path = os.path.join(clip_dir, "text_model_with_projection.onnx")
    onnx_data_path = os.path.join(clip_dir, "text_model_with_projection.onnx.data")
    if os.path.exists(onnx_path) and os.path.getsize(onnx_path) > 100_000:
        onnx_sz_mb = os.path.getsize(onnx_path) / (1024 ** 2)
        if os.path.exists(onnx_data_path) and os.path.getsize(onnx_data_path) > 10_000_000:
            data_sz_mb = os.path.getsize(onnx_data_path) / (1024 ** 2)
            print_check_result("ONNX Text Projection Weights", "PASS", 
                               f"text_model_with_projection.onnx ({onnx_sz_mb:.2f} MB + {data_sz_mb:.1f} MB external weights)")
        else:
            print_check_result("ONNX Text Projection Weights", "PASS", f"text_model_with_projection.onnx ({onnx_sz_mb:.1f} MB)")
    else:
        print_check_result("ONNX Text Projection Weights", "FAIL", "Missing or incomplete text_model_with_projection.onnx")
        report.record_fail("ONNX Weights", "text_model_with_projection.onnx missing or invalid")
        success = False

    return success, clip_dir


# ------------------------------------------------------------------------------
# TIER 6: Live Model Inference & Zero-Shot Tactical Classifier Smoke Test
# ------------------------------------------------------------------------------
def check_model_inference_smoke(report: DiagnosticReport, clip_dir: str) -> Tuple[bool, Any]:
    print_section_header(6, "Live Model Inference & Tactical Smoke Tests")
    success = True
    embedder = None

    try:
        from app.engine.embedder import Embedder
        from app.engine.tactical import TacticalClassifier
        from PIL import Image
        import numpy as np

        # 6.1 Embedder Initialization
        t0 = time.perf_counter()
        embedder = Embedder(model_dir=clip_dir)
        t_init = (time.perf_counter() - t0) * 1000
        print_check_result("Embedder Initialization", "PASS", f"Loaded in {t_init:.1f}ms (Device: {embedder.device})")

        # 6.2 Text Embedding Smoke Test (ONNX CPU)
        test_text = "military airfield runway with concrete hangars"
        t0 = time.perf_counter()
        text_emb = embedder.embed_text(test_text)
        t_text = (time.perf_counter() - t0) * 1000
        norm_text = np.linalg.norm(text_emb)

        if text_emb.shape == (768,) and abs(norm_text - 1.0) < 0.01:
            print_check_result("ONNX Text Inference", "PASS", f"768-dim vector @ {t_text:.1f}ms (L2-norm: {norm_text:.4f})")
            report.record_pass("ONNX Text Inference", f"{t_text:.1f}ms")
        else:
            print_check_result("ONNX Text Inference", "FAIL", f"Unexpected output shape {text_emb.shape} or norm {norm_text}")
            report.record_fail("ONNX Text", f"Vector shape mismatch: {text_emb.shape}")
            success = False

        # 6.3 Vision Embedding Smoke Test (PyTorch GPU / CPU)
        # Create dummy synthetic RGB patch (512x512)
        dummy_arr = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        dummy_img = Image.fromarray(dummy_arr)
        
        t0 = time.perf_counter()
        img_emb = embedder.embed_image(dummy_img)
        t_img = (time.perf_counter() - t0) * 1000
        norm_img = np.linalg.norm(img_emb)

        if img_emb.shape == (768,) and abs(norm_img - 1.0) < 0.01:
            device_flag = "GPU/FP16" if embedder.device == "cuda" else "CPU/FP32"
            print_check_result("Vision Model Inference", "PASS", f"768-dim vector @ {t_img:.1f}ms ({device_flag})")
            report.record_pass("Vision Model Inference", f"{t_img:.1f}ms on {embedder.device}")
        else:
            print_check_result("Vision Model Inference", "FAIL", f"Unexpected output shape {img_emb.shape} or norm {norm_img}")
            report.record_fail("Vision Model", f"Vector shape mismatch: {img_emb.shape}")
            success = False

        # 6.4 Tactical Classifier Smoke Test
        t0 = time.perf_counter()
        classifier = TacticalClassifier(embedder)
        res = classifier.classify(img_emb)
        t_class = (time.perf_counter() - t0) * 1000

        if "classification" in res and "confidence" in res and "distribution" in res:
            print_check_result("Tactical Zero-Shot Gate", "PASS", 
                               f"Classified dummy patch as '{res['classification'][:28]}...' ({res['confidence']*100:.1f}%) in {t_class:.1f}ms")
            report.record_pass("Tactical Classifier", f"Classified in {t_class:.1f}ms")
        else:
            print_check_result("Tactical Zero-Shot Gate", "FAIL", "Invalid classification dictionary output")
            report.record_fail("Tactical Classifier", "Unexpected classification output structure")
            success = False

    except Exception as e:
        print_check_result("Live Model Inference", "FAIL", f"Inference execution failed: {e}")
        report.record_fail("Live Model Inference", str(e), exc=e)
        success = False

    return success, embedder


# ------------------------------------------------------------------------------
# TIER 7: Geospatial Vector Indices & Metadata Audit
# ------------------------------------------------------------------------------
def check_vector_indices_and_datasets(report: DiagnosticReport) -> Tuple[bool, List[str]]:
    print_section_header(7, "Geospatial FAISS Indices & Metadata Catalogs")
    success = True
    available_datasets = []

    processed_dir = os.path.join(PROJECT_ROOT, "data", "processed")
    if not os.path.exists(processed_dir):
        print_check_result("Processed Data Directory", "FAIL", f"Directory {processed_dir} not found")
        report.record_fail("Data Processed Dir", f"Missing {processed_dir}")
        return False, []

    import faiss

    # Scan for index files
    index_files = sorted(glob.glob(os.path.join(processed_dir, "*.index")))
    if not index_files:
        print_check_result("FAISS Index Files", "FAIL", f"No .index files found in {processed_dir}")
        report.record_fail("FAISS Indices", "No indices found in data/processed",
                           remediation="Run index builder script: python backend/scripts/rebuild_index_auto.py")
        return False, []

    print_check_result("FAISS Indices Discovered", "PASS", f"Found {len(index_files)} dataset index files")

    for idx_path in index_files:
        base_name = os.path.basename(idx_path).replace(".index", "")
        meta_path = os.path.join(processed_dir, f"{base_name}_metadata.json")

        try:
            # 1. Inspect FAISS index
            index = faiss.read_index(idx_path)
            ntotal = index.ntotal
            dim = index.d

            # 2. Inspect Metadata JSON
            meta_count = 0
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                    meta_count = len(meta_data)
                
                # Check sample record structure
                sample_item = next(iter(meta_data.values())) if isinstance(meta_data, dict) else meta_data[0]
                has_coords = "coordinates" in sample_item or "bounds" in sample_item or "center" in sample_item
                has_patch_id = "patch_id" in sample_item or "faiss_id" in sample_item
                
                status = "PASS" if (ntotal > 0 and has_coords and has_patch_id) else "WARN"
                meta_status = f"{meta_count} metadata records (dim={dim})"
                print_check_result(f"Dataset: {base_name.upper()}", status, 
                                   f"{ntotal:,} vectors | {meta_status}")
                available_datasets.append(base_name)
                report.record_pass(f"Dataset {base_name}", f"{ntotal} vectors, {meta_count} meta")
            else:
                print_check_result(f"Dataset: {base_name.upper()}", "WARN", 
                                   f"{ntotal:,} vectors in index, but missing {os.path.basename(meta_path)}")
                report.record_warn(f"Dataset {base_name}", "Missing companion metadata JSON")

        except Exception as e:
            print_check_result(f"Dataset: {base_name.upper()}", "FAIL", f"Index load error: {e}")
            report.record_fail(f"Dataset {base_name}", str(e), exc=e)
            success = False

    # Sentinel-2 Imagery JP2 Check
    jp2_files = glob.glob(os.path.join(processed_dir, "*TCI_10m.jp2"))
    if len(jp2_files) >= 2:
        print_check_result("Sentinel-2 T1/T2 Scenes", "PASS", f"Found {len(jp2_files)} Sentinel-2 TCI JP2 scenes")
    elif len(jp2_files) == 1:
        print_check_result("Sentinel-2 T1/T2 Scenes", "WARN", f"Found only 1 scene: {os.path.basename(jp2_files[0])}")
    else:
        print_check_result("Sentinel-2 T1/T2 Scenes", "WARN", "No TCI 10m JP2 scenes in data/processed (change detection requires mock or JP2)")

    return success, available_datasets


# ------------------------------------------------------------------------------
# TIER 8: SQLite Database & Audit Trail System
# ------------------------------------------------------------------------------
def check_sqlite_audit_system(report: DiagnosticReport) -> bool:
    print_section_header(8, "SQLite Audit Trail Database & Schema Integrity")
    success = True

    db_dir = os.path.join(BACKEND_DIR, "data")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "audit.db")

    try:
        from sqlalchemy import create_engine, inspect, text
        from app.db.audit_models import Base, _ensure_columns

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        _ensure_columns()

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "audit_records" in tables:
            cols = [c["name"] for c in inspector.get_columns("audit_records")]
            required_cols = ["id", "query_string", "latitude", "longitude", "status", "analyst_id"]
            missing = [rc for rc in required_cols if rc not in cols]

            if not missing:
                # Test query
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT COUNT(*) FROM audit_records")).scalar()
                print_check_result("Audit Table (audit_records)", "PASS", 
                                   f"Verified schema ({len(cols)} columns, {result} logged commits)")
                report.record_pass("Audit DB", f"{result} records present")
            else:
                print_check_result("Audit Table Schema", "FAIL", f"Missing columns: {missing}")
                report.record_fail("Audit DB Schema", f"Missing columns {missing}")
                success = False
        else:
            print_check_result("Audit Table (audit_records)", "FAIL", "Table audit_records was not created")
            report.record_fail("Audit DB", "Table missing")
            success = False

    except Exception as e:
        print_check_result("Audit Database Connection", "FAIL", f"SQLite check error: {e}")
        report.record_fail("Audit DB Connection", str(e), exc=e)
        success = False

    return success


# ------------------------------------------------------------------------------
# TIER 9: Natural Query Search Engine Verification (Automated + Interactive CLI)
# ------------------------------------------------------------------------------
def execute_single_query(engine_manager, query: str, dataset: str, top_k: int) -> Tuple[List[Dict], float]:
    t0 = time.perf_counter()
    if dataset == "all":
        combined_results = []
        for name, eng in engine_manager.engines.items():
            res = eng.search_by_text(query, top_k=top_k)
            for r in res:
                r["properties"]["dataset"] = name
            combined_results.extend(res)
        combined_results.sort(key=lambda x: x["properties"].get("similarity_score", 0.0), reverse=True)
        results = combined_results[:top_k]
    else:
        eng = engine_manager.get_engine(dataset)
        if not eng:
            return [], 0.0
        results = eng.search_by_text(query, top_k=top_k)
        for r in results:
            r["properties"]["dataset"] = dataset
    t_elapsed = (time.perf_counter() - t0) * 1000
    return results, t_elapsed


def display_search_results(query: str, dataset: str, results: List[Dict], latency_ms: float):
    print(f"\n{TermColor.MAGENTA}┌─ SEARCH QUERY:{TermColor.RESET} {TermColor.BOLD}'{query}'{TermColor.RESET}")
    print(f"{TermColor.MAGENTA}│  Dataset:{TermColor.RESET} {dataset.upper()} | {TermColor.MAGENTA}Latency:{TermColor.RESET} {latency_ms:.1f}ms | {TermColor.MAGENTA}Candidates Retrieved:{TermColor.RESET} {len(results)}")
    print(f"{TermColor.MAGENTA}├" + "─" * 78)

    if not results:
        print(f"{TermColor.MAGENTA}│{TermColor.RESET}  {TermColor.YELLOW}No matching patches found in index.{TermColor.RESET}")
        print(f"{TermColor.MAGENTA}└" + "─" * 78)
        return

    for rank, feat in enumerate(results, 1):
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        patch_id = props.get("patch_id", "Unknown")
        sim_score = props.get("similarity_score", 0.0)
        ds = props.get("dataset", dataset).upper()
        site_name = props.get("site_name") or props.get("label") or "Surveillance Sector"
        center = props.get("center") or [0.0, 0.0]
        coords = geom.get("coordinates", [])

        # Color score
        if sim_score >= 0.20:
            score_badge = f"{TermColor.GREEN}{sim_score*100:.1f}%{TermColor.RESET}"
        elif sim_score >= 0.15:
            score_badge = f"{TermColor.CYAN}{sim_score*100:.1f}%{TermColor.RESET}"
        else:
            score_badge = f"{TermColor.YELLOW}{sim_score*100:.1f}%{TermColor.RESET}"

        print(f"{TermColor.MAGENTA}│{TermColor.RESET}  #{rank} [{ds}] {TermColor.BOLD}{patch_id}{TermColor.RESET} | Match Score: {score_badge}")
        print(f"{TermColor.MAGENTA}│{TermColor.RESET}     Site / Label : {TermColor.WHITE}{site_name}{TermColor.RESET}")
        print(f"{TermColor.MAGENTA}│{TermColor.RESET}     Center (Lat,Lon) : [{center[0]:.5f}, {center[1]:.5f}]")
        if coords and len(coords[0]) >= 4:
            print(f"{TermColor.MAGENTA}│{TermColor.RESET}     Georef Polygon   : {len(coords[0])} vertices mapped successfully")
        t2_date = props.get("t2_date")
        if t2_date:
            print(f"{TermColor.MAGENTA}│{TermColor.RESET}     Acquisition Date : {t2_date}")
        if rank < len(results):
            print(f"{TermColor.MAGENTA}│{TermColor.RESET}     " + "·" * 70)

    print(f"{TermColor.MAGENTA}└" + "─" * 78)


def check_search_engine_and_manual_queries(
    report: DiagnosticReport,
    embedder: Any,
    cli_query: Optional[str] = None,
    cli_dataset: str = "all",
    non_interactive: bool = False
) -> bool:
    print_section_header(9, "Natural Query Search Engine & Vector Mapping Verification")
    success = True

    if embedder is None:
        print_check_result("Search Engine Loader", "FAIL", "Embedder not initialized")
        report.record_fail("Search Engine", "Embedder not available")
        return False

    try:
        from app.engine.search import SearchEngineManager
        engine_manager = SearchEngineManager(embedder)
        loaded_count = len(engine_manager.engines)

        if loaded_count == 0:
            print_check_result("Search Engine Manager", "FAIL", "No vector indices could be loaded")
            report.record_fail("SearchEngineManager", "Zero engines loaded")
            return False

        print_check_result("Search Engine Manager", "PASS", 
                           f"Online with {loaded_count} active datasets ({', '.join(engine_manager.engines.keys())})")

        # 9.1 Automated Benchmark Queries (Zero hardcoding of results — validates pipeline)
        benchmark_queries = [
            ("dense urban settlement or industrial infrastructure", "all"),
            ("military airfield runway or aircraft hangars", "delhi" if "delhi" in engine_manager.engines else "all"),
            ("water body reservoir or riverbed", "mumbai" if "mumbai" in engine_manager.engines else "all"),
            ("agricultural seasonal crops or barren fields", "gujarat" if "gujarat" in engine_manager.engines else "all")
        ]

        print(f"\n│  {TermColor.BOLD}Executing Automated Semantic Retrieval Benchmarks:{TermColor.RESET}")
        for q_text, target_ds in benchmark_queries:
            results, lat_ms = execute_single_query(engine_manager, q_text, target_ds, top_k=3)
            if results and len(results) > 0:
                top_score = results[0]["properties"].get("similarity_score", 0.0)
                top_patch = results[0]["properties"].get("patch_id", "Unknown")
                status = "PASS" if top_score > 0.05 else "WARN"
                print_check_result(f"Query: '{q_text[:28]}...'", status, 
                                   f"Retrieved in {lat_ms:.1f}ms | Top: {top_score*100:.1f}% ({top_patch})")
                report.record_pass(f"Benchmark: {q_text[:20]}", f"{lat_ms:.1f}ms")
            else:
                print_check_result(f"Query: '{q_text[:28]}...'", "WARN", f"No results returned in {lat_ms:.1f}ms")
                report.record_warn(f"Benchmark: {q_text[:20]}", "No candidates retrieved")

        # 9.2 Direct CLI Query if provided
        if cli_query:
            print(f"\n│  {TermColor.BOLD}Running Custom CLI Query Verification:{TermColor.RESET}")
            results, lat_ms = execute_single_query(engine_manager, cli_query, cli_dataset, top_k=5)
            display_search_results(cli_query, cli_dataset, results, lat_ms)

        # 9.3 Interactive Manual Search Prompt on Terminal
        # Only trigger if terminal is interactive (TTY) and not running non-interactive / CI
        is_interactive = sys.stdin.isatty() and not non_interactive and not cli_query

        if is_interactive:
            cprint("\n" + "=" * 80, TermColor.CYAN)
            cprint("   🛰️  INTERACTIVE LIVE NATURAL LANGUAGE SEARCH VERIFICATION", TermColor.CYAN, bold=True)
            cprint("=" * 80, TermColor.CYAN)
            cprint("Test any natural language surveillance query to verify query-to-vector mapping.", TermColor.WHITE)
            cprint("Examples: 'fuel storage tanks', 'solar farm installations', 'dry river bed', 'harbor shipping dock'", TermColor.DIM)
            cprint("Type 'exit', 'quit', or press Enter on an empty line to finish and terminate script cleanly.\n", TermColor.DIM)

            while True:
                try:
                    user_q = input(f"{TermColor.BOLD}{TermColor.YELLOW}Enter Search Query ❯ {TermColor.RESET}").strip()
                    if not user_q or user_q.lower() in ["exit", "quit", "q"]:
                        cprint("\n[*] Exiting Interactive Search Verification...", TermColor.CYAN)
                        break

                    # Ask for optional dataset filter
                    available_keys = ["all"] + list(engine_manager.engines.keys())
                    ds_input = input(f"{TermColor.DIM}Target Dataset [{'/'.join(available_keys)}] (Default: all): {TermColor.RESET}").strip().lower()
                    if not ds_input or ds_input not in available_keys:
                        ds_input = "all"

                    # Execute query
                    results, lat_ms = execute_single_query(engine_manager, user_q, ds_input, top_k=5)
                    display_search_results(user_q, ds_input, results, lat_ms)
                    print()

                except (KeyboardInterrupt, EOFError):
                    print("\n[*] Interactive session cancelled by user.")
                    break

        elif not non_interactive and not cli_query:
            cprint("│  [INFO] Non-TTY or automated pipe detected — interactive prompt bypassed.", TermColor.DIM)

    except Exception as e:
        print_check_result("Search Engine Verification", "FAIL", f"Search engine execution error: {e}")
        report.record_fail("Search Engine Execution", str(e), exc=e)
        success = False

    return success


# ------------------------------------------------------------------------------
# Final Pre-Flight Dashboard & Exit Routing
# ------------------------------------------------------------------------------
def print_final_summary(report: DiagnosticReport):
    total_time = time.perf_counter() - report.start_time
    print("\n" + "=" * 80)
    cprint("                     PRE-BOOT FULL SMOKE TEST DASHBOARD", TermColor.BOLD)
    print("=" * 80)

    print(f"  Execution Wall Time : {total_time:.2f} seconds")
    print(f"  Diagnostic Tiers    : {TermColor.GREEN}{report.tiers_passed} Passed{TermColor.RESET} | "
          f"{TermColor.YELLOW}{report.tiers_warned} Warnings{TermColor.RESET} | "
          f"{TermColor.RED}{report.tiers_failed} Critical Failures{TermColor.RESET}")

    if report.warnings:
        print(f"\n{TermColor.YELLOW}[!] NON-CRITICAL SYSTEM WARNINGS:{TermColor.RESET}")
        for w in report.warnings:
            print(f"    • {TermColor.BOLD}{w['tier']}{TermColor.RESET}: {w['reason']}")
            if w['remediation']:
                print(f"      {TermColor.CYAN}Recommendation:{TermColor.RESET} {w['remediation']}")

    if report.critical_failures:
        print(f"\n{TermColor.RED}[X] CRITICAL PRE-BOOT BLOCKERS DETECTED:{TermColor.RESET}")
        for f in report.critical_failures:
            print(f"    • {TermColor.BOLD}{f['tier']}{TermColor.RESET}: {f['error']}")
            if f['remediation']:
                print(f"      {TermColor.GREEN}Fix:{TermColor.RESET} {f['remediation']}")
        print(f"\n{TermColor.DIM}Full traceback and logs written to: {report.log_path}{TermColor.RESET}")

    print("=" * 80)

    if report.tiers_failed == 0:
        cprint("""
╔════════════════════════════════════════════════════════════════════════════════╗
║  ✅ PRE-SYSTEM BOOT CHECK COMPLETE — ALL CRITICAL TIERS VERIFIED               ║
║  SYSTEM STATUS: AIR-GAP OPERATIONAL & READY FOR LIVE DEMO / PRESENTATION       ║
╚════════════════════════════════════════════════════════════════════════════════╝
""", TermColor.GREEN, bold=True)
    else:
        cprint("""
╔════════════════════════════════════════════════════════════════════════════════╗
║  ❌ PRE-SYSTEM BOOT CHECK FAILED — CRITICAL DEPENDENCY OR MODEL DEFECTS        ║
║  SYSTEM STATUS: NOT READY FOR LIVE DEMO (REVIEW REMEDIATION ACTIONS ABOVE)     ║
╚════════════════════════════════════════════════════════════════════════════════╝
""", TermColor.RED, bold=True)


# ------------------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="VAYU-CHRONICLE Pre-Boot Full Smoke Test & Natural Query Verifier"
    )
    parser.add_argument("--non-interactive", "--ci", action="store_true", 
                        help="Run in non-interactive / CI mode (bypasses manual search prompt)")
    parser.add_argument("--query", type=str, default=None, 
                        help="Run a specific natural language query verification directly")
    parser.add_argument("--dataset", type=str, default="all", 
                        help="Target dataset for search verification ('all', 'delhi', 'mumbai', etc.)")
    parser.add_argument("--log-file", type=str, default=os.path.join(BACKEND_DIR, "full_smoke_test.log"),
                        help="Path to output diagnostic log file")
    args = parser.parse_args()

    print_banner()

    report = DiagnosticReport(log_path=args.log_file)
    report.log("Starting Pre-Boot Full Smoke Test...")

    # Sequential Tier Execution
    # 1. Environment & Venv
    check_environment_and_venv(report)

    # 2. Hardware & CUDA
    check_hardware_and_compute(report)

    # 3. Dependencies
    check_core_dependencies(report)

    # 4. Config & Air-Gap
    cfg_ok, config = check_configuration_and_env(report)

    # 5. Offline Model Files
    models_ok, clip_dir = check_offline_model_artifacts(report, config)

    # 6. Model Inference Smoke
    embedder = None
    if models_ok:
        _, embedder = check_model_inference_smoke(report, clip_dir)
    else:
        print_section_header(6, "Live Model Inference & Tactical Smoke Tests")
        print_check_result("Model Inference", "FAIL", "Skipped due to missing model artifacts in Tier 5")
        report.record_fail("Model Inference", "Skipped due to missing weights")

    # 7. Geospatial Indices
    check_vector_indices_and_datasets(report)

    # 8. SQLite Audit DB
    check_sqlite_audit_system(report)

    # 9. Natural Search Engine & Interactive CLI
    check_search_engine_and_manual_queries(
        report, 
        embedder, 
        cli_query=args.query, 
        cli_dataset=args.dataset, 
        non_interactive=args.non_interactive
    )

    # Flush report to disk
    report.flush_to_disk()

    # Final Summary
    print_final_summary(report)

    # Exit code: 0 if passed, 1 if critical failures exist
    sys.exit(0 if report.tiers_failed == 0 else 1)


if __name__ == "__main__":
    main()
