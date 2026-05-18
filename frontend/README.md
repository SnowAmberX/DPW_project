# 新冠疫情与疫苗可视化

## 当前页面结构

- 首页：`src/pages/home/index.vue`
- 新冠疫情与疫苗接种概况：`src/pages/overview/index.vue`
- 疫苗接种情况与新增病例：`src/pages/cases-vaccination/index.vue`
- 疫苗接种情况与死亡率：`src/pages/mortality-vaccination/index.vue`
- 预测未来新疫情：`src/pages/prediction/index.vue`

## 路由

路由定义在 `src/router/index.js`：

- `/`
- `/overview`
- `/cases-vaccination`
- `/mortality-vaccination`
- `/prediction`

## 疫苗与死亡率页面（Python 图表）

该页面采用“Python 生成静态 HTML + 前端 iframe 嵌入”模式：

- Python 脚本目录：`src/pages/mortality-vaccination/python_charts/`
- 批量生成入口：`src/pages/mortality-vaccination/python_charts/build_all.py`
- 输出目录：`public/python-viz/`
- 前端展示组件：`src/pages/mortality-vaccination/MortalityVaccinationCharts.vue`

### Python 依赖

请确保 Python 环境安装：

```bash
pip install pandas plotly
```

### 生成图表

```bash
python src/pages/mortality-vaccination/python_charts/build_all.py
```

## 本地运行前端

```bash
npm install
npm run dev
```

默认开发地址：`http://localhost:5173`

## 构建产物

- 前端构建命令：`npm run build`
- 构建输出目录：`dist/`
