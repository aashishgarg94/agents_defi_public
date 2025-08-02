from langchain_openai.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains.llm import LLMChain
from langchain.output_parsers import PydanticOutputParser
from langchain.memory import ConversationBufferMemory
from src.aizen.schemas.rebalance_decision import RebalanceDecision
import json, os

# Indicator reference dictionary
indicator_reference = {
    "Rsi": {
        "description": "RSI (Relative Strength Index) is a momentum oscillator that helps identify if an asset is overbought or oversold based on recent price movements. Values closer to 100 indicate overbought conditions, while values closer to 0 suggest oversold conditions. It is useful in spotting potential reversals or trend exhaustion.",
        "fields": ["rsi"]
    },
    "Bollinger Bands": {
        "description": "Bollinger Bands are a set of three lines that measure price volatility. The middle band is a moving average, while the upper and lower bands represent standard deviations. When the price is near the upper band, the asset may be relatively expensive; when it's near the lower band, it may be relatively cheap. This helps determine if liquidity should be repositioned.",
        "fields": ["bb_upper", "bb_middle", "bb_lower"]
    },
    "MACD": {
        "description": "MACD (Moving Average Convergence Divergence) helps identify trend direction and momentum by comparing short- and long-term EMAs. The signal line helps spot changes in trend, and the histogram shows the difference between MACD and signal, helping detect early momentum shifts.",
        "fields": ["macd", "macd_signal", "macd_histogram"]
    },
    "ATR": {
        "description": "ATR (Average True Range) measures volatility by capturing how much the price moves over a period. High ATR means large price swings (high volatility); low ATR means smaller, more stable movements. Useful for adjusting liquidity ranges to avoid frequent rebalancing in volatile markets.",
        "fields": ["atr"]
    },
    "Volatility": {
        "description": "Volatility measures how much the price deviates from its average, often represented as a standard deviation. It helps the agent understand market uncertainty and potential risk. High volatility might call for wider liquidity bands, while low volatility allows for tighter ranges.",
        "fields": ["volatility"]
    },
    "VWAP": {
        "description": "VWAP (Volume Weighted Average Price) gives the average price of an asset weighted by volume. It helps determine if the current price is favorable compared to where most trading has occurred. Prices significantly above or below VWAP can signal overvaluation or undervaluation.",
        "fields": ["vwap"]
    },
    "Price Range": {
        "description": "Price Range is the spread between the high and low prices over a time period. It helps assess how much the asset is fluctuating and supports decisions on how wide a liquidity range should be. A narrow range implies stability; a wide range implies movement.",
        "fields": ["price_range"]
    }
}


class LiquidityRebalancingPipeline:
    def __init__(self):
        # Initialize LLM and Pydantic parser
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.parser = PydanticOutputParser(pydantic_object=RebalanceDecision)

        # Build prompt with format instructions
        self.prompt = PromptTemplate(
        template="""
        {format_instructions}

        You are a Uniswap V3 liquidity rebalancing analyst.
        Given the pool configuration and latest market data, output JSON matching exactly the RebalanceDecision schema.

        ### Pool Configuration
        This includes user preferences such as liquidity amounts, slippage tolerance, and rebalance strategies.
        You must consider the `rebalance_strategies` field from this config to determine which indicators are relevant.

        ```json
        {config_json}
        ```

        ### Market Data
        This includes the current price and all evaluated indicator values at the current timestamp.

        ```json
        {price_json}
        ```

        ### Indicator Reference
        This provides detailed descriptions of each technical indicator used in the market data to help you reason about trends.

        ```json
        {indicator_reference_json}
        ```

        Use these inputs to provide an informed market bias (`bias`) in percentage format (e.g., 0.1 for +10%, -0.05 for -5%). 
        Explain briefly _why_ the bias is positive or negative based on the indicators.
        """,
            input_variables=["config_json", "price_json", "indicator_reference_json"],
            partial_variables={
                "format_instructions": self.parser.get_format_instructions()
            }
        )



    def rebalance_now(self, config: dict, price_data: dict, memory: ConversationBufferMemory = None) -> RebalanceDecision:
        # Serialize inputs to JSON
        config_json = json.dumps(config, indent=2)
        price_json = json.dumps(price_data, indent=2)
        indicator_json = json.dumps(indicator_reference, indent=2)

        # Build LLMChain each call to include memory and verbose
        chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            memory=memory,
            verbose=True
        )

        # Run chain
        raw_output = None
        try:
            raw_output = chain.run(
                config_json=config_json,
                price_json=price_json,
                indicator_reference_json=indicator_json
            )
        except Exception as e:
            print(f"[LLM Error] {str(e)}")
            return None

        try:
            decision = self.parser.parse(raw_output)
            return decision
        except Exception as e:
            print(f"[Parser Error] {str(e)}")
            print(f"[LLM Raw Output] {raw_output}")
            return None