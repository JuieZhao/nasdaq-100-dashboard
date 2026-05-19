#!/usr/bin/env python3
"""
NASDAQ 100 实时仪表盘 — Glassmorphism UI (PySide6 + QWebEngine + Chart.js)
数据源: yfinance (Yahoo Finance, 15分钟延迟)
"""

import sys, json, time, threading
from datetime import datetime

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt, QUrl, QObject, Signal, Slot, QThread
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

import yfinance as yf

# ── NASDAQ 100 成分股 ───────────────────────────────────
NDX_TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","AVGO","TSLA","COST",
    "NFLX","AMD","PEP","ADBE","LIN","CSCO","TXN","QCOM","INTU","AMAT",
    "ISRG","CMCSA","AMGN","HON","BKNG","ADP","GILD","PANW","VRTX","SBUX",
    "ADI","MU","LRCX","MELI","MDLZ","REGN","KLAC","CRWD","SNPS","CDNS",
    "ASML","CTAS","MAR","ORLY","CSX","ABNB","PCAR","WDAY","ROP","NXPI",
    "FTNT","CPRT","ADSK","CEG","CHTR","DASH","AZN","ODFL","KDP","MNST",
    "DDOG","MCHP","IDXX","KHC","FAST","GEHC","BKR","XEL","VRSK","EXC",
    "CTSH","EA","CCEP","BIIB","DXCM","ANSS","TTD","TEAM","ZS","WBD",
    "TTWO","CDW","MDB","FANG","CSGP","PDD","LULU","ILMN","ON","SMCI",
    "GFS","WBA","ARM","DLTR","ROST","PAYX","SIRI","SGEN",
]
NDX_TICKERS = list(dict.fromkeys(NDX_TICKERS))  # 去重

# ── HTML 模板 ──────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>NASDAQ 100 Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<script>tailwind.config={darkMode:'class'}</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*{font-family:'Inter','Microsoft YaHei',sans-serif;margin:0;padding:0;box-sizing:border-box}
body{background:linear-gradient(135deg,#0a0a1a,#0f172a,#1a1a2e);min-height:100vh;color:#e2e8f0;overflow-x:hidden}
body::before{content:'';position:fixed;top:-30%;left:-30%;width:160%;height:160%;
 background:radial-gradient(circle at 30% 20%,rgba(59,130,246,0.08) 0%,transparent 40%),
  radial-gradient(circle at 70% 60%,rgba(139,92,246,0.06) 0%,transparent 40%),
  radial-gradient(circle at 50% 90%,rgba(236,72,153,0.05) 0%,transparent 40%);
 z-index:0}
.glass{background:rgba(15,23,42,0.55);backdrop-filter:blur(24px) saturate(180%);-webkit-backdrop-filter:blur(24px) saturate(180%);
 border:1px solid rgba(255,255,255,0.06);border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,0.2)}
.glass-card{background:rgba(30,41,59,0.5);backdrop-filter:blur(16px) saturate(150%);-webkit-backdrop-filter:blur(16px) saturate(150%);
 border:1px solid rgba(255,255,255,0.05);border-radius:14px;padding:18px;transition:all .2s}
.glass-card:hover{background:rgba(30,41,59,0.7);border-color:rgba(255,255,255,0.1);transform:translateY(-1px)}

.price-up{color:#22c55e}.price-down{color:#ef4444}
.change-badge{font-size:13px;font-weight:600;padding:4px 10px;border-radius:8px;display:inline-flex;align-items:center;gap:4px}
.change-up{background:rgba(34,197,94,0.15);color:#22c55e}
.change-down{background:rgba(239,68,68,0.15);color:#ef4444}

.ticker-row{display:flex;align-items:center;gap:12px;padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.03);
 transition:all .15s;cursor:default}
.ticker-row:hover{background:rgba(59,130,246,0.06)}
.ticker-symbol{font-weight:700;font-size:13px;width:64px;color:#e2e8f0}
.ticker-name{font-size:12px;color:#94a3b8;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ticker-price{font-weight:600;font-size:13px;width:90px;text-align:right}
.ticker-change{font-weight:600;font-size:12px;width:80px;text-align:right}

.time-badge{background:rgba(59,130,246,0.1);color:#60a5fa;font-size:11px;padding:3px 8px;border-radius:6px}

.section-title{font-size:13px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px}

.chart-tab{padding:5px 12px;border-radius:8px;font-size:11px;cursor:pointer;color:#64748b;transition:all .15s;
 background:rgba(255,255,255,0.02);border:1px solid transparent}
.chart-tab.active{background:rgba(59,130,246,0.15);color:#60a5fa;border-color:rgba(59,130,246,0.3)}
.chart-tab:hover:not(.active){color:#94a3b8;background:rgba(255,255,255,0.04)}

.spark{display:inline-block;width:70px;height:22px;margin-left:8px}

@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.loading{animation:pulse 1.5s ease infinite}

@keyframes slideUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.slide-up{animation:slideUp .35s ease}

::-webkit-scrollbar{width:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.08);border-radius:4px}
::-webkit-scrollbar-thumb:hover{background:rgba(255,255,255,0.15)}
</style>
</head>
<body>
<div class="relative z-10 max-w-7xl mx-auto p-4 space-y-3">

<!-- Header -->
<div class="glass-card flex items-center justify-between slide-up">
  <div class="flex items-center gap-3">
    <div class="w-11 h-11 rounded-xl flex items-center justify-center" style="background:linear-gradient(135deg,#3b82f6,#8b5cf6)">
      <span class="text-xl">📊</span>
    </div>
    <div>
      <h1 class="text-lg font-bold tracking-tight text-white">NASDAQ 100</h1>
      <p class="text-xs text-slate-400">实时仪表盘 · 15分钟延迟</p>
    </div>
  </div>
  <div class="text-right">
    <div class="flex items-center gap-2 justify-end">
      <span id="idxPrice" class="text-2xl font-extrabold text-white loading">--</span>
      <span id="idxChange" class="change-badge loading">--</span>
    </div>
    <div class="mt-1 text-xs text-slate-500" id="idxMeta">--</div>
  </div>
</div>

<!-- Chart -->
<div class="glass-card slide-up" style="animation-delay:.05s">
  <div class="flex items-center justify-between mb-3">
    <span class="section-title">📈 指数走势</span>
    <div class="flex gap-1" id="chartTabs">
      <span class="chart-tab active" data-range="1d">1D</span>
      <span class="chart-tab" data-range="5d">5D</span>
      <span class="chart-tab" data-range="1mo">1M</span>
      <span class="chart-tab" data-range="3mo">3M</span>
      <span class="chart-tab" data-range="6mo">6M</span>
      <span class="chart-tab" data-range="1y">1Y</span>
    </div>
  </div>
  <div style="height:260px"><canvas id="mainChart"></canvas></div>
</div>

<!-- 3-column grid: Gainers | Losers | Components -->
<div class="grid grid-cols-3 gap-3">

<!-- Gainers -->
<div class="glass-card slide-up col-span-1" style="animation-delay:.1s">
  <span class="section-title">🔥 涨幅榜</span>
  <div id="gainersList"><div class="text-xs text-slate-500 py-8 text-center loading">加载中...</div></div>
</div>

<!-- Losers -->
<div class="glass-card slide-up col-span-1" style="animation-delay:.15s">
  <span class="section-title">📉 跌幅榜</span>
  <div id="losersList"><div class="text-xs text-slate-500 py-8 text-center loading">加载中...</div></div>
</div>

<!-- Components Table -->
<div class="glass-card slide-up col-span-1" style="animation-delay:.2s;max-height:460px;overflow:hidden;display:flex;flex-direction:column">
  <div class="flex items-center justify-between mb-2">
    <span class="section-title">📋 成分股</span>
    <input id="filterInput" class="text-xs bg-transparent border border-solid border-white/10 rounded-lg px-3 py-1.5 text-slate-300 w-28 outline-none focus:border-blue-500/50"
     placeholder="筛选..." oninput="filterComponents()">
  </div>
  <div id="componentsList" style="flex:1;overflow-y:auto;margin:-10px -18px 0 -18px;padding:0 18px">
    <div class="text-xs text-slate-500 py-8 text-center loading">加载中...</div>
  </div>
</div>

</div>

<!-- Footer -->
<div class="text-center text-xs text-slate-600 pb-2 slide-up" style="animation-delay:.25s">
  <span id="updateTime">--</span> · 数据源: Yahoo Finance · 仅供参考
</div>

</div>

<script>
let mainChart = null;
let bridge = null;
let allComponents = [];

// ── QWebChannel ──
new QWebChannel(qt.webChannelTransport, function(ch){
  bridge = ch.objects.bridge;
  bridge.dataReady.connect(function(dataJson){
    let d = JSON.parse(dataJson);
    renderAll(d);
  });
  bridge.refreshStatus.connect(function(msg){
    document.getElementById('updateTime').textContent = msg;
  });
});

function renderAll(data){
  document.getElementById('idxPrice').textContent = formatPrice(data.index.price);
  document.getElementById('idxPrice').classList.remove('loading');

  let chg = data.index.change;
  let chgPct = data.index.changePercent;
  let isUp = chg >= 0;
  let badge = document.getElementById('idxChange');
  badge.innerHTML = (isUp?'▲':'▼')+' '+Math.abs(chg).toFixed(2)+' ('+chgPct.toFixed(2)+'%)';
  badge.className = 'change-badge '+(isUp?'change-up':'change-down');
  badge.classList.remove('loading');

  let metaText = '开盘 '+formatPrice(data.index.open)+
    ' · 最高 '+formatPrice(data.index.high)+
    ' · 最低 '+formatPrice(data.index.low)+
    ' · 52周 '+formatPrice(data.index.low52)+' - '+formatPrice(data.index.high52);
  document.getElementById('idxMeta').textContent = metaText;

  renderChart(data.history);
  renderGainers(data.components);
  renderLosers(data.components);
  allComponents = data.components;
  renderComponents(allComponents);
}

function formatPrice(p){
  if(p===null||p===undefined)return'--';
  return p>=1000?p.toLocaleString('en-US',{maximumFractionDigits:0}):p.toFixed(2);
}

// ── Chart ──
function renderChart(history){
  if(!history||!history.length)return;
  let labels=history.map(h=>h.date), prices=history.map(h=>h.close);
  let isGreen=prices.length>1&&prices[prices.length-1]>=prices[0];
  let color=isGreen?'#22c55e':'#ef4444';

  let ctx=document.getElementById('mainChart').getContext('2d');
  if(mainChart)mainChart.destroy();

  let gradient=ctx.createLinearGradient(0,0,0,260);
  gradient.addColorStop(0,isGreen?'rgba(34,197,94,0.15)':'rgba(239,68,68,0.15)');
  gradient.addColorStop(1,'rgba(15,23,42,0)');

  mainChart=new Chart(ctx,{
    type:'line',
    data:{labels,datasets:[{data:prices,borderColor:color,borderWidth:2,
      backgroundColor:gradient,fill:true,pointRadius:0,pointHoverRadius:4,
      pointHoverBackgroundColor:color,tension:.3}]},
    options:{
      responsive:true,maintainAspectRatio:false,interaction:{intersect:false,mode:'index'},
      plugins:{legend:{display:false},tooltip:{
        backgroundColor:'rgba(15,23,42,0.9)',titleColor:'#94a3b8',bodyColor:'#e2e8f0',
        borderColor:'rgba(255,255,255,0.1)',borderWidth:1,cornerRadius:8,
        callbacks:{label:function(c){return'$'+c.raw.toLocaleString()}}}} ,
      scales:{
        x:{grid:{display:false},ticks:{color:'#475569',maxTicksLimit:8,font:{size:10}}},
        y:{grid:{color:'rgba(255,255,255,0.04)'},ticks:{color:'#475569',font:{size:10},
          callback:function(v){return v>=1000?(v/1000).toFixed(1)+'k':v}}}
      }
    }
  });
}

// ── Gainers / Losers ──
function renderGainers(components){
  let sorted=[...components].sort((a,b)=>b.changePercent-a.changePercent).slice(0,5);
  document.getElementById('gainersList').innerHTML=sorted.map(c=>renderTicker(c)).join('');
}
function renderLosers(components){
  let sorted=[...components].sort((a,b)=>a.changePercent-b.changePercent).slice(0,5);
  document.getElementById('losersList').innerHTML=sorted.map(c=>renderTicker(c)).join('');
}
function renderTicker(c){
  let up=c.changePercent>=0, cls=up?'price-up':'price-down';
  let sign=up?'+':'';
  return '<div class="ticker-row">'+
    '<span class="ticker-symbol">'+c.symbol+'</span>'+
    '<span class="ticker-name">'+c.name+'</span>'+
    '<span class="ticker-price">'+formatPrice(c.price)+'</span>'+
    '<span class="ticker-change '+cls+'">'+sign+c.changePercent.toFixed(2)+'%</span>'+
    '</div>';
}
function renderComponents(comps){
  let html=comps.map(c=>renderTicker(c)).join('');
  if(!html)html='<div class="text-xs text-slate-500 py-8 text-center">无匹配结果</div>';
  document.getElementById('componentsList').innerHTML='<div>'+html+'</div>';
}
function filterComponents(){
  let q=document.getElementById('filterInput').value.toLowerCase();
  let filtered=allComponents.filter(c=>
    c.symbol.toLowerCase().includes(q)||c.name.toLowerCase().includes(q));
  renderComponents(filtered);
}

// ── Chart tabs ──
document.addEventListener('DOMContentLoaded',function(){
  document.getElementById('chartTabs').addEventListener('click',function(e){
    if(!e.target.classList.contains('chart-tab'))return;
    document.querySelectorAll('.chart-tab').forEach(t=>t.classList.remove('active'));
    e.target.classList.add('active');
    if(bridge)bridge.setRange(e.target.dataset.range);
  });
});

// ── Auto refresh ──
setInterval(function(){if(bridge)bridge.refresh()},60000);
</script>
</body>
</html>"""


# ── Python 桥接对象 ──────────────────────────────────────
class Bridge(QObject):
    dataReady = Signal(str)
    refreshStatus = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ticker = "^NDX"
        self._range = "1d"
        self._tickers = NDX_TICKERS
        self._worker = None

    @Slot()
    def refresh(self):
        self._fetch_data()

    @Slot(str)
    def setRange(self, range_str):
        self._range = range_str
        self._fetch_data()

    def initial_fetch(self):
        self._fetch_data()

    def _fetch_data(self):
        if self._worker and self._worker.isRunning():
            return
        self._worker = DataWorker(self._ticker, self._tickers, self._range)
        self._worker.data_ready.connect(self.dataReady)
        self._worker.status_update.connect(self.refreshStatus)
        self._worker.start()


class DataWorker(QThread):
    data_ready = Signal(str)
    status_update = Signal(str)

    def __init__(self, ticker, tickers, range_str):
        super().__init__()
        self.ticker = ticker
        self.tickers = tickers
        self.range_str = range_str

    def run(self):
        try:
            # 指数数据
            idx = yf.Ticker(self.ticker)
            info = idx.info

            index_data = {
                "price": info.get("regularMarketPrice") or info.get("previousClose"),
                "change": info.get("regularMarketChange", 0),
                "changePercent": info.get("regularMarketChangePercent", 0),
                "open": info.get("regularMarketOpen"),
                "high": info.get("regularMarketDayHigh") or info.get("dayHigh"),
                "low": info.get("regularMarketDayLow") or info.get("dayLow"),
                "high52": info.get("fiftyTwoWeekHigh"),
                "low52": info.get("fiftyTwoWeekLow"),
            }

            # 历史数据
            history = yf.download(self.ticker, period=self.range_str, interval=self._interval(self.range_str),
                                   progress=False, auto_adjust=True)
            hist_list = []
            if not history.empty:
                close_col = "Close" if "Close" in history.columns else history.columns[3]
                for i, row in history.iterrows():
                    ts = i.date() if hasattr(i, 'date') else str(i)
                    hist_list.append({"date": str(ts), "close": float(row[close_col])})

            # 成分股 — 逐个获取 (保证数据完整)
            comp_info = {}
            for t_idx, t in enumerate(self.tickers[:20]):  # Top 20 for gainers/losers display
                try:
                    t_info = yf.Ticker(t).info
                    price = t_info.get("regularMarketPrice")
                    prev = t_info.get("previousClose") or t_info.get("regularMarketPreviousClose")
                    change_pct = 0
                    if price and prev and prev != 0:
                        change_pct = ((price - prev) / prev) * 100
                    comp_info[t] = {"price": price, "changePercent": change_pct}
                except Exception:
                    comp_info[t] = {"price": None, "changePercent": 0}

            # Build component list
            components = []
            for t in self.tickers:
                ci = comp_info.get(t, {})
                name = self._ticker_names().get(t, t)
                components.append({
                    "symbol": t,
                    "name": name,
                    "price": ci.get("price"),
                    "changePercent": ci.get("changePercent", 0),
                })
            components.sort(key=lambda x: x.get("changePercent", 0) or 0, reverse=True)

            result = json.dumps({
                "index": index_data,
                "history": hist_list,
                "components": components,
            }, default=str)

            self.data_ready.emit(result)
            self.status_update.emit(datetime.now().strftime("%H:%M:%S"))

        except Exception as e:
            self.status_update.emit(f"⚠️ {e}")

    def _interval(self, r):
        mapping = {"1d": "5m", "5d": "15m", "1mo": "1h", "3mo": "1d", "6mo": "1d", "1y": "1d"}
        return mapping.get(r, "1h")

    def _ticker_names(self):
        return {
            "AAPL": "Apple Inc.", "MSFT": "Microsoft Corp.", "NVDA": "NVIDIA Corp.",
            "AMZN": "Amazon.com Inc.", "META": "Meta Platforms", "GOOGL": "Alphabet Class A",
            "GOOG": "Alphabet Class C", "AVGO": "Broadcom Inc.", "TSLA": "Tesla Inc.",
            "COST": "Costco Wholesale", "NFLX": "Netflix Inc.", "AMD": "Advanced Micro Devices",
            "PEP": "PepsiCo Inc.", "ADBE": "Adobe Inc.", "LIN": "Linde plc",
            "CSCO": "Cisco Systems", "TXN": "Texas Instruments", "QCOM": "Qualcomm Inc.",
            "INTU": "Intuit Inc.", "AMAT": "Applied Materials", "ISRG": "Intuitive Surgical",
            "CMCSA": "Comcast Corp.", "AMGN": "Amgen Inc.", "HON": "Honeywell Intl.",
            "BKNG": "Booking Holdings", "ADP": "Automatic Data Proc.", "GILD": "Gilead Sciences",
            "PANW": "Palo Alto Networks", "VRTX": "Vertex Pharma.", "SBUX": "Starbucks Corp.",
            "ADI": "Analog Devices", "MU": "Micron Technology", "LRCX": "Lam Research",
            "MELI": "MercadoLibre", "MDLZ": "Mondelez Intl.", "REGN": "Regeneron Pharma.",
            "KLAC": "KLA Corp.", "CRWD": "CrowdStrike Holdings", "SNPS": "Synopsys Inc.",
            "CDNS": "Cadence Design Sys.", "ASML": "ASML Holding", "CTAS": "Cintas Corp.",
            "MAR": "Marriott Intl.", "ORLY": "O'Reilly Automotive", "CSX": "CSX Corp.",
            "ABNB": "Airbnb Inc.", "PCAR": "PACCAR Inc.", "WDAY": "Workday Inc.",
            "ROP": "Roper Technologies", "NXPI": "NXP Semiconductors", "FTNT": "Fortinet Inc.",
            "CPRT": "Copart Inc.", "ADSK": "Autodesk Inc.", "CEG": "Constellation Energy",
            "CHTR": "Charter Comm.", "DASH": "DoorDash Inc.", "AZN": "AstraZeneca",
            "ODFL": "Old Dominion Freight", "KDP": "Keurig Dr Pepper", "MNST": "Monster Beverage",
            "DDOG": "Datadog Inc.", "MCHP": "Microchip Technology", "IDXX": "IDEXX Labs",
            "KHC": "Kraft Heinz", "FAST": "Fastenal Co.", "GEHC": "GE HealthCare",
            "BKR": "Baker Hughes", "XEL": "Xcel Energy", "VRSK": "Verisk Analytics",
            "EXC": "Exelon Corp.", "CTSH": "Cognizant Tech.", "EA": "Electronic Arts",
            "CCEP": "Coca-Cola Europacific", "BIIB": "Biogen Inc.", "DXCM": "DexCom Inc.",
            "ANSS": "ANSYS Inc.", "TTD": "The Trade Desk", "TEAM": "Atlassian Corp.",
            "WBD": "Warner Bros. Discovery", "TTWO": "Take-Two Interactive",
            "CDW": "CDW Corp.", "MDB": "MongoDB Inc.", "FANG": "Diamondback Energy",
            "CSGP": "CoStar Group", "PDD": "PDD Holdings", "LULU": "Lululemon Athletica",
            "ILMN": "Illumina Inc.", "ON": "ON Semiconductor", "SMCI": "Super Micro Computer",
            "GFS": "GlobalFoundries", "WBA": "Walgreens Boots", "DLTR": "Dollar Tree",
            "ROST": "Ross Stores", "PAYX": "Paychex Inc.", "SIRI": "Sirius XM",
            "SGEN": "Seagen Inc.",
        }


# ── 主窗口 ────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NASDAQ 100 Dashboard")
        self.resize(1200, 860)
        self.setMinimumSize(900, 700)
        self._center()

        self.webview = QWebEngineView()
        self.channel = QWebChannel()
        self.bridge = Bridge(self)
        self.channel.registerObject("bridge", self.bridge)
        self.webview.page().setWebChannel(self.channel)
        self.webview.setHtml(HTML)

        self.setCentralWidget(self.webview)

        # 初始加载
        self.webview.loadFinished.connect(lambda ok: self.bridge.initial_fetch() if ok else None)

    def _center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NASDAQ 100 Dashboard")
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
