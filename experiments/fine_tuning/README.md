
# MLX Fine-tuning Experiment: Product Mapping

This directory contains an experiment demonstrating how to fine-tune a Small Language Model (SLM) like Qwen 2.5-0.5B to perform specific product mapping for the Vietnamese market context.

## 🎯 Objective
Train a small, fast model (0.5B parameters) to replicate the logic of our `retailer_mapping.yaml` database. This allows for:
1.  **Fast Inference**: ~100x faster than 7B models.
2.  **Structured Output**: The model learns to output *only* the product key.
3.  **Generalization**: The model can guess keys for unseen product variations.

## 🛠️ Setup

### Prerequisites
- Apple Silicon Mac (M1/M2/M3)
- Python 3.11+
- `mlx` and `mlx-lm` libraries

```bash
pip install mlx-lm
```

### Directory Structure
```
experiments/fine_tuning/
├── data/
│   ├── train.jsonl      # Training data (from retailer_mapping.yaml)
│   └── valid.jsonl      # Validation data
├── adapters/            # Trained weights (LoRA)
├── prepare_data.py      # Script to convert YAML -> JSONL
├── test_inference.py    # Script to test the trained model
└── README.md            # This file
```

## 🚀 Workflow

### 1. Prepare Data
Convert the existing `retailer_mapping.yaml` into JSONL format for training.

```bash
python experiments/fine_tuning/prepare_data.py
```
*Output: `data/train.jsonl` (347 examples), `data/valid.jsonl` (39 examples)*

### 2. Fine-tune (LoRA)
Train the adapter using MLX. We use `mlx-community/Llama-3.2-3B-Instruct-4bit` as the base.

```bash
python -m mlx_lm.lora \
    --model mlx-community/Llama-3.2-3B-Instruct-4bit \
    --train \
    --data experiments/fine_tuning/data \
    --iters 1000 \
    --batch-size 4 \
    --adapter-path experiments/fine_tuning/adapters_llama
```

### 3. Inference / Testing
Load the trained adapter and test on new product names.

```bash
python experiments/fine_tuning/test_inference.py
```

## 📊 Results (Example)
*Input*: `Apple Watch SE 3 40mm (GPS) Viền Nhôm Dây Cao Su`
*Output*: `apple_watch_se_3_gps`

## 🧠 Why this matters?
Instead of writing 1000s of Regex rules, we teach a small AI to "understand" our catalog. This is the foundation for a scalable, automated catalog system.
