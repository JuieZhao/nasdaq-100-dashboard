# 📊 NASDAQ 100 实时仪表盘

Glassmorphism 毛玻璃 UI · 实时数据 · 交互式图表

## ✨ 功能

- 📈 **指数走势图** — 1D / 5D / 1M / 3M / 6M / 1Y 切换，渐变色曲线
- 🔥 **涨幅榜 / 跌幅榜** — NASDAQ 100 成分股 Top 5 实时涨跌
- 📋 **可筛选成分股表** — 按代码/公司名筛选，实时排序
- ⏱️ **自动刷新** — 每 60 秒自动拉取最新行情
- 🎨 **毛玻璃 UI** — 深色主题，渐变背景 + 动画光斑

## 🚀 使用

```bash
pip install -r requirements.txt
python dashboard.py
# 或双击 启动.bat
```

## 📋 系统要求

- Python 3.12+
- 网络连接（Yahoo Finance API）

## 📦 依赖

- PySide6 — Qt6 WebEngine 桌面框架
- yfinance — Yahoo Finance 行情数据

## ⚠️ 免责声明

数据有 15 分钟延迟，仅供研究参考，不构成投资建议。
