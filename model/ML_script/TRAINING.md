# Training LightGBM Country Models (v4 simple)

This document explains how to run the training script `train_lightgbm_country_models_v4_simple.py` located in this folder.

## Overview

The script trains per-country LightGBM regression models and a global fallback model, then exports artifacts (ONNX) and a `model_registry.json` describing available models.

## Prerequisites

- Python 3.8+ (3.9/3.10 recommended)
- pip
- Sufficient RAM and disk space for the dataset and models
- (Optional) A Python virtual environment

Required Python packages include (the repository may include a `requirements.txt` under `model/`):

- lightgbm
- numpy
- pandas
- scikit-learn
- onnxmltools
- onnxconverter_common

If a `requirements.txt` exists in the `model/` folder, prefer installing from it.

## Setup (recommended)

On macOS / Linux:

```bash
cd model/ML_script
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r ../requirements.txt   # if present
# or explicit install
pip install lightgbm pandas numpy scikit-learn onnxmltools onnxconverter-common
```

On Windows PowerShell:

```powershell
cd model\ML_script
python -m venv .venv
. .venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r ..\requirements.txt   # if present
# or explicit install
pip install lightgbm pandas numpy scikit-learn onnxmltools onnxconverter-common
```

## Running the training script

Basic run with defaults (reads default processed data and writes artifacts under `model/artifacts_country_v4_simple`):

```bash
python train_lightgbm_country_models_v4_simple.py
```

Specify a custom processed data path and output directory:

```bash
python train_lightgbm_country_models_v4_simple.py \
  --data ../data/processed_data/cleaned_panel_country_day.csv \
  --output-dir ../model/artifacts_country_v4_simple
```

Train only for a subset of countries (comma-separated ISO3 codes):

```bash
python train_lightgbm_country_models_v4_simple.py --countries USA,CAN,GBR
```

Notes:
- The script expects the input CSV to contain at least the columns: `code`, `date`, and `target_next_day_active_change`. It will raise an error if these are missing.
- If `model/requirements.txt` exists, prefer installing from it to get the correct package versions used by the project.

## Running in background / on a server

On macOS / Linux you can run in background and log output:

```bash
nohup python train_lightgbm_country_models_v4_simple.py --output-dir /path/to/out > train.log 2>&1 &
tail -f train.log
```

On Windows use `Start-Process` or run inside a terminal multiplexer.

## Outputs

The script writes artifacts to the `--output-dir` (default: `model/artifacts_country_v4_simple`):

- `country_models/<ISO3>/lightgbm_model.onnx` - ONNX model export
- `country_models/<ISO3>/feature_columns.json` - feature list used for that country
- `global_fallback_model/*` - global fallback model + artifacts
- `model_registry.json` - registry describing which countries have per-country models and which fall back to the global model
- `country_metrics.csv`, `country_metrics.json`, `summary.txt`, `skipped_countries.txt`

## Troubleshooting

- Missing required columns: open the processed CSV and verify `code`, `date`, `target_next_day_active_change` exist.
- Low-memory or long runtimes: reduce the country list with `--countries` to train a subset, or run on a machine with more RAM/CPUs.
- LightGBM build errors: ensure a prebuilt wheel is available for your Python version or install from conda.
- ONNX export errors: check `onnxmltools` and `onnxconverter_common` versions; the script targets opset 15.

If you want, I can add a small wrapper to run the training in a reproducible container or create an example `requirements.txt` for this script. 
