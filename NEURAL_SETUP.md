# Neural Network Setup Guide

The DPW project includes both **traditional machine learning** (ONNX) and **neural network** (PyTorch GNN+LSTM) prediction models.

## The Problem

If you see errors like:
- `POST /api/v1/infections/neural-prediction` returns 500
- `ImportError: No module named 'torch'`
- `RuntimeError: Neural prediction dependencies are missing`

...then the neural network dependencies are not installed.

## Solution

The one-click start scripts (`start_all.sh`, `start_all.ps1`, `start_all.bat`) now attempt to install all dependencies, including PyTorch and torch-geometric.

### For Automatic Installation (Recommended)

Run the one-click script for your OS:
- **macOS/Linux**: `bash start_all.sh`
- **Windows (PowerShell)**: `.\start_all.ps1`
- **Windows (CMD)**: `start_all.bat`

These scripts will now install PyTorch and torch-geometric automatically. The first run may take several minutes.

### For Manual Installation

If the automatic installation fails or you prefer manual control:

1. **Activate the backend virtual environment:**
   ```bash
   cd backend
   source .venv/bin/activate  # macOS/Linux
   # or
   .venv\Scripts\activate     # Windows CMD
   # or
   .venv\Scripts\Activate.ps1 # Windows PowerShell
   ```

2. **Install PyTorch (choose one):**
   ```bash
   # CPU version (recommended for most users)
   pip install torch
   
   # GPU with CUDA 12.1
   pip install torch --index-url https://download.pytorch.org/whl/cu121
   
   # GPU with CUDA 11.8
   pip install torch --index-url https://download.pytorch.org/whl/cu118
   ```

3. **Install remaining dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation:**
   ```python
   python -c "import torch; import torch_geometric; print('✓ Neural deps installed')"
   ```

5. **Restart the backend service**

## Platform-Specific Notes

### macOS
- May require Xcode command line tools:
  ```bash
  xcode-select --install
  ```

### Linux (Ubuntu/Debian)
- May require build dependencies:
  ```bash
  sudo apt-get update
  sudo apt-get install build-essential python3-dev
  ```

### Windows
- Visual C++ build tools recommended (install via Visual Studio Community)
- PowerShell ExecutionPolicy may need adjustment to run `.ps1` scripts

## Verify Setup

Test that both models work:

```bash
# Terminal 1: Start backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Test endpoints
curl -X POST http://127.0.0.1:8000/api/v1/infections/neural-prediction \
  -H "Content-Type: application/json" \
  -d '{"seed_country": "USA"}'

curl -X POST http://127.0.0.1:8000/api/v1/infections/traditional-onnx-forecast \
  -H "Content-Type: application/json" \
  -d '{"origin_country": "USA", "forecast_days": 30}'
```

Both should return valid predictions (not 500 errors).

## More Information

- **PyTorch Installation**: https://pytorch.org/get-started/locally/
- **PyTorch Geometric**: https://pytorch-geometric.readthedocs.io/en/latest/notes/installation.html
- **Neural Model Training**: See [model/neural/README.md](model/neural/README.md)
