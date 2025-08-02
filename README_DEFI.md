# 🚀 Aizen AI DeFi Agents Marketplace

Aizen AI is building a revolutionary AI-agents marketplace for decentralized finance (DeFi), empowering anyone to effortlessly create sophisticated AI agents for liquidity management, trading strategies, and investor portfolio optimization across multiple DeFi categories. The platform initially addresses two key use cases:

- **Liquidity Provider (LP) Rebalancing:** Automated liquidity management for dynamic and efficient liquidity positioning.
- **Low-Churn Investor Portfolio Management:** Automatic portfolio rebalancing optimized for stable, low-turnover investment strategies.

## What We’ve Built

### Overview
The marketplace ecosystem consists of the following core components:


1. **[AI Agent-Based Interaction](#ai-agent-based-interaction)** *(Currently Live)* – A multi-agent framework powered by CrewAI, coordinating specialized agents for user interaction, technical analysis, liquidity strategy execution, trading execution, historical analysis, and more.

2. **[Technical Signals & Alphas](#technical-signals--alphas)** *(Currently Live with core indicators, planned expansion to 100+ indicators.)* – A robust real-time market data module computing key quantitative indicators to drive intelligent decisions. These are passed to AI Agents as tools and can be used by them to take intelligent decisions.

3. **[Web3 DeFi Protocol Management](#web3-defi-protocol-management)** *(Currently Live)* – Automated entry, rebalancing, and exit strategies across multiple DeFi platforms. These connectors are also passed as tools to the AI Agents to help interact with on chain protocols. Currently supporting Uniswap V3, will extend the fucntionality

4. **StratGPT-Powered AI Agents Marketplace** *(Upcoming)* – Allowing easy creation, deployment, and commissioning of AI agents through intuitive natural language instructions.

5. **User-Friendly Dashboards** *(Upcoming)* – Real-time monitoring, robust historical analytics, and transparent agent performance summaries.

6. **Comprehensive Tools Library** *(Upcoming)* – Plans to expand the available signals and technical indicators to over 100, enhancing the precision and efficiency of AI agent decisions.


## AI Agent-Based Interaction

### Overview
The multi-agent framework powered by CrewAI coordinates specialized AI agents:

| Agent                          | Role                            | Core Responsibilities                           |
|--------------------------------|---------------------------------|-------------------------------------------------|
| User Interface Agent 🗣️       | Communication & User Interaction | Handles user inputs, config updates, feedback   |
| Technical Analyst Agent 📊     | Market Data & Signal Analysis   | Real-time analysis, technical indicator generation |
| Liquidity Strategist Agent 💡  | Strategic Execution             | Executes liquidity positioning & rebalancing    |
| Trading Agent 📈 *(Upcoming)*  | Trading Execution               | Executes trade actions based on signals         |
| Historical Analyst Agent 📚 *(Upcoming)* | Threshold Optimization | Chooses optimal thresholds from historical data |
| Backtesting Agent 🔄 *(Upcoming)*| Historical Validation         | Backtests strategies, validates decisions       |


The Aizen AI Liquidity Provider (LP) Rebalancing System is powered by AI agents with a specialized role. These agents work together seamlessly to ensure optimal liquidity management based on real-time market conditions, technical indicators, and user preferences.
Each agent operates with a specific skill set, leveraging market data, trading strategies, and liquidity optimization techniques to execute precise and efficient rebalancing actions.

## Technical Signals & Alphas

### Purpose
Quantitative indicators (alphas) guiding optimal liquidity allocation, market trend identification, and volatility management. These signals are used to adjust liquidity ranges dynamically and identify ideal entry/exit points.

### Key Technical Indicators
### 1. Momentum-Based Indicators

**Relative Strength Index (RSI):**
- Measures momentum strength (overbought/oversold conditions).
- RSI > 70 → Overbought, potential sell/liquidity exit.
- RSI < 30 → Oversold, potential buy/liquidity entry.

**Moving Average Convergence Divergence (MACD):**
- Tracks trend strength & momentum shifts.
- MACD crossover above zero → Bullish trend.
- MACD crossover below zero → Bearish trend.

**Stochastic Oscillator:**
- Compares closing price to historical price range.
- Helps confirm momentum reversals.

### 2. Volatility Indicators

**Bollinger Bands:**
- Identifies price breakouts & reversals.
- Price above upper band → Overextension, possible mean reversion.
- Price below lower band → Undervaluation, potential reversal.

**Average True Range (ATR):**
- Measures market volatility.
- Higher ATR → More volatility, requiring wider liquidity ranges.

**Keltner Channels:**
- Similar to Bollinger Bands but based on ATR instead of standard deviation.
- Helps refine support/resistance zones.

### 3. Trend-Following Indicators

**Simple & Exponential Moving Averages (SMA/EMA):**
- SMA → Longer-term trends.
- EMA → Recent price sensitivity.
- Price above 50-EMA → Uptrend.
- Price below 50-EMA → Downtrend.

**Ichimoku Cloud:**
- Comprehensive trend analysis tool (support/resistance, momentum, breakout levels).
- Price above the cloud → Strong bullish trend.
- Price inside the cloud → Ranging market.
- Price below the cloud → Bearish trend.

**Parabolic SAR (Stop & Reverse):**
- Trailing stop-loss indicator that follows trends.
- Parabolic SAR dots below price → Uptrend.
- Parabolic SAR dots above price → Downtrend.

### 4. Market Structure & Liquidity Metrics

**Fibonacci Retracements:**
- Identifies support/resistance zones based on key retracement levels (23.6%, 38.2%, 50%, 61.8%).
- Used for range adjustments & rebalancing triggers.

**Volume Analysis & On-Balance Volume (OBV):**
- High volume on uptrend → Strong continuation.
- Divergence between price & OBV → Potential trend reversal.

**VWAP (Volume Weighted Average Price):**
- Measures the "fair price" based on volume-weighted trading activity.
- Helps identify accumulation/distribution zones.

**Order Flow & Liquidity Heatmaps:**
- Tracks whale activity & institutional orders.
- Detects buy/sell pressure shifts that can impact liquidity depth.

### Role in the System
These signals collectively inform rebalancing decisions, ensuring that the liquidity provider’s funds remain optimally allocated based on market conditions.


### Comprehensive Tools Library *(Upcoming)*
Plans include expanding to over 100+ technical indicators, signals, and alphas, significantly enhancing decision-making precision across diverse DeFi use cases.

## Web3 DeFi Protocol Management

### Purpose
Automates liquidity management and protocol interactions to maximize yields, mitigate risks, and optimize portfolio performance across DeFi platforms.

### Strategies
- **Entry:** Automated initiation of liquidity positions based on favorable technical signals and expected outcomes
- **Rebalancing:** Dynamic adjustments in response to real-time market movements. This takes into account what a really smart LP would've considered on a regular basis to take decisions
- **Exit:** Automated liquidity exits and collection of rewards based on risk check or outcome checks


## AI Agent Interaction Flows

### Agent Creation Flow
- 1️⃣ User defines AI agent via natural language or simple commands.
- 2️⃣ StratGPT generates initial agent configuration and suggests tools.
- 3️⃣ User refines strategies iteratively through intuitive chat interfaces.
- 4️⃣ User finalizes the agent configuration and deploys with a simple click.

### Marketplace User Flow
- 1️⃣ User searches for agents by intent and filters.
- 2️⃣ Reviews transparent historical agent performance.
- 3️⃣ Commissions preferred agents.
- 4️⃣ Monitors real-time performance via comprehensive dashboards.

Agents created by builders will have distinct personalities, names, and custom images, allowing builders to create engaging, exciting, and easily identifiable AI agents that traders can follow, support, and trust.

### 1. User Interface Agent 🗣️
**Role:**  
Acts as the primary communication layer between the user and the system.  
Translates human-readable instructions into configurations and commands for the other agents.  
Ensures users stay informed about their liquidity positions, market conditions, and system decisions.

**Responsibilities:**  
- ✅ Processes user input
- ✅ Interacts with other agents to trigger analysis and execute strategies.  
- ✅ Logs actions and provides real-time feedback to the user.  
- ✅ Updates the system’s configuration based on user commands.

**Learning & Knowledge:**  
- Conversational AI skills → Understands user commands and responds naturally.  
- Config management → Reads and updates agent settings.  
- Basic trading logic → Knows when to trigger analysis or execute trades.

**Backstory:**  
The User Interface Agent is like an experienced DeFi concierge, always ready to assist traders with real-time insights and actionable decisions. While it doesn’t perform in-depth analysis, it knows exactly who to ask and what to do to get the job done.  
🔹 *“How can I assist with your liquidity today?”*

---

### 2. Technical Analyst Agent 📊
**Role:**  
The brain behind market analysis, responsible for computing trading signals and alphas.  
Continuously tracks price, liquidity depth, volatility, momentum, and order flow.  
Feeds quantitative insights to the Liquidity Strategist Agent for rebalancing decisions.

**Responsibilities:**  
- ✅ Fetches real-time market data (price, volume, volatility).  
- ✅ Computes all major technical indicators (RSI, Bollinger Bands, MACD, Ichimoku Cloud, Fibonacci, VWAP).  
- ✅ Detects momentum shifts, breakouts, and potential reversals.  
- ✅ Provides trend confirmations for liquidity adjustments.  
- ✅ Notifies the Liquidity Strategist Agent when conditions require action.

**Learning & Knowledge:**  
- Advanced Technical Analysis → Understands over 100+ indicators for trend detection and momentum shifts.  
- Quantitative Finance Models → Implements statistical approaches for mean reversion, volatility modeling, and trend confirmation.  

**Backstory:**  
The Technical Analyst Agent is like a seasoned Wall Street quant, meticulously studying market data to find high-probability trading signals. It doesn’t care about user interaction—it just crunches numbers, analyzes trends, and delivers insights needed to make smart liquidity decisions.  
🔹 *“Price nearing range edge, RSI at 65, MACD bullish—consider rebalancing.”*

---

### 3. Liquidity Strategist Agent 💡
**Role:**  
The execution layer of the system—takes market insights and translates them into actionable liquidity strategies.  
Ensures liquidity positions remain optimal while minimizing impermanent loss and maximizing yield efficiency.  
Continuously refines entry, exit, and rebalancing logic based on market conditions and risk settings.

**Responsibilities:**  
- ✅ Decides when to enter, adjust, or exit a liquidity position.  
- ✅ Optimizes liquidity ranges dynamically based on volatility and price action.  
- ✅ Implements risk-mitigation techniques (e.g., widening ranges in high volatility).  
- ✅ Ensures LP positions align with user-defined constraints (e.g., slippage tolerance).  
- ✅ Coordinates with the Technical Analyst Agent to confirm trading signals before acting.

**Learning & Knowledge:**  
- DeFi Market Microstructure → Understands liquidity provision mechanisms across protocols.  
- Risk & Portfolio Management → Minimizes impermanent loss, manages risk exposure effectively.  
- Liquidity Pool Optimization → Dynamically adjusts price ranges for optimal yield efficiency.  

**Backstory:**  
The Liquidity Strategist Agent is like a hedge fund portfolio manager, constantly evaluating risk versus reward and making calculated moves to enhance capital efficiency. While it relies on the Technical Analyst Agent for insights, the final decision on rebalancing, entry, and exit strategies rests with this agent.  
🔹 *“Market volatility rising—adjusting range dynamically for optimal yield.”*

## 🏗️ What's Next?
- **Marketplace Development:**
  - Intuitive StratGPT-powered agent creation.
  - Bonding curve economics for early adopters.
  - Real-time and historical performance dashboards.

- **Expanded AI-driven Rebalancing Strategies:**
  - Integration with broader DEX platforms (Trader Joe, PancakeSwap, SushiSwap).
  - Expansion to 100+ technical indicators.
  - Advanced volatility metrics and heuristic-driven decisions.

- **Enhanced User & Builder Experience:**
  - Refined chat interfaces for iterative strategy building.
  - Robust analytics, transparent summaries.

- **Future Integrations & Optimizations:**
  - Advanced backtesting and portfolio orchestration.
  - Expansion into weighted pools, stablecoin pools, lending platforms

- **Robust React-Based Frontend:**
  - Secure user authentication and profile management.
  - Interactive dashboards supporting both agent builders and traders.
  - Comprehensive historical data visualization and performance tracking.
  - Simplified, intuitive user flows for agent creation, discovery, commissioning, and ongoing performance monitoring.

## Installation & Usage
```sh
pip install crewai fastapi yfinance pandas_ta
uvicorn main:app --reload
```
