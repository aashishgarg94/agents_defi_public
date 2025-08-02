from sqlalchemy.orm import Session
from src.aizen.models import AgentStat, UserCommission, UserDailyStat
from sqlalchemy.sql import func
from decimal import Decimal
from src.aizen.database import SessionLocal

db: Session = SessionLocal()

def calculate_daily_user_stats():
    user_ids = db.query(AgentStat.user_id).distinct().all()
    user_ids = [uid[0] for uid in user_ids]

    for user_id in user_ids:
        try:
            # Total ETH assets from user_commission
            total_assets = db.query(func.sum(UserCommission.amount_eth)).filter(
                UserCommission.user_id == user_id, UserCommission.is_active == True, UserCommission.is_commissioned ==True
            ).scalar() or Decimal(0)

            # Aggregates from agent_stats
            stats = db.query(
                func.sum(AgentStat.impermanent_loss).label("total_il"),
                func.sum(AgentStat.reward_earned).label("total_reward"),
                func.sum(AgentStat.invested_eth).label("total_invested"),
                func.count().label("total_positions"),
                func.sum(func.cast(AgentStat.is_active, Integer)).label("active_positions")
            ).filter(AgentStat.user_id == user_id).one()

            total_il = stats.total_il or Decimal(0)
            total_reward = stats.total_reward or Decimal(0)
            total_invested = stats.total_invested or Decimal(1)  # Avoid division by 0
            reward_percent = (total_reward / total_invested) * Decimal(100)

            user_daily_stat = UserDailyStat(
                user_id=user_id,
                total_assets=total_assets,
                total_invested_eth=total_invested,
                total_reward_earned=total_reward,
                total_reward_percent=reward_percent,
                total_impermanent_loss=total_il,
                active_positions=stats.active_positions or 0,
                total_positions=stats.total_positions or 0
            )

            db.add(user_daily_stat)

        except Exception as e:
            print(f"[Error] Could not compute daily stats for user {user_id}: {e}")

    db.commit()
    print(f"[Info] Daily stats updated for {len(user_ids)} users.")

if __name__ == "__main__":
    calculate_daily_user_stats()