from sqlalchemy.orm import Session
from src.aizen.database import SessionLocal
from datetime import datetime, timedelta
from decimal import Decimal
from src.aizen.models import User, Agent, UserCommission, UserDailyEarnedFee
from web3 import Web3
import logging
import ast

logging.basicConfig(level=logging.INFO)

w3 = Web3(Web3.HTTPProvider("https://sepolia.infura.io/v3/35be664c4dfe4302abed873f7a231f42"))
WEEKS_IN_YEAR = Decimal(52)
DAYS_IN_YEAR = Decimal(365)

def process_marketplace_fees():
    db: Session = SessionLocal()
    now = datetime.utcnow()
    today_is_sunday = now.weekday() == 6  # Sunday = 6

    if not today_is_sunday:
        logging.info("Not Sunday. Skipping fee processing.")
        return

    commissions = db.query(UserCommission).filter(
        UserCommission.is_active == True,
        UserCommission.is_commissioned == True
    ).all()

    user_earned_fees = {}

    for commission in commissions:
        try:
            # Fetch relevant users and agent
            sender = db.query(User).filter(User.id == commission.user_id).first()
            agent = db.query(Agent).filter(
                Agent.id == commission.agent_id,
                Agent.is_active == True,
                Agent.is_deployed == True
            ).first()

            if not agent:
                logging.warning(f"Agent {commission.agent_id} not active or deployed. Skipping.")
                continue

            receiver = db.query(User).filter(User.id == agent.user_id).first()
            if agent.user_id not in user_earned_fees:
                user_earned_fees[agent.user_id] = 0


            # Calculate weekly fee
            annual_fee_pct = Decimal(agent.subscription_fee) / 100
            daily_fee_eth = Decimal(commission.amount_eth) * annual_fee_pct / DAYS_IN_YEAR

            # Check if sender has sufficient balance
            balance = w3.eth.get_balance(sender.wallet_address)
            balance_eth = Decimal(w3.from_wei(balance, 'ether'))

            if balance_eth < daily_fee_eth:
                logging.warning(f"User {sender.id} has insufficient balance ({balance_eth:.6f} ETH). Disabling commission.")
                commission.is_active = False
                db.commit()
                continue

            # Prepare and send transaction
            tx = {
                'nonce': w3.eth.get_transaction_count(sender.wallet_address),
                'to': receiver.wallet_address,
                'value': w3.to_wei(daily_fee_eth, 'ether'),
                'gas': 21000,
                'gasPrice': w3.eth.gas_price,
                'chainId': 11155111  # Sepolia chain ID
            }

            signed_tx = w3.eth.account.sign_transaction(tx, private_key=sender.private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt.status == 1:
                user_earned_fees[agent.user_id] += daily_fee_eth
                logging.info(f"✅ {daily_fee_eth:.6f} ETH transferred from user {sender.id} to agent owned by {receiver.id}")
            else:
                logging.error(f"❌ Transaction failed on-chain for user {sender.id}. Skipping.")
        
        except Exception as e:
            try:
                error_dict = ast.literal_eval(str(e))
                error_message = error_dict.get('message', 'Unknown error')
            except Exception:
                error_message = str(e)

            logging.error(f"⚠️ Error processing commission ID {commission.id}: {error_message}")
            continue

    for user_id, earned_fee in user_earned_fees:
        new_entry = UserDailyEarnedFee(user_id = user_id, fee_earned = earned_fee)
        db.add(new_entry)

    db.commit()

    db.close()

if __name__ == "__main__":
    process_marketplace_fees()
