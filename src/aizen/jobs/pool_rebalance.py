from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.aizen.database import SessionLocal
from src.aizen.pipelines.liquidity_rebalancing_pipeline import LiquidityRebalancingPipeline
from src.aizen.models import (Agent, UserCommission, CryptoPrice, UserAgentPool, AgentHistory, User)
from src.aizen.protocols.uniswapv3 import UniswapV3
from datetime import datetime, timedelta
import json, logging

logging.basicConfig(level=logging.INFO)

WALLET_ADDRESS = '0xb94447784Dc9E9c9c69BeD754a9C9Eea786065AA'

def liquidity_pool_rebalancing():
    db: Session = SessionLocal()
    rebalancer = LiquidityRebalancingPipeline()

    user = db.query(User).filter(User.wallet_address == WALLET_ADDRESS).first()
    PRIVATE_KEY = user.private_key
    try:
        # Fetch active commissions
        commissions = db.query(UserCommission).filter_by(is_commissioned=True, is_active=True).all()
        if not commissions:
            logging.info("No active rebalancing configurations found.")
            return

        # Bulk preload agents, pools
        agent_ids = {c.agent_id for c in commissions}
        user_ids = {c.user_id  for c in commissions}
        agents = {a.id: a for a in db.query(Agent).filter(Agent.id.in_(agent_ids)).all()}
        pools = db.query(UserAgentPool).filter(
            UserAgentPool.agent_id.in_(agent_ids),
            UserAgentPool.user_id.in_(user_ids)
        ).all()
        pool_map = {(p.agent_id, p.user_id): p for p in pools}

        # Preload latest prices (Decimal → float)
        tickers = {
            'ETH-USD' if a.config['pool_details']['token_pair'] in ['ETH/USDC','USDC/ETH'] else 'BTC-USD'
            for a in agents.values()
        }
        price_map = {}
        for t in tickers:
            p = db.query(CryptoPrice).filter_by(ticker=t).order_by(desc(CryptoPrice.date)).first()
            price_map[t] = {f: (float(getattr(p, f)) if getattr(p, f) is not None else None)
                            for f in ['open_price','high_price','low_price','close_price',
                                      'volume','rsi','bb_upper','bb_middle','bb_lower',
                                      'volatility','macd','macd_signal','macd_histogram',
                                      'atr','price_range','vwap']}

        now = datetime.utcnow()
        new_pools = []
        history_entries = []
        agent_cache = {}

        for comm in commissions:
            a = agents[comm.agent_id]
            pool = pool_map.get((a.id, comm.user_id))
            cfg = a.config
            triggers = cfg.get('rebalance_triggers', {})

            # Initialize per-agent cache
            if a.id not in agent_cache:
                uni = UniswapV3(PRIVATE_KEY, WALLET_ADDRESS, cfg['pool_details'], a.id)
                current_tick = uni.get_current_tick()
                base_cfg = {
                    'lower': cfg['liquidity_range']['lower'],
                    'upper': cfg['liquidity_range']['higher'],
                    'buffer': cfg['buffer']
                }
                init_lo, init_hi = uni.calculate_new_ticks(current_tick, base_cfg)
                ticker = 'ETH-USD' if cfg['pool_details']['token_pair'] in ['ETH/USDC','USDC/ETH'] else 'BTC-USD'
                decision = rebalancer.rebalance_now(cfg, price_map[ticker])

                agent_cache[a.id] = {
                    'uni': uni,
                    'init_range': (init_lo, init_hi),
                    'base_cfg': base_cfg,
                    'amounts': cfg['liquidity_amounts'],
                    'decision': decision
                }

            cache = agent_cache[a.id]
            # uni = cache['uni']
            init_lo, init_hi = cache['init_range']
            base_cfg = cache['base_cfg']
            amt = cache['amounts']
            decision = cache['decision']

            # Extract bias & logic from new format
            bias = decision.bias
            positive_bias = decision.positive
            logic = decision.answer

            # INITIAL DEPLOYMENT
            if pool is None:
                lo, hi = uni.calculate_new_ticks(uni.get_current_tick(), base_cfg)
                # receipt = uni.add_liquidity(lo, hi, comm.amount_eth, cfg['max_slippage'])
                # pos_id = uni.get_latest_position_id() if receipt.get('status') == 1 else None

                new_pools.append(UserAgentPool(
                    user_id=comm.user_id,
                    agent_id=a.id,
                    liquidity_amounts=amt,
                    liquidity_range={'min': lo, 'max': hi},
                    last_checked_at=now
                ))
                history_entries.append(AgentHistory(
                    agent_id=a.id,
                    last_checked_at=now,
                    last_rebalanced_at=now,
                    rebalance_decision=True,
                    positive_bias=positive_bias,
                    rebalance_logic=logic,
                    rebalance_bias=bias,
                    reason='Initial liquidity deployment'
                ))
                continue

            # THROTTLE CHECK
            interval = timedelta(minutes=cfg['rebalance_timeframe'])
            if pool.last_checked_at and now < pool.last_checked_at + interval:
                history_entries.append(AgentHistory(
                    agent_id=a.id,
                    last_checked_at=now,
                    rebalance_decision=False,
                    reason='Skipped; within rebalance timeframe'
                ))
                continue
            pool.last_checked_at = now

            # IN-RANGE CHECK
            lo_cur = pool.liquidity_range['min']
            hi_cur = pool.liquidity_range['max']
            current_tick = uni.get_current_tick()
            if lo_cur <= current_tick <= hi_cur:
                history_entries.append(AgentHistory(
                    agent_id=a.id,
                    last_checked_at=now,
                    rebalance_decision=False,
                    reason='No action; position in range'
                ))
                continue

            # OUT-OF-RANGE: triggers or bias shift on current price
            span = init_hi - init_lo
            deviation = ((init_lo - current_tick) / span * 100) if current_tick < init_lo else ((current_tick - init_hi) / span * 100)

            trigger_lo = trigger_hi = None
            reason = ''
            below_cfg = triggers.get('below')
            above_cfg = triggers.get('above')
            if below_cfg and all(k in below_cfg for k in ('by','lower','higher')):
                if current_tick < init_lo and deviation >= below_cfg['by']:
                    trigger_lo, trigger_hi = below_cfg['lower'], below_cfg['higher']
                    reason = f"Applied below-trigger"
            if trigger_lo is None and above_cfg and all(k in above_cfg for k in ('by','lower','higher')):
                if current_tick > init_hi and deviation >= above_cfg['by']:
                    trigger_lo, trigger_hi = above_cfg['lower'], above_cfg['higher']
                    reason = f"Applied above-trigger"

            if trigger_lo is not None:
                base_tick = (trigger_lo + trigger_hi) / 2
            else:
                # Shift current_tick by bias rather than alter ranges directly
                if positive_bias:
                    base_tick = current_tick * (1 + bias)
                    reason = f"Applied positive bias to current price"
                else:
                    base_tick = current_tick * (1 - bias)
                    reason = f"Applied negative bias to current price"

            # EXECUTE REBALANCE: remove + add based on shifted price
            # if pool.position_id:
            #     uni.remove_liquidity(pool.position_id)
            # lo, hi = uni.calculate_new_ticks(base_tick, base_cfg)
            # receipt = uni.add_liquidity(lo, hi, comm.amount_eth, cfg['max_slippage'])
            # if receipt.get('status') == 1:
            #     pool.position_id = uni.get_latest_position_id()

            # Update pool state
            pool.liquidity_range = {'min': lo, 'max': hi}
            pool.liquidity_amounts = {'amount_token0': amt['amount_token0'], 'amount_token1': amt['amount_token1']}

            history_entries.append(AgentHistory(
                agent_id=a.id,
                last_checked_at=now,
                last_rebalanced_at=now,
                rebalance_decision=True,
                positive_bias=positive_bias,
                rebalance_logic=logic,
                rebalance_bias=bias,
                reason=reason
            ))

        # Persist updates
        if new_pools:
            db.add_all(new_pools)
        db.add_all(history_entries)
        db.commit()
        logging.info("Rebalancing complete with detailed history.")

    except Exception as e:
        logging.error(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    liquidity_pool_rebalancing()
