from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.chains.llm import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.output_parsers import PydanticOutputParser
from typing import Dict, Any
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import logging
from src.aizen.schemas.agent_config import AgentResponse
from src.aizen.models import UserChat
from sqlalchemy.orm import Session
from src.aizen.database import SessionLocal

load_dotenv(override=True)
db: Session = SessionLocal()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

uniswap_tags = [
    "uniswap-v3",
    "liquidity-boost",
    "pool-power",
    "range-play",
    "tick-master",
    "price-band",
    "mint-magic",
    "exit-strategy",
    "nft-positions",
    "deep-liquidity",
    "fee-hack",
    "price-check",
    "auto-rebalance",
    "time-frame",
    "liq-bounds",
    "liq-spread",
    "loss-guard",
    "slip-proof",
    "max-slip",
    "buffer-zone",
    "time-pad",
    "vol-rebalance",
    "rsi-signal",
    "bolliner-band",
    "macd-move",
    "market-bias",
    "volatility-hit",
    "router-call",
    "liq-agent",
    "yield-flip",
    "smart-liquidity",
    "gas-saver",
    "price-spread",
    "tick-sync",
    "pool-surge",
    "rebalance-bot",
    "fee-track",
    "auto-adjust",
    "market-sense",
    "slip-watch"
]


class UserChatPipeline:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.parser = PydanticOutputParser(pydantic_object=AgentResponse)
        self.memories: Dict[str, ConversationBufferMemory] = {}

        self.prompt = PromptTemplate(
            template="""
        You are a helpful assistant that handles two tasks:
        1. Answer general DeFi and Uniswap V3 questions.
        2. Generate a Uniswap V3 config JSON when the query involves liquidity provision or rebalancing strategy suggestions.

        Always respond in the following format:
        {format_instructions}

        ### RESPONSE GUIDE
        - If the user **asks for explanation or clarification** (e.g., "what does RSI mean?" or "explain in detail"), respond with a **detailed answer**, regardless of length.
        - If the user **asks for a config**, provide a config JSON and an **answer under 100 words**, unless they explicitly request a longer explanation.
        - Do **not** repeat the user’s query in your answer.
        - Put all reasoning and guidance in `answer`, and the config in `config`.

        ### CONFIGURATION GUIDE
        Users may describe their preferences in natural language. Use the following to understand and map their requests:

        - **liquidity_range**:
        - This defines the price range in which liquidity is active.
        - Default behavior: When liquidity range is mentioned, use `lower = 0.04`, `higher = 0.04` (i.e., ±4 percent range).
        - Always try to keep the total spread below ±1.5 (i.e., `lower + higher ≤ 1.5`), unless the user clearly asks for a wider range.
        - If the query is vague, shrink the range conservatively within these limits.

        - **tags**:
        - Give a list of tags from {uniswap_tags}.
        - Give a list of 3 to 4 tags that are relevant to the users input from them.

        - **buffer**:
        - A safety margin added to the liquidity range to avoid frequent rebalances.
        - Example: "Add some buffer to prevent quick range exits" → `buffer = 0.01` (1%).

        - **max_slippage**:
        - Acceptable slippage during swaps or rebalancing.
        - Example: "I want low risk during trades" → lower value like 0.1.
        - "High flexibility" → higher slippage like 0.03 (3%).

        - **time_buffer**:
        - Minimum duration (in minutes) to wait before considering rebalancing again.
        - Example: "Don’t rebalance too frequently" → 60 (1 hour).
        - "I want quick reaction to market changes" → 10 or 15.

        - **rebalance_timeframe**:
        - interval to check this config
        - Example: "Check every 15 minutes" → 15
        - For less Rebalance Frequency keep it high 30 minutes → 30

        - **rebalance_strategies**:
        - Strategies to evaluate rebalancing decisions.
        - You may include any of: `Momentum`, `MACD`, `RSI`, `Moving Average`, `Liquidity Pool API`, `Volatility`, etc.
        - Example: "Use technical indicators like RSI and MACD" → include those in the strategy list.

        - **rebalance_triggers**:
        - Dual-action triggers for entering a new position when the current price deviates significantly.
        - `below`: If price drops below a given threshold (`by`), re-enter with the specified `lower` and `higher` range.
        - `above`: If price rises above a given threshold, enter a new position with its own range.
        - Example: "If price drops by more than 25%, shift to a narrower range" → use `below.by = 2.5`, `lower/higher = 0.04`.
        - If the user doesn't want such dual-trigger logic, omit `rebalance_triggers`.

        ### USER QUERY
        {input}
        """,
            input_variables=["input"],
            partial_variables={"format_instructions": self.parser.get_format_instructions(), "uniswap_tags": uniswap_tags}
        )

    def _get_memory_key(self, user_id: int, agent_id: int) -> str:
        return f"{user_id}_{agent_id or 'default'}"

    def _get_memory(self, user_id: int, agent_id: int) -> ConversationBufferMemory:
        key = self._get_memory_key(user_id, agent_id)
        if key not in self.memories:
            history = self._fetch_chat_history(user_id, agent_id)
            memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
            for entry in history:
                memory.chat_memory.add_user_message(entry["user_query"])
                memory.chat_memory.add_ai_message(entry["response"])
            self.memories[key] = memory
        return self.memories[key]

    def _fetch_chat_history(self, user_id: int, agent_id: int):
        chats = (
            db.query(UserChat)
            .filter(UserChat.user_id == user_id, UserChat.agent_id == agent_id)
            .order_by(UserChat.created_at)
            .all()
        )

        chat_history = [
            {
                "user_query": chat.user_query,
                "response": chat.response["raw"]
            }
            for chat in chats
        ]

        return chat_history

    def _save_chat_history(self, user_id: int, agent_id: int, user_query: str, response: dict):
        new_chat = UserChat(user_id = user_id, agent_id = agent_id, user_query = user_query, response = response)

        db.add(new_chat)
        db.commit()
        

    def handle_chat(self, user_id, user_query, agent_id) -> AgentResponse:
        memory = self._get_memory(user_id, agent_id)

        chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            memory=memory,
            verbose=True
        )
        try:
            result = chain.run(input=user_query)
        except Exception as e:
            logger.error("Error executing %%%%%%%%%%%%%%%%%%%%%")
            logger.error(str(e))

        try:
            parsed = self.parser.parse(result)
            print(parsed)
            return parsed
        except Exception as e:
            raise ValueError(f"Failed to parse LLM output: {e}\nRaw Output:\n{result}")
