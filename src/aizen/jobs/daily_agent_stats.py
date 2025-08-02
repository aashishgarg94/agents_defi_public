from sqlalchemy.orm import Session
from src.aizen.models import AgentStat, AgentDailyStat, UserCommission
from sqlalchemy.sql import func
from sqlalchemy import Integer
from decimal import Decimal
from src.aizen.database import SessionLocal

db: Session = SessionLocal()

def calculate_daily_agent_stats():
    agent_ids = db.query(AgentStat.agent_id).distinct().all()
    agent_ids = [aid[0] for aid in agent_ids]

    for agent_id in agent_ids:
        try:
            total_assets = db.query(func.sum(UserCommission.amount_eth)).filter(
                UserCommission.agent_id == agent_id, UserCommission.is_active == True, UserCommission.is_commissioned ==True
            ).scalar() or Decimal(0)

            stats = db.query(
                func.sum(AgentStat.impermanent_loss).label("total_il"),
                func.sum(AgentStat.reward_earned).label("total_reward"),
                func.sum(AgentStat.invested_eth).label("total_invested"),
                func.max(AgentStat.is_active.cast(Integer)).label("is_active")
            ).filter(AgentStat.agent_id == agent_id).first()

            if stats is None:
                continue

            total_il = stats.total_il or Decimal(0)
            total_reward = stats.total_reward or Decimal(0)
            total_invested = stats.total_invested or Decimal(1)  # Avoid division by zero
            reward_percent = (total_reward / total_invested) * Decimal(100)

            daily_stat = AgentDailyStat(
                agent_id=agent_id,
                total_assets = total_assets,
                total_invested_eth=total_invested,
                total_reward_earned=total_reward,
                total_reward_percent=reward_percent,
                total_impermanent_loss=total_il
            )

            db.add(daily_stat)

        except Exception as e:
            print(f"[Error] Could not compute daily stats for agent {agent_id}: {e}")

    db.commit()
    print(f"[Info] Daily agent stats updated for {len(agent_ids)} agents.")

if __name__ == "__main__":
    calculate_daily_agent_stats()