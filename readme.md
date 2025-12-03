# PandasQuantLab

PandasQuantLab is a modular framework for quantitative trading in Python.  
It integrates backtesting, strategy development, technical analysis, and live trading into a single, extensible structure. The project is designed for traders and developers who want to build, test, and deploy algorithmic strategies using a clean and scalable architecture.

---

## 🚀 Key Features

### **Backtesting Engine**
- Vectorized backtests based on Pandas.
- Trade tracking, performance metrics, and statistics.
- Automated report generation.
- Plotting utilities for equity curves, drawdowns, signals, and more.

### **Live Trading Module**
- File-based or API-driven signal management.
- Position manager for tracking open and closed trades.
- Order execution module (exchange/broker integration ready).
- Telegram sender for notifications and alerts.

### **Strategies**
- Plug-and-play strategy architecture.
- Easy to extend with custom trading logic.
- Compatible with historical and live data flows.

### **Technical Analysis Toolkit**
Contains multiple submodules:
- **Indicators** – classic technical indicators and custom tools.
- **SMC Components** – Points of Interest (POI), sessions, structure tools.
- **Price Action & Fibonacci Tools** – swing detection, levels, confluence zones.


---

## ⚙️ Goals of the Project
- Provide a clean, understandable, and modern framework for quantitative research.
- Allow fast iteration from strategy idea → backtest → live deployment.
- Support both traditional technical analysis and SMC/price-action-based systems.
- Enable modular expansion without breaking existing workflows.
