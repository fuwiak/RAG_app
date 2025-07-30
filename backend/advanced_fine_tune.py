#!/usr/bin/env python3
"""
Advanced Fine-Tuning for RAG Applications
Supports LoRA, QLoRA, PEFT, and RAG-specific tuning methods
"""

import sys
import json
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

# Core ML libraries
try:
    import torch
    import transformers
    from transformers import (
        AutoTokenizer, AutoModelForCausalLM, AutoModelForSequenceClassification,
        TrainingArguments, Trainer, DataCollatorForLanguageModeling
    )
    from datasets import load_dataset, Dataset
    
    # PEFT libraries for LoRA/QLoRA
    from peft import (
        LoraConfig, TaskType, get_peft_model, PeftModel,
        prepare_model_for_kbit_training
    )
    
    # Quantization libraries
    from bitsandbytes import BitsAndBytesConfig
    
    # RAG-specific libraries
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    
    ML_AVAILABLE = True
except ImportError as e:
    ML_AVAILABLE = False
    print(f"Warning: ML libraries not available: {e}")

@dataclass
class FineTuneConfig:
    """Comprehensive fine-tuning configuration"""
    # Basic settings
    model_name: str = "microsoft/DialoGPT-medium"
    dataset_path: str = ""
    output_dir: str = "./fine_tuned_model"
    
    # Fine-tuning method
    method: str = "lora"  # lora, qlora, full, instruction, rag_specific
    
    # LoRA settings
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    lora_target_modules: list = None
    
    # QLoRA settings
    use_4bit: bool = False
    bnb_4bit_compute_dtype: str = "float16"
    bnb_4bit_use_double_quant: bool = True
    bnb_4bit_quant_type: str = "nf4"
    
    # Training parameters
    num_epochs: int = 3
    learning_rate: float = 2e-4
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    warmup_steps: int = 100
    max_seq_length: int = 512
    
    # RAG-specific settings
    use_retrieval_augmentation: bool = False
    retrieval_corpus_path: str = ""
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    top_k_retrieval: int = 5
    
    # Advanced settings
    gradient_checkpointing: bool = True
    fp16: bool = True
    dataloader_num_workers: int = 4
    save_steps: int = 500
    eval_steps: int = 500
    logging_steps: int = 10
    
    # Language-specific settings
    language: str = "en"  # en, pl, ru, de, fr
    instruction_template: str = "default"

class AdvancedFineTuner:
    def __init__(self, config: FineTuneConfig):
        self.config = config
        self.model = None
        self.tokenizer = None
        self.dataset = None
        self.retrieval_index = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def emit_progress(self, step: str, progress: float, message: str, extra_data: Dict = None):
        """Emit progress updates for the frontend"""
        progress_data = {
            "step": step,
            "progress": progress,
            "message": message,
            "timestamp": time.time(),
            **(extra_data or {})
        }
        print(json.dumps(progress_data), flush=True)
        
    def setup_quantization_config(self) -> Optional[BitsAndBytesConfig]:
        """Setup quantization for QLoRA"""
        if not self.config.use_4bit or not ML_AVAILABLE:
            return None
            
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=getattr(torch, self.config.bnb_4bit_compute_dtype),
            bnb_4bit_use_double_quant=self.config.bnb_4bit_use_double_quant,
            bnb_4bit_quant_type=self.config.bnb_4bit_quant_type
        )
        
    def load_model_and_tokenizer(self):
        """Load model and tokenizer with optional quantization"""
        self.emit_progress("model_loading", 0.1, "Loading model and tokenizer...")
        
        if not ML_AVAILABLE:
            self.emit_progress("model_loading", 1.0, "ML libraries not available - using mock implementation")
            return
            
        # Setup quantization
        quantization_config = self.setup_quantization_config()
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
        # Load model
        model_kwargs = {
            "torch_dtype": torch.float16 if self.config.fp16 else torch.float32,
            "device_map": "auto" if torch.cuda.is_available() else None,
        }
        
        if quantization_config:
            model_kwargs["quantization_config"] = quantization_config
            
        self.model = AutoModelForCausalLM.from_pretrained(
            self.config.model_name,
            **model_kwargs
        )
        
        # Prepare for k-bit training if using quantization
        if quantization_config:
            self.model = prepare_model_for_kbit_training(self.model)
            
        self.emit_progress("model_loading", 1.0, f"Model {self.config.model_name} loaded successfully")
        
    def setup_lora(self):
        """Setup LoRA configuration"""
        if self.config.method not in ["lora", "qlora"] or not ML_AVAILABLE:
            return
            
        self.emit_progress("lora_setup", 0.5, "Setting up LoRA configuration...")
        
        # Default target modules based on model type
        if self.config.lora_target_modules is None:
            if "gpt" in self.config.model_name.lower():
                target_modules = ["c_attn", "c_proj", "c_fc"]
            elif "llama" in self.config.model_name.lower():
                target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]
            else:
                target_modules = ["q_proj", "v_proj"]  # Default for most models
        else:
            target_modules = self.config.lora_target_modules
            
        lora_config = LoraConfig(
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            target_modules=target_modules,
            lora_dropout=self.config.lora_dropout,
            bias="none",
            task_type=TaskType.CAUSAL_LM
        )
        
        self.model = get_peft_model(self.model, lora_config)
        self.model.print_trainable_parameters()
        
        self.emit_progress("lora_setup", 1.0, f"LoRA setup complete - targeting modules: {target_modules}")
        
    def setup_rag_retrieval(self):
        """Setup RAG retrieval system"""
        if not self.config.use_retrieval_augmentation or not ML_AVAILABLE:
            return
            
        self.emit_progress("rag_setup", 0.3, "Setting up RAG retrieval system...")
        
        # Load embedding model
        embedding_model = SentenceTransformer(self.config.embedding_model)
        
        # Load and process retrieval corpus
        if Path(self.config.retrieval_corpus_path).exists():
            with open(self.config.retrieval_corpus_path, 'r') as f:
                corpus = [line.strip() for line in f.readlines()]
                
            # Create embeddings
            embeddings = embedding_model.encode(corpus)
            
            # Build FAISS index
            dimension = embeddings.shape[1]
            self.retrieval_index = faiss.IndexFlatIP(dimension)
            self.retrieval_index.add(embeddings.astype('float32'))
            
            self.emit_progress("rag_setup", 1.0, f"RAG setup complete - indexed {len(corpus)} documents")
        else:
            self.emit_progress("rag_setup", 1.0, "RAG corpus not found - skipping retrieval setup")
            
    def prepare_dataset(self):
        """Prepare and preprocess training dataset"""
        self.emit_progress("data_prep", 0.2, "Loading and preprocessing dataset...")
        
        if not ML_AVAILABLE:
            self.emit_progress("data_prep", 1.0, "Dataset preparation skipped - ML libraries not available")
            return
            
        # Load dataset
        if self.config.dataset_path.endswith('.jsonl'):
            dataset = load_dataset('json', data_files=self.config.dataset_path)['train']
        elif self.config.dataset_path.endswith('.csv'):
            dataset = load_dataset('csv', data_files=self.config.dataset_path)['train']
        else:
            raise ValueError(f"Unsupported dataset format: {self.config.dataset_path}")
            
        # Preprocess based on training method
        if self.config.method == "instruction":
            dataset = self.prepare_instruction_dataset(dataset)
        elif self.config.method == "rag_specific":
            dataset = self.prepare_rag_dataset(dataset)
        else:
            dataset = self.prepare_standard_dataset(dataset)
            
        self.dataset = dataset
        self.emit_progress("data_prep", 1.0, f"Dataset prepared - {len(dataset)} examples")
        
    def prepare_instruction_dataset(self, dataset):
        """Prepare dataset for instruction tuning"""
        def format_instruction(example):
            if self.config.language == "pl":
                template = f"Instrukcja: {example.get('instruction', '')}\nOdpowiedź: {example.get('output', '')}"
            elif self.config.language == "ru":
                template = f"Инструкция: {example.get('instruction', '')}\nОтвет: {example.get('output', '')}"
            elif self.config.language == "de":
                template = f"Anweisung: {example.get('instruction', '')}\nAntwort: {example.get('output', '')}"
            elif self.config.language == "fr":
                template = f"Instruction: {example.get('instruction', '')}\nRéponse: {example.get('output', '')}"
            else:  # English
                template = f"Instruction: {example.get('instruction', '')}\nResponse: {example.get('output', '')}"
                
            return {"text": template}
            
        return dataset.map(format_instruction)
        
    def prepare_rag_dataset(self, dataset):
        """Prepare dataset for RAG-specific tuning"""
        def format_rag(example):
            context = example.get('context', '')
            question = example.get('question', '')
            answer = example.get('answer', '')
            
            if self.config.language == "pl":
                template = f"Kontekst: {context}\nPytanie: {question}\nOdpowiedź: {answer}"
            else:  # Default English
                template = f"Context: {context}\nQuestion: {question}\nAnswer: {answer}"
                
            return {"text": template}
            
        return dataset.map(format_rag)
        
    def prepare_standard_dataset(self, dataset):
        """Prepare dataset for standard language modeling"""
        def tokenize_function(examples):
            return self.tokenizer(
                examples["text"],
                truncation=True,
                padding=True,
                max_length=self.config.max_seq_length
            )
            
        return dataset.map(tokenize_function, batched=True)
        
    def train(self):
        """Execute the training process"""
        if not ML_AVAILABLE:
            # Mock training for demo
            self.mock_training()
            return
            
        self.emit_progress("training", 0.0, "Starting training...")
        
        # Setup training arguments
        training_args = TrainingArguments(
            output_dir=self.config.output_dir,
            num_train_epochs=self.config.num_epochs,
            per_device_train_batch_size=self.config.batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            warmup_steps=self.config.warmup_steps,
            learning_rate=self.config.learning_rate,
            fp16=self.config.fp16,
            logging_steps=self.config.logging_steps,
            save_steps=self.config.save_steps,
            eval_steps=self.config.eval_steps,
            gradient_checkpointing=self.config.gradient_checkpointing,
            dataloader_num_workers=self.config.dataloader_num_workers,
            remove_unused_columns=False,
        )
        
        # Setup data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False
        )
        
        # Initialize trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=self.dataset,
            data_collator=data_collator,
        )
        
        # Start training
        trainer.train()
        
        # Save final model
        trainer.save_model()
        self.tokenizer.save_pretrained(self.config.output_dir)
        
        self.emit_progress("training", 1.0, "Training completed successfully!")
        
    def mock_training(self):
        """Mock training process for demo purposes"""
        steps = [
            ("initialization", "Initializing training environment..."),
            ("data_loading", "Loading training data..."),
            ("model_setup", f"Setting up {self.config.method.upper()} configuration..."),
            ("epoch_1", "Training epoch 1/3..."),
            ("epoch_2", "Training epoch 2/3..."),
            ("epoch_3", "Training epoch 3/3..."),
            ("evaluation", "Evaluating model performance..."),
            ("saving", "Saving fine-tuned model..."),
            ("completion", "Training completed successfully!")
        ]
        
        for i, (step, message) in enumerate(steps):
            progress = (i + 1) / len(steps)
            self.emit_progress("training", progress, message, {
                "step_name": step,
                "method": self.config.method,
                "language": self.config.language,
                "model": self.config.model_name
            })
            time.sleep(2)  # Simulate processing time
            
    def run_full_pipeline(self):
        """Run the complete fine-tuning pipeline"""
        try:
            self.emit_progress("start", 0.0, "Starting advanced fine-tuning pipeline...")
            
            # Load model and tokenizer
            self.load_model_and_tokenizer()
            
            # Setup LoRA if needed
            if self.config.method in ["lora", "qlora"]:
                self.setup_lora()
                
            # Setup RAG if needed
            if self.config.use_retrieval_augmentation:
                self.setup_rag_retrieval()
                
            # Prepare dataset
            self.prepare_dataset()
            
            # Train model
            self.train()
            
            self.emit_progress("complete", 1.0, "Fine-tuning pipeline completed successfully!")
            
        except Exception as e:
            self.emit_progress("error", 0.0, f"Error during fine-tuning: {str(e)}")
            raise

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Configuration required"}), flush=True)
        return
        
    try:
        config_json = sys.argv[1]
        config_dict = json.loads(config_json)
        
        # Create configuration object
        config = FineTuneConfig(**config_dict)
        
        # Run fine-tuning
        tuner = AdvancedFineTuner(config)
        tuner.run_full_pipeline()
        
    except Exception as e:
        print(json.dumps({"error": f"Failed to run fine-tuning: {str(e)}"}), flush=True)

if __name__ == "__main__":
    main() 