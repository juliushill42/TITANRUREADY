#!/usr/bin/env python3
"""
TitanU OS v2.5 — CPU Benchmark & Model Selection
=================================================
Analyzes your hardware and recommends optimal model configuration.
Run this first to generate your personalized .env file.
"""

import os
import sys
import time
import platform
import subprocess
import json
from pathlib import Path
from datetime import datetime

# =============================================================================
# HARDWARE DETECTION
# =============================================================================

def get_cpu_info() -> dict:
    """Gather CPU information."""
    info = {
        "platform": platform.system(),
        "processor": platform.processor() or "Unknown",
        "cores_physical": (os.cpu_count() or 8) // 2,
        "cores_logical": os.cpu_count() or 8,
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
    }
    
    # Linux: Get detailed CPU info
    if platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line.lower():
                        info["model_name"] = line.split(":")[1].strip()
                        break
        except:
            pass
    
    # Windows: Try wmic
    elif platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["wmic", "cpu", "get", "name"],
                capture_output=True, text=True, timeout=10
            )
            lines = [l.strip() for l in result.stdout.split("\n") if l.strip() and l.strip() != "Name"]
            if lines:
                info["model_name"] = lines[0]
        except:
            pass
    
    return info


def get_memory_info() -> dict:
    """Get RAM information."""
    try:
        if platform.system() == "Windows":
            import ctypes
            
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ('dwLength', ctypes.c_ulong),
                    ('dwMemoryLoad', ctypes.c_ulong),
                    ('ullTotalPhys', ctypes.c_ulonglong),
                    ('ullAvailPhys', ctypes.c_ulonglong),
                    ('ullTotalPageFile', ctypes.c_ulonglong),
                    ('ullAvailPageFile', ctypes.c_ulonglong),
                    ('ullTotalVirtual', ctypes.c_ulonglong),
                    ('ullAvailVirtual', ctypes.c_ulonglong),
                    ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
                ]
            
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            
            return {
                "total_gb": round(stat.ullTotalPhys / (1024**3), 1),
                "available_gb": round(stat.ullAvailPhys / (1024**3), 1),
                "used_percent": stat.dwMemoryLoad,
            }
        else:
            # Linux/Mac
            with open("/proc/meminfo") as f:
                lines = f.readlines()
                mem = {}
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(":")
                        mem[key] = int(parts[1])
                
                total = mem.get("MemTotal", 8000000) / (1024 * 1024)
                available = mem.get("MemAvailable", 4000000) / (1024 * 1024)
                
                return {
                    "total_gb": round(total, 1),
                    "available_gb": round(available, 1),
                    "used_percent": round((1 - available/total) * 100, 1),
                }
    except Exception as e:
        print(f"  Warning: Could not detect RAM ({e})")
        return {"total_gb": 8, "available_gb": 4, "used_percent": 50}


def check_gpu() -> dict:
    """Check for GPU availability."""
    gpu_info = {"available": False, "name": None, "vram_gb": None}
    
    # Check NVIDIA
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            gpu_info["available"] = True
            gpu_info["type"] = "nvidia"
            gpu_info["name"] = parts[0].strip() if parts else "NVIDIA GPU"
            if len(parts) > 1:
                vram = parts[1].strip().replace("MiB", "").strip()
                gpu_info["vram_gb"] = round(int(vram) / 1024, 1)
    except:
        pass
    
    return gpu_info


def check_ollama() -> dict:
    """Check Ollama status and installed models."""
    info = {"running": False, "models": [], "version": None}
    
    try:
        # Check version
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            info["version"] = result.stdout.strip()
        
        # List models
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            info["running"] = True
            lines = result.stdout.strip().split("\n")[1:]  # Skip header
            for line in lines:
                if line.strip():
                    model_name = line.split()[0]
                    info["models"].append(model_name)
    except FileNotFoundError:
        info["error"] = "Ollama not installed"
    except Exception as e:
        info["error"] = str(e)
    
    return info


# =============================================================================
# MODEL RECOMMENDATIONS
# =============================================================================

# Model database: (context_window, min_ram_gb, recommended_ram_gb, quality_tier)
MODEL_DATABASE = {
    # Small models (4GB+ RAM)
    "phi3:mini": (4096, 2, 4, "basic"),
    "qwen2.5:0.5b": (4096, 2, 4, "minimal"),
    "qwen2.5:1.5b": (8192, 3, 4, "basic"),
    
    # Medium models (8GB+ RAM)  
    "qwen2.5-coder:3b": (8192, 4, 8, "good"),
    "llama3.2:3b": (8192, 4, 8, "good"),
    "phi3:medium": (8192, 6, 8, "good"),
    
    # Large models (16GB+ RAM)
    "qwen2.5-coder:7b": (16384, 8, 16, "very_good"),
    "llama3.2:8b": (8192, 8, 16, "very_good"),
    "mistral:7b": (8192, 8, 16, "very_good"),
    "deepseek-coder:6.7b": (16384, 8, 16, "very_good"),
    
    # XL models (32GB+ RAM)
    "qwen2.5-coder:14b": (32768, 16, 32, "excellent"),
    "llama3.1:70b": (131072, 48, 64, "premium"),
    "qwen2.5:72b": (32768, 48, 64, "premium"),
}


def recommend_models(memory_gb: float, cpu_cores: int, has_gpu: bool = False) -> list:
    """Generate model recommendations based on hardware."""
    recommendations = []
    
    for model, (context, min_ram, rec_ram, quality) in MODEL_DATABASE.items():
        if memory_gb >= min_ram:
            # Calculate suitability score
            ram_headroom = memory_gb - min_ram
            comfort_level = "comfortable" if memory_gb >= rec_ram else "tight"
            
            # CPU thread recommendation
            optimal_threads = min(cpu_cores, 8)
            
            recommendations.append({
                "model": model,
                "context_window": context,
                "min_ram": min_ram,
                "recommended_ram": rec_ram,
                "quality": quality,
                "comfort_level": comfort_level,
                "optimal_threads": optimal_threads,
                "priority": (
                    4 if quality == "premium" else
                    3 if quality == "excellent" else
                    2 if quality == "very_good" else
                    1 if quality == "good" else
                    0
                )
            })
    
    # Sort by quality (descending) but only include comfortable fits
    recommendations.sort(key=lambda x: (-x["priority"], x["min_ram"]))
    
    # Filter to best options
    comfortable = [r for r in recommendations if r["comfort_level"] == "comfortable"]
    tight = [r for r in recommendations if r["comfort_level"] == "tight"]
    
    # Return comfortable options first, then tight options as fallbacks
    result = comfortable[:3] + tight[:2]
    
    # Always include phi3:mini as ultimate fallback
    if not any(r["model"] == "phi3:mini" for r in result):
        result.append({
            "model": "phi3:mini",
            "context_window": 4096,
            "min_ram": 2,
            "quality": "fallback",
            "comfort_level": "comfortable",
            "optimal_threads": min(cpu_cores, 4),
            "priority": -1
        })
    
    return result


# =============================================================================
# BENCHMARKING
# =============================================================================

def benchmark_model(model: str, prompt: str = "Write a hello world function in Python. Be concise.") -> dict:
    """Run inference benchmark on a model."""
    result = {
        "model": model,
        "success": False,
        "time_seconds": None,
        "tokens_per_second": None,
        "output_preview": None,
        "error": None
    }
    
    print(f"  ⏱️  Benchmarking {model}...", end=" ", flush=True)
    
    try:
        start = time.time()
        proc = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True,
            text=True,
            timeout=120
        )
        elapsed = time.time() - start
        
        if proc.returncode == 0:
            output = proc.stdout.strip()
            # Rough token estimate: ~1.3 tokens per word
            token_estimate = len(output.split()) * 1.3
            tps = token_estimate / elapsed if elapsed > 0 else 0
            
            result["success"] = True
            result["time_seconds"] = round(elapsed, 2)
            result["tokens_per_second"] = round(tps, 1)
            result["output_preview"] = output[:100] + "..." if len(output) > 100 else output
            
            print(f"✓ {elapsed:.1f}s (~{tps:.1f} tok/s)")
        else:
            result["error"] = proc.stderr[:200] if proc.stderr else "Unknown error"
            print(f"✗ Error")
            
    except subprocess.TimeoutExpired:
        result["error"] = "Timeout (>120s)"
        print("✗ Timeout")
    except Exception as e:
        result["error"] = str(e)
        print(f"✗ {e}")
    
    return result


# =============================================================================
# ENV FILE GENERATION
# =============================================================================

def generate_env_file(
    recommended_model: str,
    context_window: int,
    cpu_threads: int,
    fallback_model: str = "phi3:mini",
    hardware_info: dict = None
) -> str:
    """Generate optimized .env configuration."""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    hardware_notes = ""
    if hardware_info:
        hardware_notes = f"""
# Hardware Detected:
# - CPU: {hardware_info.get('cpu', 'Unknown')}
# - RAM: {hardware_info.get('ram_total', '?')}GB total, {hardware_info.get('ram_available', '?')}GB available
# - Cores: {hardware_info.get('cores', '?')}
# - GPU: {hardware_info.get('gpu', 'None')}
"""
    
    env_content = f"""# ============================================
# TitanU OS v2.5 Configuration
# Generated: {timestamp}
# ============================================
{hardware_notes}
# ===================
# LLM PROVIDER
# ===================
TITAN_MODEL_PROVIDER=ollama
TITAN_LLM_BASE_URL=http://localhost:11434/v1
TITAN_LLM_API_KEY=ollama

# ===================
# MODEL SELECTION
# ===================
# Primary model for all agents
TITAN_MASTER_MODEL={recommended_model}
TITAN_SUB_MODEL={recommended_model}

# Fallback if primary fails
TITAN_FALLBACK_MODEL={fallback_model}

# ===================
# CONTEXT WINDOW
# ===================
TITAN_CONTEXT_WINDOW={context_window}
TITAN_OUTPUT_RESERVE={context_window // 4}
TITAN_MAX_HISTORY=50

# ===================
# HARDWARE CONFIG
# ===================
# Set to true only if you have NVIDIA GPU + CUDA
TITAN_GPU_ENABLED=false

# CPU threads for inference (usually cores/2 to cores)
TITAN_CPU_THREADS={cpu_threads}

# Batch size for processing
TITAN_BATCH_SIZE=512

# ===================
# PERFORMANCE
# ===================
# Options: fast, balanced, quality
TITAN_PERFORMANCE_MODE=balanced

# ===================
# MEMORY MANAGEMENT
# ===================
TITAN_MEMORY_MAX_ENTRIES=500
TITAN_CHAT_MAX_MESSAGES=200

# ===================
# AGENT CONFIG
# ===================
# Max time (seconds) for agent response
TITAN_AGENT_TIMEOUT=120

# Retry attempts on failure
TITAN_AGENT_MAX_RETRIES=2

# Artificial delay before response (seconds) for UI feel
TITAN_AGENT_THINKING_DELAY=1.5

# ===================
# PATHS
# ===================
TITAN_DATA_DIR=./titan_data
TITAN_LOGS_DIR=./logs
TITAN_AGENTS_DIR=./agents

# ===================
# WEB UI
# ===================
TITAN_PORT=8000
TITAN_HOST=127.0.0.1

# ===================
# BRANDING
# ===================
TITAN_VERSION=2.5.0
TITAN_EDITION=Commander
"""
    return env_content


# =============================================================================
# MAIN
# =============================================================================

def main():
    print()
    print("=" * 60)
    print("  TitanU OS v2.5 — Hardware Benchmark & Configuration")
    print("=" * 60)
    print()
    
    # -------------------------------------------------------------------------
    # Step 1: Gather Hardware Info
    # -------------------------------------------------------------------------
    print("📊 ANALYZING HARDWARE")
    print("-" * 40)
    
    cpu = get_cpu_info()
    memory = get_memory_info()
    gpu = check_gpu()
    ollama = check_ollama()
    
    print(f"  CPU: {cpu.get('model_name', cpu.get('processor', 'Unknown'))}")
    print(f"  Cores: {cpu['cores_logical']} logical ({cpu['cores_physical']} physical)")
    print(f"  Architecture: {cpu['architecture']}")
    print()
    print(f"  RAM Total: {memory['total_gb']} GB")
    print(f"  RAM Available: {memory['available_gb']} GB")
    print(f"  RAM Used: {memory['used_percent']}%")
    print()
    
    if gpu["available"]:
        print(f"  GPU: {gpu['name']}")
        if gpu.get("vram_gb"):
            print(f"  VRAM: {gpu['vram_gb']} GB")
    else:
        print("  GPU: None detected (CPU-only mode)")
    print()
    
    print(f"  Ollama: {'Running ✓' if ollama['running'] else 'Not running ✗'}")
    if ollama.get("error"):
        print(f"  Ollama Error: {ollama['error']}")
    if ollama["models"]:
        print(f"  Installed Models: {', '.join(ollama['models'][:5])}")
        if len(ollama["models"]) > 5:
            print(f"                    +{len(ollama['models']) - 5} more")
    print()
    
    # -------------------------------------------------------------------------
    # Step 2: Generate Recommendations
    # -------------------------------------------------------------------------
    print("🎯 MODEL RECOMMENDATIONS")
    print("-" * 40)
    
    recommendations = recommend_models(
        memory_gb=memory["available_gb"],
        cpu_cores=cpu["cores_logical"],
        has_gpu=gpu["available"]
    )
    
    for i, rec in enumerate(recommendations[:4]):
        marker = "→" if i == 0 else " "
        status = "★" if rec["comfort_level"] == "comfortable" else "○"
        print(f"  {marker} {status} {rec['model']}")
        print(f"      Context: {rec['context_window']} tokens")
        print(f"      Quality: {rec['quality']}")
        print(f"      RAM: {rec.get('min_ram', '?')}GB+ required")
        print()
    
    # -------------------------------------------------------------------------
    # Step 3: Benchmark (if Ollama running and model installed)
    # -------------------------------------------------------------------------
    best_model = recommendations[0]["model"]
    benchmark_results = None
    
    if ollama["running"]:
        print("⚡ BENCHMARKING")
        print("-" * 40)
        
        models_to_test = []
        for rec in recommendations[:2]:
            if rec["model"] in ollama["models"]:
                models_to_test.append(rec["model"])
        
        if not models_to_test:
            print(f"  Recommended model not installed.")
            print(f"  Install with: ollama pull {best_model}")
            print()
        else:
            benchmark_results = []
            for model in models_to_test:
                result = benchmark_model(model)
                benchmark_results.append(result)
            print()
            
            # Pick fastest successful model
            successful = [r for r in benchmark_results if r["success"]]
            if successful:
                fastest = min(successful, key=lambda x: x["time_seconds"])
                print(f"  Best performer: {fastest['model']} ({fastest['tokens_per_second']} tok/s)")
                best_model = fastest["model"]
    else:
        print("⚠️  Ollama not running - skipping benchmark")
        print("   Start with: ollama serve")
        print()
    
    # -------------------------------------------------------------------------
    # Step 4: Generate Configuration
    # -------------------------------------------------------------------------
    print("📝 GENERATING CONFIGURATION")
    print("-" * 40)
    
    best_rec = next((r for r in recommendations if r["model"] == best_model), recommendations[0])
    
    hardware_info = {
        "cpu": cpu.get("model_name", cpu.get("processor")),
        "cores": cpu["cores_logical"],
        "ram_total": memory["total_gb"],
        "ram_available": memory["available_gb"],
        "gpu": gpu.get("name", "None"),
    }
    
    env_content = generate_env_file(
        recommended_model=best_model,
        context_window=best_rec["context_window"],
        cpu_threads=best_rec.get("optimal_threads", min(cpu["cores_logical"], 8)),
        fallback_model="phi3:mini",
        hardware_info=hardware_info,
    )
    
    # Save files
    env_path = Path(".env.titanu")
    env_path.write_text(env_content)
    print(f"  ✓ Saved: {env_path}")
    
    # Also create quick-start .env if it doesn't exist
    if not Path(".env").exists():
        Path(".env").write_text(env_content)
        print(f"  ✓ Saved: .env")
    else:
        print(f"  ℹ .env already exists (not overwritten)")
    
    # Save benchmark report
    report = {
        "timestamp": datetime.now().isoformat(),
        "hardware": {
            "cpu": cpu,
            "memory": memory,
            "gpu": gpu,
        },
        "ollama": ollama,
        "recommendations": recommendations[:4],
        "selected_model": best_model,
        "benchmarks": benchmark_results,
    }
    
    report_path = Path("benchmark_report.json")
    report_path.write_text(json.dumps(report, indent=2))
    print(f"  ✓ Saved: {report_path}")
    print()
    
    # -------------------------------------------------------------------------
    # Step 5: Next Steps
    # -------------------------------------------------------------------------
    print("🚀 NEXT STEPS")
    print("-" * 40)
    
    if best_model not in ollama.get("models", []):
        print(f"  1. Install model:")
        print(f"     ollama pull {best_model}")
        print()
    
    print(f"  2. Start TitanU OS:")
    print(f"     python titan_os.py")
    print()
    print(f"  3. Open in browser:")
    print(f"     http://127.0.0.1:8000")
    print()
    
    print("=" * 60)
    print("  Configuration complete! TitanU OS is ready.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()