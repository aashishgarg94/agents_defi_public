from fastapi import FastAPI, HTTPException, Depends, Query, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import os
from pydantic import BaseModel
from typing import List, Dict, Any
from decimal import Decimal
from dotenv import load_dotenv
from src.aizen.pipelines import UserChatPipeline, LiquidityRebalancingPipeline
import jwt
from eth_account.messages import encode_defunct
from eth_account import Account
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import LargeBinary, func, literal_column, cast, Date
from src.aizen.database import get_db
from src.aizen.schemas.user import MyAgent, ChatRequest 
from src.aizen.models import User, Agent, UserCommission, UserChat, AgentHistory, UserDailyCloneFee, UserDailyEarnedFee, AgentDailyStat, UserDailyStat
from src.aizen.schemas.user_commission import CreateUserCommission, UpdateCommission, UpdateAmountEth
from src.aizen.schemas.agent import BuildAgentRequest, DEFAULT_CONFIG, GetAgent, DeployAgent, DeleteAgent, CloneAgent
from src.aizen.schemas.analytics import DailyFeeAnalyticsRequest, DailyFeeAnalyticsResponse
from web3 import Web3
import random, json, base64, io, ast
from PIL import Image


load_dotenv(override=True)

# from src.aizen.agents.crew import LPRebalancing

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ACCOUNT_ADDRESS = os.getenv("ACCOUNT_ADDRESS")
TOKEN_SECRET = os.getenv("JWT_SECRET", "supersecret")
PERFORMANCE = ["High", "Moderate", "Very High", "Low"]
IMAGE_URL = ['https://cdn.prod.website-files.com/63974a9c19a1dd54281c47a8/64d0b5970be523e3ea00fe44_AI-Agents.webp',
             'https://smythos.com/wp-content/uploads/2024/10/friendly-robot-laptop-office.jpeg',
             'https://www.augmentir.com/wp-content/uploads/2024/11/ai-agent.webp']


if not os.getenv("OPENAI_API_KEY") or not PRIVATE_KEY or not ACCOUNT_ADDRESS:
    raise ValueError("required env variables not set")

w3 = Web3(Web3.HTTPProvider("https://sepolia.infura.io/v3/35be664c4dfe4302abed873f7a231f42"))

# Initialize FastAPI app
app = FastAPI(title="Uniswap V3 LP Rebalancing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://sparkling-creponne-2d042d.netlify.app", "https://ai-zen.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"] 
)

def generate_jwt(wallet_address: str):
    payload = {
        "sub": wallet_address,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, TOKEN_SECRET, algorithm="HS256")

def resize_image(image_bytes: bytes, content_type: str, max_size=(512, 512), quality=70):
    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception:
        raise ValueError("Invalid image format")

    image_format = content_type.split("/")[-1].upper()
    if image_format == "JPG":
        image_format = "JPEG"  # Pillow expects "JPEG", not "JPG"

    image = image.convert("RGB")
    image.thumbnail(max_size, Image.Resampling.LANCZOS)

    output_io = io.BytesIO()
    image.save(output_io, format=image_format, quality=quality)

    return output_io.getvalue()

def format_image(image_bytes: LargeBinary, content_type: str):
    if not image_bytes:
        image_type = "url"
        image_data = random.choice(IMAGE_URL)
    else:
        image_type = "base_64"
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")    
        image_data = f"data:{content_type};base64,{image_base64}"

    return {
        "type": image_type,
        "data": image_data
    }

class CategorySelectionRequest(BaseModel):
    category: str

class GetWalletBalance(BaseModel):
    wallet_address: str

class WalletAuthRequest(BaseModel):
    wallet_address: str
    signature: str
    message: str


@app.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        user_id = request.user_id
        user = db.query(User).filter(User.id == user_id).first()
        if not user: 
            raise HTTPException(status_code=400, detail= f"User with id '{request.user_id}' not present")
        
        user_input_text = request.user_input

        if request.agent_id:
            agent_id = request.agent_id
        else:
            agent_id = random.randint(10000, 99999)
        
        user_tasks = UserChatPipeline()

        response = user_tasks.handle_chat(user_id, user_input_text, agent_id)
        
        data = {
            "raw": response.answer,
            "config": response.config.dict() if hasattr(response.config, "dict") else response.config
        }

        user_tasks._save_chat_history(user_id, agent_id, user_input_text, data)
        
        data["agent_id"] = agent_id

        return {"response": data}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/agent_marketplace", response_model=None)
async def agent_marketplace(db: Session = Depends(get_db)):
    agents = db.query(Agent).filter(Agent.is_deployed == True, Agent.is_active == True).order_by(Agent.created_date.desc()).all()  # Fetch all agents

    total_agents = len(agents)
    deployed_agents = sum(1 for agent in agents if agent.is_deployed)
    valid_performance_values = [
        float(agent.performance.strip('%')) for agent in agents
        if agent.performance and agent.performance.strip('%').replace(".", "", 1).isdigit()
    ]

    avg_performance = (
        sum(valid_performance_values) / len(valid_performance_values)
        if valid_performance_values else 0
    )

    results = (
        db.query(UserCommission.agent_id, func.sum(UserCommission.amount_eth).label("total_eth"))
        .filter(UserCommission.is_commissioned == True, UserCommission.is_active == True)
        .group_by(UserCommission.agent_id)
        .all()
    )
    
    total_aum = 0
    agents_aum = {}
    for agent_id, total_eth in results:
        agents_aum[agent_id] = total_eth
        total_aum += total_eth
    
    response = {
        "stats": {
            "totalAgents": total_agents,
            "deployedAgents": deployed_agents,
            "totalAUM": format_amount_eth(str(total_aum)),  # Convert to million format
            "avgPerformance": f"+{avg_performance:.1f}%" if total_agents else "N/A",
        },
        "agents": [
            {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "image": format_image(agent.image, agent.image_content),
                "performance": agent.performance or random.choice(PERFORMANCE),
                "aum": format_amount_eth(str(agents_aum[agent.id])) if agent.id in agents_aum else 0,
                "il": f"{agent.il}%" if agent.il is not None else "N/A",
                "weeklyReward": f"{agent.weekly_reward}%" if agent.weekly_reward else "N/A",
                "tags": agent.tags if agent.tags else [],
                "is_deployed": agent.is_deployed,
                "is_active": agent.is_active,
                "is_trending": agent.is_trending,
                "created_date": agent.created_date.strftime("%Y-%m-%d") if agent.created_date else "N/A",
                "subscription_fee": agent.subscription_fee,
                "clone_fee": format_amount_eth(str(agent.clone_fee)),
                "cloned_by": agent.cloned_by,
            }
            for agent in agents
        ],
    }

    return {"status": "success", "response": response}

@app.post("/my_agents", response_model=None)
async def my_agents(request: MyAgent, db: Session = Depends(get_db)):
    agents = db.query(Agent).filter(Agent.user_id == request.user_id, Agent.is_active == True).order_by(Agent.created_date.desc()).all()

    if not agents:
        return []
    
    agent_ids = {agent.id for agent in agents}

    user_commissions = (
        db.query(UserCommission)
        .filter(UserCommission.user_id == request.user_id, UserCommission.agent_id.in_(agent_ids))
        .all()
    )

    user_agent_commissions = {}
    for user_commission in user_commissions:
        user_agent_commissions[user_commission.agent_id] = user_commission.is_commissioned 

    results = (
        db.query(UserCommission.agent_id, func.sum(UserCommission.amount_eth).label("total_eth"))
        .filter(UserCommission.agent_id.in_(agent_ids), UserCommission.is_commissioned == True, UserCommission.is_active == True)
        .group_by(UserCommission.agent_id)
        .all()
    )

    agents_aum = {}
    total_aum = 0

    for result in results:
        agents_aum[result.agent_id] = result.total_eth
        total_aum += result.total_eth

    total_agents = len(agents)
    deployed_agents = sum(1 for agent in agents if agent.is_deployed)
    valid_performance_values = [
        float(agent.performance.strip('%')) for agent in agents
        if agent.performance and agent.performance.strip('%').replace(".", "", 1).isdigit()
    ]

    avg_performance = (
        sum(valid_performance_values) / len(valid_performance_values)
        if valid_performance_values else 0
    )
    
    response = {
        "stats": {
            "totalAgents": total_agents,
            "deployedAgents": deployed_agents,
            "totalAUM": format_amount_eth(str(total_aum)),  # Convert to million format
            "avgPerformance": f"+{avg_performance:.1f}%" if total_agents else "N/A",
        },
        "agents": [
            {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "image": format_image(agent.image, agent.image_content),
                "performance": agent.performance or random.choice(PERFORMANCE),
                "aum": format_amount_eth(str(agents_aum[agent.id])) if agent.id in agents_aum else 0,
                "il": f"{agent.il}%" if agent.il is not None else "N/A",
                "weeklyReward": f"{agent.weekly_reward}%" if agent.weekly_reward else "N/A",
                "tags": agent.tags if agent.tags else [],
                "config": agent.config,
                "is_deployed": agent.is_deployed,
                "is_active": agent.is_active,
                "is_trending": agent.is_trending,
                "created_date": agent.created_date.strftime("%Y-%m-%d") if agent.created_date else "N/A",
                "subscription_fee": agent.subscription_fee,
                "clone_fee": format_amount_eth(str(agent.clone_fee)),
                "cloned_by": agent.cloned_by,
                "is_commissioned": user_agent_commissions.get(agent.id, False),
            }
            for agent in agents
        ],
    }

    return {"status": "success", "response": response}


@app.post("/agent_tools")
async def agent_tools_and_capabilities(request: CategorySelectionRequest):
    category = request.category
    if not category:
        raise HTTPException(status_code=400, detail="Missing 'category' in request body")

    response = {
        "capabilities": [
            "Liquidity Provision",
            "Asset Rebalancing",
            "Volatility Prediction",
        ],
        "tools": [
            "Bollinger Bands",
            "RSI",
            "MACD",
            "Average True Range",
            "Volume Weighted Average Price",
            "Volatility"
        ]
    }
    return {"status": "success", "response": response}

@app.post("/build_agent")
async def build_agent(
    id: int = Form(...),
    name: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    user_id: int = Form(...),
    config: str = Form(...),
    image: UploadFile = File(None),
    clone_fee: str = Form(...),
    subscription_fee: float = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user: 
        raise HTTPException(status_code=400, detail= f"User with id '{user_id}' not present")
    
    image_data = None
    content_type = None

    if image:
        raw_image = await image.read()
        content_type = image.content_type  

        try:
            image_data = resize_image(raw_image, content_type)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    try:
        config_data = json.loads(config)
    except Exception:
        return {"error": "Invalid config JSON"}
    
    ph_agent_id = id
    
    tags = config_data.get("tags", [])

    agent = db.query(Agent).filter(Agent.name == name).first()

    if agent:
        raise HTTPException(status_code=400, detail=f"Agent with {agent.name} already exists")

    new_agent = Agent(
        name = name,
        category = category,
        description = description,
        user_id = user_id,
        config = config_data,
        image = image_data,
        image_content = content_type,
        tags = tags,
        clone_fee = Decimal(clone_fee),
        subscription_fee = subscription_fee,
        is_trending = False,
        is_deployed = False,
        is_active = True
    )

    if not config:
        new_agent.config = DEFAULT_CONFIG

    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)

    db.query(UserChat).filter(UserChat.user_id == user.id, UserChat.agent_id == ph_agent_id).update(
        {UserChat.agent_id: new_agent.id}, synchronize_session=False
    )

    db.commit()

    return {
        "status": "success",
        "response": f"Agent '{new_agent.name}' built successfully",
        "agent_id": new_agent.id
    }

@app.post("/deploy_agent")
async def update_agent(request: BuildAgentRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == request.user_id).first()

    if not user: 
        raise HTTPException(status_code=400, detail= f"User with id '{request.user_id}' not present")
    

    agent = db.query(Agent).filter(Agent.id == request.id, Agent.user_id == user.id).first()
    
    if not agent:
        return {
            "status": "error",
            "response": f"Agent with ID {request.id} not found"
        }
    
    agent.name = request.name
    agent.category = request.category
    agent.config=request.config
    agent.description = request.description
    agent.clone_fee = Decimal(request.clone_fee)
    agent.subscription_fee = request.subscription_fee
    agent.is_deployed = request.is_deployed
    agent.is_active = True

    if not request.config:
        agent.config = DEFAULT_CONFIG
    
    if request.config:
        tags = request.config.get("tags", [])
        agent.tags = tags

    if request.is_deployed == False:
        db.query(UserCommission).filter(UserCommission.is_commissioned == True).update({
            UserCommission.is_commissioned: False,
            UserCommission.is_active: False
        },
            synchronize_session=False
    )


    db.add(agent)
    db.commit()
    db.refresh(agent)

    return {
        "status": "success",
        "response": f"Agent '{agent.name}' updated successfully",
        "agent_id": agent.id
    }

def verify_signature(wallet_address: str, message: str, signature: str) -> bool:
    message_encoded = encode_defunct(text=message)
    recovered_address = Account.recover_message(message_encoded, signature=signature)
    return recovered_address.lower() == wallet_address.lower()


@app.post("/wallet_auth")
async def wallet_auth(req: WalletAuthRequest, db: Session = Depends(get_db)):
    auth_wallet_address = req.wallet_address

    if not verify_signature(auth_wallet_address, req.message, req.signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    
    user = db.query(User).filter(User.auth_wallet_address == auth_wallet_address).first()

    if not user:
        account = w3.eth.account.create()
        private_key = account.key.hex()
        wallet_address = account.address
        public_key = w3.eth.account.from_key(private_key)._key_obj.public_key.to_hex() 
        user = User(auth_wallet_address = auth_wallet_address, wallet_address = wallet_address, public_key = public_key, private_key = private_key)
        db.add(user)
        db.commit()
        db.refresh(user)

    return {
        "user_id": user.id,
        "wallet_address": user.wallet_address,
        "public_key": user.public_key
    }

@app.get("/agent_history/{user_id}")
async def get_agent_history_for_user(
    user_id: int,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    For a given user_id, fetch all agent_ids from UserCommission,
    then return each agent's details along with up to 10 most recent history entries
    and a total count of how many times the agent was rebalanced.
    """
    # 1) Find all commissions for this user

    user = db.query(User).filter(User.id == user_id).first()

    if not user: 
        raise HTTPException(status_code=400, detail= f"User with id '{user_id}' not present")

    commissions = (
        db.query(UserCommission)
          .filter(UserCommission.user_id == user_id, UserCommission.is_commissioned == True)
          .all()
    )
    if not commissions:
        return []
    
    agents = db.query(Agent).filter(Agent.is_active == True, Agent.user_id == user_id).all()
    

    response: List[Dict[str, Any]] = []
    for agent in agents:
        # 4) Fetch up to 10 most recent history entries
        histories = (
            db.query(AgentHistory)
              .filter(AgentHistory.agent_id == agent.id)
              .order_by(AgentHistory.created_at.desc())
              .all()
        )

        reason_to_type = {
            'Position out of range; executed rebalance': 'rebalanced',
            'No action; position in range': 'in_range',
            'Skipped; within rebalance timeframe': 'skipped',
            'Initial liquidity deployment': 'initial',
            'Applied below-trigger': 'Below Trigger Rebalance',
            'Applied above-trigger': 'Above Trigger Rebalance',
            'Applied positive bias to current price': 'Positive Bias',
            'Applied negative bias to current price': 'Negative Bias'
        }

        hist_list = [{
                "event": h.reason,
                "type": reason_to_type.get(h.reason, "unknown"),
                "rebalance_bias": h.rebalance_bias,
                "positive_bias": h.positive_bias,
                "timestamp": h.created_at.isoformat()
            }
            for h in histories
        ]

        # 5) Count total rebalances (where last_rebalanced_at is not null)
        rebalance_count = (
            db.query(AgentHistory)
              .filter(
                  
                  AgentHistory.agent_id == agent.id,
                  AgentHistory.last_rebalanced_at.isnot(None)
              )
              .count()
        )

        response.append({
            "id": agent.id,
            "agentName": agent.name,
            "description": agent.description,
            "image": format_image(agent.image, agent.image_content),
            "performance": agent.performance or random.choice(PERFORMANCE),
            "aum": f"${float(agent.aum) / 1_000:.1f}K" if agent.aum and agent.aum.replace(".", "", 1).isdigit() else 0,
            "il": f"{agent.il}%" if agent.il is not None else "N/A",
            "weeklyReward": f"{agent.weekly_reward}%" if agent.weekly_reward else "N/A",
            "tags": agent.tags if agent.tags else [],
            "created_date": agent.created_date.strftime("%Y-%m-%d") if agent.created_date else "N/A",
            "subscription_fee": agent.subscription_fee,
            "clone_fee": format_amount_eth(str(agent.clone_fee)),
            "cloned_by": agent.cloned_by,
            "duration": "N/A",  # Placeholder
            "is_deployed":  agent.is_deployed,
            "is_active": agent.is_active,
            "is_trending": agent.is_trending,
            "performance": getattr(agent, 'performance', None),
            "rebalanceCount": rebalance_count,
            "agentHistory": hist_list,
        })

    return response

@app.get("/get_private_key")
async def private_key(id: int = Query(..., description="ID of the agent to update"), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == id).first()

    if not user:
        return {
            "status": "error",
            "response": f"User with ID {id} not found"
        }
    
    return {"status": "success", "private_key": user.private_key}

@app.post("/commission")
async def save_user_commission(request: CreateUserCommission, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == request.agent_id, Agent.is_active==True, Agent.is_deployed == True).first()

    if not agent:
        raise HTTPException(status_code=400, detail= f"Agent with '{request.agent_id}' not present")
    
    user = db.query(User).filter(User.id == request.user_id).first()
    
    if not user:
        raise HTTPException(status_code=400, detail= f"User with id '{request.user_id}' not present")
    
    user_commission = db.query(UserCommission).filter(UserCommission.agent_id == agent.id, UserCommission.user_id==user.id).first()
    amount_eth = Decimal(request.amount_eth)

    if user_commission and user_commission.is_commissioned:
        raise HTTPException(status_code=400, detail= f"User has already commissioned '{request.agent_id}'")
    elif user_commission:
        user_commission.is_commissioned = request.is_commissioned
        user_commission.is_active = request.is_commissioned
        user_commission.amount_eth = amount_eth
    else:
        user_commission = UserCommission(
            user_id=request.user_id,
            agent_id = request.agent_id,
            amount_eth = amount_eth,
            is_commissioned = request.is_commissioned,
            is_active = request.is_commissioned
        )

    db.add(user_commission)
    db.commit()
    db.refresh(user_commission)

    return {
        "status": "success",
        "response": "Agent commission successful",
        "config_id": user_commission.id,
        "agent_id": agent.id
    }

@app.post("/get_agent")
async def get_agent(request: GetAgent, db: Session = Depends(get_db)):
    user_id = request.user_id
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=400, detail= f"User with id '{request.user_id}' not present")
    
    agent = db.query(Agent).filter(Agent.id == request.agent_id, Agent.is_active == True).first()

    if not agent:
        raise HTTPException(status_code=400, detail= f"Agent with '{request.agent_id}' not present")
    
    histories = (
            db.query(AgentHistory)
              .filter(AgentHistory.agent_id == agent.id)
              .order_by(AgentHistory.created_at.desc())
              .all()
        )
    
    reason_to_type = {
        'Position out of range; executed rebalance': 'rebalanced',
        'No action; position in range': 'in_range',
        'Skipped; within rebalance timeframe': 'skipped',
        'Initial liquidity deployment': 'initial',
        'Applied below-trigger': 'Below Trigger Rebalance',
        'Applied above-trigger': 'Above Trigger Rebalance',
        'Applied positive bias to current price': 'Positive Bias',
        'Applied negative bias to current price': 'Negative Bias'
    }

    hist_list = [{
            "event": h.reason,
            "type": reason_to_type.get(h.reason, "unknown"),
            "rebalance_bias": h.rebalance_bias,
            "positive_bias": h.positive_bias,
            "timestamp": h.created_at.isoformat()
        }
        for h in histories
    ]

    rebalance_count = (
            db.query(AgentHistory)
              .filter(
                  AgentHistory.agent_id == agent.id,
                  AgentHistory.last_rebalanced_at.isnot(None)
              )
              .count()
        )
    
    clone_agent = db.query(Agent).filter(Agent.cloned_by == agent.id, Agent.user_id == user.id, Agent.is_active == True).first() if user_id else None

    result = (
        db.query(
            UserCommission.agent_id,
            func.sum(UserCommission.amount_eth).label("total_eth")
        )
        .filter(UserCommission.agent_id == agent.id, UserCommission.is_commissioned == True, UserCommission.is_active == True)
        .group_by(UserCommission.agent_id)
        .first()
    )
    
    user_commission = None

    if user_id:
        user_commission = db.query(UserCommission).filter(UserCommission.user_id == user_id, UserCommission.agent_id == agent.id).first()

    paused_at = None

    if user_commission and user_commission.paused_at:
        paused_at = user_commission.paused_at.strftime("%Y-%m-%d")

    
    if not start_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
    elif not end_date:
        end_date = datetime.utcnow()

    agent_daily_stats = db.query(AgentDailyStat).filter(
        AgentDailyStat.agent_id == agent.id,
        AgentDailyStat.created_at >= start_date.date(),
        AgentDailyStat.created_at <= end_date.date()
    ).order_by(AgentDailyStat.created_at.asc()).all()

    stats = []

    for stat in agent_daily_stats:
        params = {
            "date": stat.created_a.isoformat(),
            "invested_eth": float(stat.total_invested_eth),
            "reward_earned": float(stat.total_reward_earned),
            "impermanent_loss": float(stat.total_impermanent_loss),
            "total_assets": float(stat.total_assets),
            "reward_percent": float(stat.total_reward_percent)
        }
        stats.append(params)

    data = {
        "id": agent.id,
        "agentName": agent.name,
        "description": agent.description,
        "image": format_image(agent.image, agent.image_content),
        "performance": agent.performance or random.choice(PERFORMANCE),
        "aum": format_amount_eth(str(result.total_eth)) if result else 0,
        "il": f"{agent.il}%" if agent.il is not None else "N/A",
        "weeklyReward": f"{agent.weekly_reward}%" if agent.weekly_reward else "N/A",
        "tags": agent.tags if agent.tags else [],
        "config": agent.config,
        "created_date": agent.created_date.strftime("%Y-%m-%d") if agent.created_date else "N/A",
        "duration": "N/A",  # Placeholder
        "subscription_fee": agent.subscription_fee,
        "clone_fee": format_amount_eth(str(agent.clone_fee)),
        "cloned_by": agent.cloned_by,
        "is_deployed": agent.is_deployed,
        "is_active": user_commission.is_active if user_commission else False,
        "paused_at": paused_at,
        "is_trending": agent.is_trending,
        **({"cloned_by_user": True if clone_agent else False} if user_id else {}),
        "is_commissioned": user_commission.is_commissioned if user_commission else False,
        "user_id": agent.user_id,
        "rebalanceCount": rebalance_count,
        "agentHistory": hist_list,
        "agent_stats": stats
    }
    
    return {
        "status": "success",
        "response": data
    }

@app.post("/update_agent")
async def deploy_agent(request: DeployAgent, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == request.user_id).first()

    if not user:
        raise HTTPException(status_code=400, detail= f"User with id '{request.user_id}' not present")
    
    agent = db.query(Agent).filter(Agent.id == request.agent_id, Agent.is_active == True).first()
    
    if not agent:
        raise HTTPException(status_code=400, detail= f"Agent with id '{request.agent_id}' not present")
    
    if agent.user_id != user.id:
       raise HTTPException(status_code=400, detail= f"User is not authorized to update Agent with id '{request.agent_id}'")
    
    agent.is_deployed = request.is_deployed

    if request.is_deployed == False:
        db.query(UserCommission).filter(UserCommission.is_commissioned == True).update({
            UserCommission.is_commissioned: False,
            UserCommission.is_active: False
        },
            synchronize_session=False
    )

    db.add(agent)

    db.commit()

    return {
        "status_code": 200,
        "message": "Agent deployed succesfully",
        "agent_id": agent.id
    }

@app.post("/wallet_balance")
async def get_wallet_balance(request: GetWalletBalance, db: Session = Depends(get_db)):
    wallet_address = request.wallet_address

    if not w3.is_address(wallet_address):
        raise HTTPException(status_code=400, detail="Invalid wallet address")
    
    try:
        balance_wei = w3.eth.get_balance(wallet_address)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        balance_eth = Decimal(balance_eth)
        return {
            "wallet_address": wallet_address,
            "wallet_balance": format(balance_eth.normalize(), 'f')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching balance: {str(e)}")
    
@app.get("/user_chat_history")
def get_user_chat_history(user_id: int, agent_id: int, db: Session = Depends(get_db)):
    # Query the UserChat model and filter by user_id and agent_id
    chats = (
        db.query(UserChat)
        .filter(UserChat.user_id == user_id, UserChat.agent_id == agent_id)
        .order_by(UserChat.created_at.desc())  # Sorting by created_at in descending order
        .all()
    )

    # If no chats found, return an HTTP 404
    if not chats:
        raise HTTPException(status_code=404, detail="No chat history found for the given user and agent.")

    # Return a list of chat histories (you can customize the response format as needed)
    chat_history = [
        {
            "user_query": chat.user_query,
            "response": chat.response,
            "created_at": chat.created_at
        }
        for chat in chats
    ]

    return chat_history

@app.post("/update_commission")
async def update_commission(request: UpdateCommission, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == request.user_id).first()

    if not user:
        raise HTTPException(status_code=400, detail= f"User with id '{request.user_id}' not present")
    
    agent = db.query(Agent).filter(Agent.id == request.agent_id, Agent.is_deployed == True, Agent.is_active == True).first()
    
    if not agent:
        raise HTTPException(status_code=400, detail= f"Agent with id '{request.agent_id}' not present")
    
    user_commission = db.query(UserCommission).filter(UserCommission.agent_id == agent.id, UserCommission.user_id==user.id, UserCommission.is_commissioned == True).first()

    if not user_commission:
        raise HTTPException(status_code=400, detail= f"User has not commissioned this agent named: {agent.name}")

    if user_commission.is_active and not request.is_active:
        user_commission.paused_at = datetime.now()

    user_commission.is_active = request.is_active
    user_commission.is_commissioned = request.is_commissioned


    db.add(user_commission)
    db.commit()

    return {
        "status": "success",
        "message": f"Agent Commission updated"
    }


@app.get("/user_commission/{user_id}")
async def get_agent_history_for_user( user_id: int, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    For a given user_id, fetch all agent_ids from UserCommission,
    then return each agent's details along with up to 10 most recent history entries
    and a total count of how many times the agent was rebalanced.
    """
    # 1) Find all commissions for this user
    commissions = (
        db.query(UserCommission)
          .filter(UserCommission.user_id == user_id, UserCommission.is_commissioned == True)
          .all()
    )
    if not commissions:
        return []
    
    # 2) Unique agent IDs
    agent_ids = {c.agent_id for c in commissions}

    commission_state = {}
    commission_amounts = {}
    commission_paused_at = {}
    for c in commissions:
        commission_state[c.agent_id] = c.is_active
        commission_amounts[c.agent_id] = c.amount_eth
        commission_paused_at[c.agent_id] = c.paused_at if c.paused_at else None

    # 3) Load agent metadata
    agents = (
        db.query(Agent)
          .filter(Agent.id.in_(agent_ids))
          .all()
    )

    response: List[Dict[str, Any]] = []
    for agent in agents:
        # 4) Fetch up to 10 most recent history entries
        histories = (
            db.query(AgentHistory)
              .filter(AgentHistory.agent_id == agent.id)
              .order_by(AgentHistory.created_at.desc())
              .limit(10)
              .all()
        )

        reason_to_type = {
            'Position out of range; executed rebalance': 'rebalanced',
            'No action; position in range': 'in_range',
            'Skipped; within rebalance timeframe': 'skipped',
            'Initial liquidity deployment': 'initial',
            'Applied below-trigger': 'Below Trigger Rebalance',
            'Applied above-trigger': 'Above Trigger Rebalance',
            'Applied positive bias to current price': 'Positive Bias',
            'Applied negative bias to current price': 'Negative Bias'
        }

        hist_list = [{
                "event": h.reason,
                "type": reason_to_type.get(h.reason, "unknown"),
                "rebalance_bias": h.rebalance_bias,
                "positive_bias": h.positive_bias,
                "timestamp": h.created_at.isoformat()
            }
            for h in histories
        ]

        # 5) Count total rebalances (where last_rebalanced_at is not null)
        rebalance_count = (
            db.query(AgentHistory)
              .filter(
                  AgentHistory.agent_id == agent.id,
                  AgentHistory.last_rebalanced_at.isnot(None)
              )
              .count()
        )

        response.append({
            "id": agent.id,
            "agentName": agent.name,
            "description": agent.description,
            "image": format_image(agent.image, agent.image_content),
            "performance": agent.performance or random.choice(PERFORMANCE),
            "aum": f"${float(agent.aum) / 1_000:.1f}K" if agent.aum and agent.aum.replace(".", "", 1).isdigit() else 0,
            "il": f"{agent.il}%" if agent.il is not None else "N/A",
            "weeklyReward": f"{agent.weekly_reward}%" if agent.weekly_reward else "N/A",
            "tags": agent.tags if agent.tags else [],
            "created_date": agent.created_date.strftime("%Y-%m-%d") if agent.created_date else "N/A",
            "subscription_fee": agent.subscription_fee,
            "clone_fee": format_amount_eth(str(agent.clone_fee)),
            "cloned_by": agent.cloned_by,
            "duration": "N/A",  # Placeholder
            "is_commissioned": True,
            "is_active": commission_state[agent.id],
            "paused_at": commission_paused_at(agent.id).strftime("%Y-%m-%d"),
            "is_trending": agent.is_trending,
            "amount_eth": format_amount_eth(str(commission_amounts[agent.id])),
            "rebalanceCount": rebalance_count,
            "agentHistory": hist_list,
        })

    response = sorted(response, key=lambda x: not x["is_active"])

    return response

def format_amount_eth(amount: str):
    amount_float = float(Decimal(amount))
    formatted_amount = format(amount_float, '.10f').rstrip('0').rstrip('.')

    return formatted_amount
    

@app.post("/update_amount_eth")
async def add_token(request: UpdateAmountEth, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == request.user_id).first()

    if not user:
        raise HTTPException(status_code=400, detail= f"User with id '{request.user_id}' not present")
    
    agent = db.query(Agent).filter(Agent.id == request.agent_id, Agent.is_active == True).first()
    
    if not agent:
        raise HTTPException(status_code=400, detail= f"Agent with id '{request.agent_id}' not present")
    
    user_commission = db.query(UserCommission).filter(UserCommission.agent_id == agent.id, UserCommission.user_id==user.id, UserCommission.is_commissioned == True).first()
    
    if not user_commission:
        raise HTTPException(status_code=400, detail= f"User has not commissioned this agent named: {agent.name}")
    
    amount = Decimal(request.amount_eth)

    if request.add:
        amount = user_commission.amount_eth + amount
    else:
        amount = user_commission.amount_eth - amount 

    user_commission.amount_eth = amount

    db.add(user_commission)
    db.commit()

    return {
        "status": "success",
        "message": f"Amount added successfully for Agent: {agent.name}"
    }


@app.post("/delete_agent")
async def delete_agent(request: DeleteAgent, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == request.agent_id, Agent.is_active == True).first()

    if not agent:
        raise HTTPException(status_code=400, detail= f"Agent with id '{request.agent_id}' not present")
    
    if agent.is_deployed:
        raise HTTPException(status_code=400, detail= f"Agent with id '{request.agent_id}' is deployed on the marketplace")
    
    if agent.user_id != request.user_id:
        raise HTTPException(status_code=400, detail= f"User can not delete this Agent with id {request.agent_id}")
    
    agent.is_active = False
    db.add(agent)

    db.query(UserCommission).filter(
        UserCommission.agent_id == agent.id,
        UserCommission.is_commissioned == True
    ).update({
            UserCommission.is_commissioned: False,
            UserCommission.is_active: False
        },
            synchronize_session=False
    )
    db.commit()
    
    return {
        "status": "success",
        "message": f"Agent deleted succesfully"
    }

@app.post("/clone_agent")
async def clone_agent(req: CloneAgent, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == req.agent_id, Agent.is_active == True).first()

    if not agent:
        raise HTTPException(status_code=400, detail=f"Agent with id '{req.agent_id}' not present")
    
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user: 
        raise HTTPException(status_code=400, detail=f"User with id '{req.user_id}' not present")
    
    sender_wallet_address = user.wallet_address
    sender_private_key = user.private_key
    receiver = db.query(User).filter(User.id == agent.user_id).first()

    if not receiver or not receiver.wallet_address:
        raise HTTPException(status_code=400, detail="Receiver wallet address not found")

    receiver_wallet_address = receiver.wallet_address

    amount_in_eth = agent.clone_fee or Decimal('0') 
    amount_in_wei = w3.to_wei(float(amount_in_eth), 'ether')

    try:
        tx = {
            'nonce': w3.eth.get_transaction_count(sender_wallet_address),
            'to': receiver_wallet_address,
            'value': amount_in_wei,
            'gas': 21000,
            'gasPrice': w3.eth.gas_price,
            'chainId': 11155111  # Chain ID for Sepolia
        }

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=sender_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt.status != 1:
            raise HTTPException(status_code=500, detail="Transaction failed on chain")
        
        clone_fee_log = UserDailyCloneFee(
            agent_id=agent.id,
            user_id=receiver.id,              
            sent_by_user_id=user.id,         
            fee_amount=amount_in_eth
        )
        db.add(clone_fee_log)
        
    except Exception as e:
        try:
            error_dict = ast.literal_eval(str(e))  # safely convert string -> dict
            error_message = error_dict.get('message', 'Something went wrong')
        except Exception:
            error_message = str(e)
        raise HTTPException(status_code=500, detail= error_message)

    new_agent = Agent(
        name= req.name,
        description=agent.description,
        category=agent.category,
        image=agent.image,
        image_content=agent.image_content,
        user_id=req.user_id,
        cloned_by=agent.id,
        is_deployed=False,
        is_active=True,
        is_trending=False,
        performance=agent.performance or random.choice(PERFORMANCE),
        config=agent.config,
        tags=agent.tags,
        subscription_fee = agent.subscription_fee,
        clone_fee = agent.clone_fee
    )

    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    
    data = {
        "id": new_agent.id,
        "agentName": new_agent.name,
        "description": new_agent.description,
        "image": format_image(new_agent.image, new_agent.image_content),
        "performance": new_agent.performance or random.choice(PERFORMANCE),
        "aum": f"${float(new_agent.aum) / 1_000:.1f}K" if new_agent.aum and new_agent.aum.replace(".", "", 1).isdigit() else 0,
        "il": f"{new_agent.il}%" if new_agent.il is not None else "N/A",
        "weeklyReward": f"{new_agent.weekly_reward}%" if new_agent.weekly_reward else "N/A",
        "tags": new_agent.tags if new_agent.tags else [],
        "created_date": new_agent.created_date.strftime("%Y-%m-%d") if new_agent.created_date else "N/A",
        "duration": "N/A",  # Placeholder
        "subscription_fee": new_agent.subscription_fee,
        "clone_fee": format_amount_eth(str(new_agent.clone_fee)),
        "cloned_by": new_agent.cloned_by,
        "is_deployed": new_agent.is_deployed,
        "is_active": new_agent.is_active,
        "is_trending": new_agent.is_trending,
        "user_id": new_agent.user_id,
        "config": new_agent.config
    }

    return {
        "status": "success",
        "response": data
    }

@app.get("/search_agent_name/{agent_name}")
async def search_agent_name(agent_name: str, db: Session = Depends(get_db)):
    is_existing = False

    agent = db.query(Agent).filter(Agent.name.ilike(agent_name)).first()
    is_existing = True if agent else False

    return {
        "status": "Success",
        "agent_name": agent_name,
        "is_existing": is_existing
    }

@app.post("/user_stats")
async def get_user_stats( req: DailyFeeAnalyticsRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()

    if not user:
        raise HTTPException(status_code=400, detail= f"User with id '{req.user_id}' not present")
    
    if not start_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
    elif not end_date:
        end_date = datetime.utcnow()

    stats = db.query(UserDailyStat).filter(
        UserDailyStat.user_id == req.user_id,
        UserDailyStat.created_at >= start_date.date(),
        UserDailyStat.created_at <= end_date.date()
    ).order_by(UserDailyStat.created_at.asc()).all()

    if not stats:
        raise HTTPException(status_code=404, detail="No stats found for this user in the given date range")

    return {
        "user_id": req.user_id,
        "start_date": start_date.date().isoformat(),
        "end_date": end_date.date().isoformat(),
        "stats": [
            {
                "date": stat.created_at.isoformat(),
                "total_assets": float(stat.total_assets),
                "total_invested_eth": float(stat.total_invested_eth),
                "total_reward_earned":float(stat.total_reward_earned),
                "total_reward_percent": float(stat.total_reward_percent),
                "total_impermanent_loss": float(stat.total_impermanent_loss),
                "active_positions": float(stat.active_positions),
                "total_positions": float(stat.total_positions) 
            }
            for stat in stats
        ]
    }

@app.post("/user_earned_fees",response_model=List[DailyFeeAnalyticsResponse])
def get_daily_fee_analytics( req: DailyFeeAnalyticsRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.id == req.user_id).first()

    if not user:
        raise HTTPException(status_code=400, detail= f"User with id '{req.user_id}' not present")
    
    today = date.today()
    start_date = req.start_date or (today - timedelta(days=6))
    end_date = req.end_date or today

    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

    # Clone fee aggregation for this user
    clone_fees = db.query(
        cast(UserDailyCloneFee.created_at, Date).label("day"),
        func.coalesce(func.sum(UserDailyCloneFee.fee_amount), 0).label("total_clone_fee")
    ).filter(
        UserDailyCloneFee.user_id == req.user_id,
        cast(UserDailyCloneFee.created_at, Date) >= start_date,
        cast(UserDailyCloneFee.created_at, Date) <= end_date
    ).group_by("day").all()

    # Usage fee aggregation for this user
    usage_fees = db.query(
        cast(UserDailyEarnedFee.created_at, Date).label("day"),
        func.coalesce(func.sum(UserDailyEarnedFee.fee_earned), 0).label("total_usage_fee")
    ).filter(
        UserDailyEarnedFee.user_id == req.user_id,
        cast(UserDailyEarnedFee.created_at, Date) >= start_date,
        cast(UserDailyEarnedFee.created_at, Date) <= end_date
    ).group_by("day").all()

    # Merge results
    fee_map = {}

    for row in clone_fees:
        fee_map[row.day] = {
            "date": row.day,
            "clone_fee": float(row.total_clone_fee),
            "usage_fee": 0.0
        }

    for row in usage_fees:
        if row.day in fee_map:
            fee_map[row.day]["usage_fee"] = float(row.total_usage_fee)
        else:
            fee_map[row.day] = {
                "date": row.day,
                "clone_fee": 0.0,
                "usage_fee": float(row.total_usage_fee)
            }

    # Ensure 0 values for missing days
    all_dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    for d in all_dates:
        if d not in fee_map:
            fee_map[d] = {
                "date": d,
                "clone_fee": 0.0,
                "usage_fee": 0.0
            }

    return sorted(fee_map.values(), key=lambda x: x["date"])


# @app.get("/rebalance")
# async def rebalnce(db: Session = Depends(get_db)):
#     rebalancer = LiquidityRebalancingPipeline()
#     user_commission = db.query(UserCommission).filter(UserCommission.is_commissioned == True, UserCommission.is_active == True).first()

#     a = db.query(Agent).filter(Agent.id == user_commission.agent_id).first()
#     cfg = a.config

#     tickers = {
#             'ETH-USD' if a.config['pool_details']['token_pair'] in ['ETH/USDC','USDC/ETH'] else 'BTC-USD'
#         }
#     price_map = {}
#     for t in tickers:
#         p = (
#             db.query(CryptoPrice)
#                 .filter_by(ticker=t)
#                 .order_by(CryptoPrice.date.desc())
#                 .first()
#         )
#         price_map[t] = {}
#         for field in [
#             'open_price','high_price','low_price','close_price','volume','rsi',
#             'bb_upper','bb_middle','bb_lower','volatility','macd',
#             'macd_signal','macd_histogram','atr','price_range','vwap'
#         ]:
#             val = getattr(p, field)
#             # If it’s a Decimal, cast to float; otherwise leave it
#             try:
#                 price_map[t][field] = float(val)
#             except (TypeError, ValueError):
#                 price_map[t][field] = val
#     ticker = 'ETH-USD' if cfg['pool_details']['token_pair'] in ['ETH/USDC','USDC/ETH'] else 'BTC-USD'

#     decision = rebalancer.rebalance_now(a.config, price_map[ticker])

#     data = {
#         "answer": decision.answer,
#         "bias": decision.bias,
#         "positive": decision.positive
#     }

#     return {"response": data}

# from src.aizen.protocols.uniswapv3 import UniswapV3
# @app.get("/get_uni")
# async def get_uni():

#     pool_details = {'fee_tier':0.3, 'token_pair': 'ETH/USDC'}

#     range_config = {"lower": 0.05, "upper": 0.005, "buffer": 0.025}


#     uni = UniswapV3(PRIVATE_KEY, WALLET_ADDRESS, pool_details)

    # position_id = 196947

    # y = uni.npm_contract.functions.positions(position_id).call()
    # print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
    # print(y)
    # print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
    # x = uni.remove_liquidity(position_id)
    # print("&&&&&&&&&&&&&&&&&&&&&&&&&&&")
    # print(x)
    # z = uni.burn_position(position_id)
    # print("&&&&&&&&&&&&&&&&&&&&&&&&&&&")
    # print(z)
    
    # amount_eth = 0.00025
    # lo, hi = uni.calculate_new_ticks(uni.get_current_tick(), range_config)

    # receipt = uni.add_liquidity(lo ,hi, amount_eth)
    # pos_id = uni.get_latest_position_id()

    # print("&&&&&&&&&&&&&&&&&&&&&&")
    # print(receipt)
    # print(pos_id)
    # return {"status":"Success"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
