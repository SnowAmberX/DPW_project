# Neural 模型 — 训练与预测

本目录包含用于训练与推断的 GNN + RNN（GAT + LSTM/GRU）模型代码与示例脚本。

先决条件
- Python 版本：建议使用 Python 3.10 或更高。
- 推荐使用uv来管理依赖和虚拟环境。

创建虚拟环境（Windows PowerShell 示例）：
```powershell
uv venv
# 或使用 venv：
python -m venv venv
# 激活虚拟环境（PowerShell）：
venv\Scripts\Activate.ps1
```

安装依赖（两种方式）：
- 推荐先安装合适的 PyTorch 版本（见下），随后安装其余依赖：
```powershell
# 例如：使用 pip 安装 requirements
pip install -r requirements.txt
# 或（如果你使用 uv）：
uv pip install -r requirements.txt
```

关于 PyTorch 与 PyTorch Geometric（PyG）
- 请先访问 PyTorch 官方安装页选择与你的 CUDA/CPU 环境相匹配的安装命令：
	https://pytorch.org/get-started/locally/
- PyG（torch-geometric）以及其底层依赖（torch-scatter, torch-sparse, torch-cluster, torch-spline-conv）
	需要与本机的 `torch` 版本精确匹配。请参照官方安装说明：
	https://pytorch-geometric.readthedocs.io/en/latest/notes/installation.html

示例（CPU 版本，按需替换）：
```powershell
# 安装 CPU 版 PyTorch（示例）
pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio

# 按 PyG 官方说明安装对应 wheel（示例占位，需替换 torch 标签）：
pip install torch-scatter -f https://data.pyg.org/whl/torch-<torch+cpu-tag>.html
pip install torch-sparse -f https://data.pyg.org/whl/torch-<torch+cpu-tag>.html
pip install torch-cluster -f https://data.pyg.org/whl/torch-<torch+cpu-tag>.html
pip install torch-spline-conv -f https://data.pyg.org/whl/torch-<torch+cpu-tag>.html
pip install torch-geometric
```

快速运行示例（在 `model/neural` 目录下运行）

- 训练：
```powershell
uv run .\train.py --data ../../data/raw_data/compact.csv --countries-meta ./artifacts/countries_meta.json --epochs 10 --batch-size 8
# 或直接
python train.py --data ../../data/raw_data/compact.csv --countries-meta ./artifacts/countries_meta.json
```

- 从任意种子国家生成预测：
```powershell
python predict.py --seed-country USA --checkpoint ./artifacts/checkpoint_gnn_rnn.pt --output ./output/outbreak_forecast.csv
```

- 基于历史窗口生成预测：
```powershell
python predict_outbreak.py --checkpoint ./artifacts/checkpoint_gnn_rnn.pt --data ../../data/raw_data/compact.csv --output ./output/outbreak_forecast.csv
```

- 生成动画（依赖 plotly）：
```powershell
uv run .\epidemic_animation.py --input-csv ./output/outbreak_forecast.csv --output-html ./output/plague_style_animation.html --show
# 或
python epidemic_animation.py --input-csv ./output/outbreak_forecast.csv --output-html ./output/plague_style_animation.html --show
```

重要路径

- 检查点: `artifacts/checkpoint_gnn_rnn.pt`
- 国家元数据: `artifacts/countries_meta.json`
- 输出预测 CSV: `output/outbreak_forecast.csv`
- 动画 HTML: `output/plague_style_animation.html`

故障排查小贴士
- 如果 PyG 安装报错，先确认 `torch` 版本，并严格按照 PyG 官方页面提供的 wheel 安装命令。
- Windows 上建议优先尝试 CPU 版本或使用 conda 环境来避免二进制兼容问题。