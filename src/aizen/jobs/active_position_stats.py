from sqlalchemy.orm import Session
from src.aizen.models import AgentStat, User
from datetime import datetime
from decimal import Decimal
from src.aizen.database import SessionLocal
from src.aizen.protocols.uniswapv3 import UniswapV3

db: Session = SessionLocal()

def active_position_stats():
    """Update impermanent loss, reward earned, and final_eth for all active positions."""
    active_positions = db.query(AgentStat).filter(AgentStat.is_active == True).all()
    now = datetime.utcnow()

    for stat in active_positions:
        try:
            user = db.query(User).filter(User.id == stat.user_id).first()
            uni = UniswapV3(user.private_key, user.wallet_address, stat.agent_id, stat.user_id, stat.pool_details)

            # Skip if position is not valid or lacks liquidity
            pos = uni.npm_contract.functions.positions(stat.position_id).call()
            liquidity = pos[7]
            if liquidity == 0:
                continue

            # Get uncollected fees (use `.call()` instead of actual transaction)
            fees = uni.npm_contract.functions.collect({
                'tokenId': stat.position_id,
                'recipient': uni.account_address,
                'amount0Max': 2**128 - 1,
                'amount1Max': 2**128 - 1
            }).call({'from': uni.account_address})

            amount0 = Decimal(fees[0]) / Decimal(1e6)   # USDC
            amount1 = Decimal(fees[1]) / Decimal(1e18)  # ETH

            price = uni.get_eth_price()
            fees_earned = (amount0 / Decimal(price)) + amount1

            # Estimate total position value in ETH (assuming only unclaimed fees are accessible)
            final_eth = fees_earned  # Approximation for active positions

            # Compute stats
            invested_eth = stat.invested_eth or Decimal(0)
            impermanent_loss = max(Decimal(0), invested_eth - final_eth)
            reward_earned = max(Decimal(0), final_eth - invested_eth)

            # Update AgentStat record
            stat.final_eth = final_eth.quantize(Decimal("0.00000001"))
            stat.reward_earned = reward_earned.quantize(Decimal("0.00000001"))
            stat.impermanent_loss = impermanent_loss.quantize(Decimal("0.00000001"))
            stat.updated_at = now

            db.add(stat)

        except Exception as e:
            print(f"[Error] Failed to update position {stat.position_id}: {e}")

    db.commit()
    print(f"[Info] Updated {len(active_positions)} active position(s).")

if __name__ == "__main__":
    active_position_stats()
