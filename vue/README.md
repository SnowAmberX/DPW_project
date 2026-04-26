# 新冠疫情与疫苗可视化（Vue 前端）

## 页面结构

- 首页：`src/pages/HomePage.vue`
- 新冠疫情与疫苗接种概况：`src/pages/OverviewPage.vue`
- 疫苗接种情况与新增病例：`src/pages/CasesVaccinationPage.vue`
- 疫苗接种情况与死亡率：`src/pages/MortalityVaccinationPage.vue`
- 预测未来新疫情：`src/pages/PredictionPage.vue`

## 图表目录（按页面分开）

- `src/charts/home/`
- `src/charts/overview/`
- `src/charts/cases-vaccination/`
- `src/charts/mortality-vaccination/`
- `src/charts/prediction/`

## Python 代码接入方式

### 方式 A：导出 HTML 后前端 iframe 引入

1. 组员在 Python 中导出图表 HTML（如 Plotly、Pyecharts）。
2. 放到后端静态服务或可访问 URL。
3. 在对应 `*Charts.vue` 文件中给 `PythonVizFrame` 的 `src` 传 URL。

### 方式 B：后端提供 JSON API，前端渲染

1. Python 后端暴露接口，例如：
   - `/api/overview`
   - `/api/cases-vaccination`
   - `/api/mortality-vaccination`
   - `/api/prediction`
2. 在 `src/api/vizApi.js` 已预留请求函数。
3. 页面/图表组件里调用这些函数并渲染成 ECharts/Chart.js/Vega 等。

## 本地启动（需要 npm 可用）

```bash
npm install
npm run dev
```

> 你当前环境里 `npm` 命令不可用（Node 已安装），建议修复 Node PATH 或重装 Node.js（含 npm）后再运行。
