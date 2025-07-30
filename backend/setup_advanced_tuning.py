#!/usr/bin/env python3
"""
Advanced Fine-Tuning Setup Script
Checks system requirements and installs dependencies for LoRA, QLoRA, and RAG tuning
"""

import os
import sys
import subprocess
import platform
import json
import time
from pathlib import Path

def print_progress(step: str, progress: float, message: str, extra_data: dict = None):
    """Print progress updates in JSON format for frontend"""
    progress_data = {
        "step": step,
        "progress": progress,
        "message": message,
        "timestamp": time.time(),
        **(extra_data or {})
    }
    print(json.dumps(progress_data), flush=True)

def check_python_version():
    """Check if Python version is compatible"""
    print_progress("python_check", 0.1, "Checking Python version...")
    
    version = sys.version_info
    if version.major != 3 or version.minor < 8:
        print_progress("python_check", 1.0, 
                      f"❌ Python 3.8+ required, found {version.major}.{version.minor}", 
                      {"error": True})
        return False
    
    print_progress("python_check", 1.0, 
                  f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def check_gpu_availability():
    """Check GPU availability and CUDA support"""
    print_progress("gpu_check", 0.2, "Checking GPU availability...")
    
    gpu_info = {
        "has_nvidia": False,
        "has_cuda": False,
        "cuda_version": None,
        "gpu_count": 0,
        "gpu_memory": []
    }
    
    try:
        # Check NVIDIA GPUs
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', 
                               '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            gpu_info["has_nvidia"] = True
            gpu_lines = result.stdout.strip().split('\n')
            gpu_info["gpu_count"] = len(gpu_lines)
            
            for line in gpu_lines:
                if line.strip():
                    name, memory = line.split(',')
                    gpu_info["gpu_memory"].append({
                        "name": name.strip(),
                        "memory_mb": int(memory.strip())
                    })
        
        # Check CUDA
        try:
            import torch
            if torch.cuda.is_available():
                gpu_info["has_cuda"] = True
                gpu_info["cuda_version"] = torch.version.cuda
        except ImportError:
            pass
            
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    if gpu_info["has_nvidia"]:
        total_memory = sum(gpu["memory_mb"] for gpu in gpu_info["gpu_memory"])
        print_progress("gpu_check", 1.0, 
                      f"✅ Found {gpu_info['gpu_count']} NVIDIA GPU(s) with {total_memory//1024:.1f}GB total memory",
                      gpu_info)
    else:
        print_progress("gpu_check", 1.0, 
                      "⚠️ No NVIDIA GPU detected - CPU-only training available",
                      gpu_info)
    
    return gpu_info

def check_system_memory():
    """Check system RAM"""
    print_progress("memory_check", 0.3, "Checking system memory...")
    
    try:
        import psutil
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        
        if memory_gb < 8:
            print_progress("memory_check", 1.0, 
                          f"⚠️ Low RAM detected: {memory_gb:.1f}GB (8GB+ recommended)",
                          {"memory_gb": memory_gb, "warning": True})
        elif memory_gb < 16:
            print_progress("memory_check", 1.0, 
                          f"✅ Adequate RAM: {memory_gb:.1f}GB",
                          {"memory_gb": memory_gb})
        else:
            print_progress("memory_check", 1.0, 
                          f"✅ Excellent RAM: {memory_gb:.1f}GB",
                          {"memory_gb": memory_gb})
        
        return memory_gb
    except ImportError:
        print_progress("memory_check", 1.0, 
                      "❓ Could not check memory (psutil not installed)")
        return None

def install_pytorch(gpu_info):
    """Install PyTorch with appropriate CUDA support"""
    print_progress("pytorch_install", 0.1, "Installing PyTorch...")
    
    # Determine PyTorch installation command
    if gpu_info["has_cuda"] and gpu_info["cuda_version"]:
        cuda_version = gpu_info["cuda_version"]
        if cuda_version.startswith("12"):
            torch_cmd = ["pip", "install", "torch", "torchvision", "torchaudio", 
                        "--index-url", "https://download.pytorch.org/whl/cu121"]
        elif cuda_version.startswith("11"):
            torch_cmd = ["pip", "install", "torch", "torchvision", "torchaudio", 
                        "--index-url", "https://download.pytorch.org/whl/cu118"]
        else:
            torch_cmd = ["pip", "install", "torch", "torchvision", "torchaudio"]
    else:
        torch_cmd = ["pip", "install", "torch", "torchvision", "torchaudio", "--index-url", 
                    "https://download.pytorch.org/whl/cpu"]
    
    try:
        print_progress("pytorch_install", 0.5, f"Running: {' '.join(torch_cmd)}")
        result = subprocess.run(torch_cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print_progress("pytorch_install", 1.0, "✅ PyTorch installed successfully")
            return True
        else:
            print_progress("pytorch_install", 1.0, 
                          f"❌ PyTorch installation failed: {result.stderr}",
                          {"error": True})
            return False
            
    except subprocess.TimeoutExpired:
        print_progress("pytorch_install", 1.0, 
                      "❌ PyTorch installation timed out",
                      {"error": True})
        return False

def install_requirements():
    """Install all requirements from requirements.txt"""
    print_progress("requirements_install", 0.1, "Installing requirements...")
    
    requirements_path = Path(__file__).parent / "requirements.txt"
    
    if not requirements_path.exists():
        print_progress("requirements_install", 1.0, 
                      "❌ requirements.txt not found",
                      {"error": True})
        return False
    
    try:
        cmd = ["pip", "install", "-r", str(requirements_path)]
        print_progress("requirements_install", 0.3, f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print_progress("requirements_install", 1.0, 
                          "✅ All requirements installed successfully")
            return True
        else:
            print_progress("requirements_install", 1.0, 
                          f"❌ Requirements installation failed: {result.stderr[:500]}",
                          {"error": True})
            return False
            
    except subprocess.TimeoutExpired:
        print_progress("requirements_install", 1.0, 
                      "❌ Requirements installation timed out",
                      {"error": True})
        return False

def verify_installations():
    """Verify that key packages are correctly installed"""
    print_progress("verification", 0.1, "Verifying installations...")
    
    packages_to_check = [
        ("torch", "PyTorch"),
        ("transformers", "Transformers"),
        ("peft", "PEFT (LoRA)"),
        ("bitsandbytes", "BitsAndBytes (QLoRA)"),
        ("sentence_transformers", "Sentence Transformers"),
        ("datasets", "HuggingFace Datasets"),
        ("accelerate", "Accelerate")
    ]
    
    verification_results = {}
    
    for i, (package, name) in enumerate(packages_to_check):
        progress = (i + 1) / len(packages_to_check) * 0.8
        print_progress("verification", progress, f"Checking {name}...")
        
        try:
            __import__(package)
            verification_results[package] = True
            print_progress("verification", progress, f"✅ {name} available")
        except ImportError:
            verification_results[package] = False
            print_progress("verification", progress, f"❌ {name} not available")
    
    # Special check for CUDA in PyTorch
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        verification_results["cuda"] = cuda_available
        
        if cuda_available:
            print_progress("verification", 0.9, f"✅ CUDA available in PyTorch (devices: {torch.cuda.device_count()})")
        else:
            print_progress("verification", 0.9, "⚠️ CUDA not available in PyTorch")
    except ImportError:
        verification_results["cuda"] = False
    
    success_count = sum(verification_results.values())
    total_count = len(verification_results)
    
    print_progress("verification", 1.0, 
                  f"Verification complete: {success_count}/{total_count} packages available",
                  {"results": verification_results})
    
    return verification_results

def setup_model_cache():
    """Setup model cache directory"""
    print_progress("cache_setup", 0.5, "Setting up model cache directory...")
    
    cache_dir = Path.home() / ".cache" / "rag_app_models"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Set environment variable for HuggingFace cache
    os.environ["HF_HOME"] = str(cache_dir / "huggingface")
    os.environ["TRANSFORMERS_CACHE"] = str(cache_dir / "transformers")
    
    print_progress("cache_setup", 1.0, f"✅ Model cache set up at {cache_dir}")
    return cache_dir

def generate_config_template():
    """Generate a configuration template for fine-tuning"""
    print_progress("config_template", 0.5, "Generating configuration template...")
    
    config_template = {
        "basic_settings": {
            "model_name": "microsoft/DialoGPT-medium",
            "dataset_path": "./data/training_data.jsonl",
            "output_dir": "./fine_tuned_models",
            "language": "en"
        },
        "method_settings": {
            "method": "lora",
            "lora_r": 16,
            "lora_alpha": 32,
            "lora_dropout": 0.1,
            "use_4bit": False
        },
        "training_settings": {
            "num_epochs": 3,
            "learning_rate": 0.0002,
            "batch_size": 4,
            "gradient_accumulation_steps": 4,
            "max_seq_length": 512
        },
        "rag_settings": {
            "use_retrieval_augmentation": False,
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "top_k_retrieval": 5
        },
        "advanced_settings": {
            "gradient_checkpointing": True,
            "fp16": True,
            "save_steps": 500,
            "logging_steps": 10
        }
    }
    
    config_path = Path("fine_tuning_config_template.json")
    with open(config_path, 'w') as f:
        json.dump(config_template, f, indent=2)
    
    print_progress("config_template", 1.0, f"✅ Configuration template saved to {config_path}")
    return config_path

def create_example_dataset():
    """Create an example training dataset"""
    print_progress("example_data", 0.5, "Creating example dataset...")
    
    # Example data for different training methods
    examples = {
        "instruction_tuning": [
            {
                "instruction": "Explain what machine learning is in simple terms.",
                "input": "",
                "output": "Machine learning is a way for computers to learn and make decisions from data, just like how humans learn from experience."
            },
            {
                "instruction": "Translate the following English text to Polish.",
                "input": "Hello, how are you?",
                "output": "Cześć, jak się masz?"
            }
        ],
        "rag_training": [
            {
                "context": "Machine learning is a subset of artificial intelligence that enables computers to learn without being explicitly programmed.",
                "question": "What is machine learning?",
                "answer": "Machine learning is a subset of AI that allows computers to learn from data without explicit programming."
            }
        ],
        "conversation": [
            {
                "text": "Human: What's the weather like today?\nAssistant: I don't have access to real-time weather data, but you can check a weather app or website for current conditions in your area."
            }
        ]
    }
    
    data_dir = Path("example_data")
    data_dir.mkdir(exist_ok=True)
    
    for data_type, data in examples.items():
        file_path = data_dir / f"{data_type}_example.jsonl"
        with open(file_path, 'w') as f:
            for item in data:
                f.write(json.dumps(item) + '\n')
    
    print_progress("example_data", 1.0, f"✅ Example datasets created in {data_dir}")
    return data_dir

def main():
    """Main setup function"""
    print_progress("start", 0.0, "Starting Advanced Fine-Tuning Setup...")
    
    # System checks
    if not check_python_version():
        return
    
    gpu_info = check_gpu_availability()
    memory_gb = check_system_memory()
    
    # Recommendations based on system
    if memory_gb and memory_gb < 8:
        print_progress("recommendations", 0.0, 
                      "⚠️ Recommendation: Use QLoRA method for memory efficiency",
                      {"low_memory": True})
    
    if not gpu_info["has_nvidia"]:
        print_progress("recommendations", 0.0, 
                      "⚠️ Recommendation: Consider using smaller models for CPU training",
                      {"cpu_only": True})
    
    # Install PyTorch first
    if not install_pytorch(gpu_info):
        print_progress("error", 1.0, "❌ Setup failed at PyTorch installation")
        return
    
    # Install other requirements
    if not install_requirements():
        print_progress("error", 1.0, "❌ Setup failed at requirements installation")
        return
    
    # Verify installations
    verification_results = verify_installations()
    
    # Setup cache and templates
    cache_dir = setup_model_cache()
    config_path = generate_config_template()
    example_dir = create_example_dataset()
    
    # Final summary
    success_count = sum(verification_results.values())
    total_count = len(verification_results)
    
    if success_count == total_count:
        print_progress("complete", 1.0, 
                      "🎉 Advanced Fine-Tuning setup completed successfully!",
                      {
                          "cache_dir": str(cache_dir),
                          "config_template": str(config_path),
                          "example_data": str(example_dir),
                          "gpu_available": gpu_info["has_nvidia"],
                          "cuda_available": verification_results.get("cuda", False)
                      })
    else:
        print_progress("partial", 1.0, 
                      f"⚠️ Setup completed with warnings ({success_count}/{total_count} packages available)",
                      {
                          "missing_packages": [k for k, v in verification_results.items() if not v],
                          "cache_dir": str(cache_dir),
                          "config_template": str(config_path)
                      })

if __name__ == "__main__":
    main() 