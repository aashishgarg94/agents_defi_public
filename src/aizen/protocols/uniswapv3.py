from web3 import Web3
import json
import time
from dotenv import load_dotenv
from web3.exceptions import Web3RPCError, TimeExhausted
from decimal import Decimal
from src.aizen.models import AgentStat
from sqlalchemy.orm import Session
from src.aizen.database import SessionLocal

import logging

logging.basicConfig(level=logging.INFO)

load_dotenv(override=True)
db: Session = SessionLocal()

GOERLI_ENDPOINT ="https://sepolia.infura.io/v3/7c53966f13674d06b53df9e4a635145b"
NETWORK = GOERLI_ENDPOINT

# Goerli Testnet Contract Addresses
# USDC_ETH_POOL_ADDRESS = "0x4e68Ccd3E89f51C3074ca5072bbAC773960dFa36"  # USDC/ETH 0.3% pool on Goerli
# NPM_ADDRESS = "0xC36442b4a4522E871399CD717aBDD847Ab11FE88"  # NonfungiblePositionManager on Goerli

USDC_ETH_POOL_ADDRESS = "0x88A3e4F35D64aAD41A6d4030ac9AFE4356c34bcB" # USDC/ETH 0.3% pool (example, verify on Sepolia)
NPM_ADDRESS = "0x1238536071E1c677A632429e3655c799b22cDA52".lower()  # NonfungiblePositionManager on Sepolia
USDC_ADDRESS = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238".lower()  # Test USDC on Sepolia
WETH_ADDRESS = "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14".lower() # Wrapped ETH on Sepolia

ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
]

WETH_ABI = [
    {"constant": False, "inputs": [], "name": "deposit", "outputs": [], "stateMutability": "payable", "type": "function"},
    {"constant": True, "inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
]

class UniswapV3:
    def __init__(self, private_key, account_address, pool_details, agent_id, user_id):
        self.w3 = Web3(Web3.HTTPProvider(GOERLI_ENDPOINT))

        if not self.w3.is_connected():
            raise Exception("Failed to connect to Goerli network")

        # Load ABI files (assumes they're in an 'abi' directory)
        with open("src/aizen/protocols/abi/usdc_eth/uniswap_v3_pool_abi.json", "r") as f:
            POOL_ABI = json.load(f)
        with open("src/aizen/protocols/abi/uniswap_v3_npm_abi.json", "r") as f:
            NPM_ABI = json.load(f)
        
        self.pool_details = pool_details
        self.fee_tier = pool_details['fee_tier']
        self.agent_id = agent_id
        self.user_id = user_id
        pool_address = get_pool_address(pool_details)

        self.pool_address = Web3.to_checksum_address(pool_address)
        self.npm_address = Web3.to_checksum_address(NPM_ADDRESS)

        self.pool_contract = self.w3.eth.contract(address=self.pool_address, abi=POOL_ABI)
        self.npm_contract = self.w3.eth.contract(address=self.npm_address, abi=NPM_ABI)

        self.private_key = private_key
        self.account_address = Web3.to_checksum_address(account_address)
        balance = self.w3.eth.get_balance(self.account_address)
        logging.info(f"Account balance: {self.w3.from_wei(balance, 'ether')} Sepolia ETH")
        pending_nonce = self.w3.eth.get_transaction_count(self.account_address, 'pending')
        logging.info(f"'{pending_nonce}'===pending nonce")
        self.desired_range_percent = 0.10  # 10% price range
        self.position_id = None

    def get_eth_balance(self):
        return self.w3.eth.get_balance(self.account_address)
    
    def get_current_tick(self):
        slot0 = self.pool_contract.functions.slot0().call()
        return slot0[1]
    
    def get_token_balance(self, token_contract):
        return token_contract.functions.balanceOf(self.account_address).call()

    def get_eth_price(self):
        # Get sqrtPriceX96 from pool slot0
        sqrtPriceX96 = self.pool_contract.functions.slot0().call()[0]
        price = (Decimal(sqrtPriceX96) ** 2 / (2 ** 192))
        return price
    
    def get_latest_position_id(self):
        latest_block = self.w3.eth.block_number
        events = self.npm_contract.events.Transfer().create_filter(
            from_block=latest_block - 500,
            to_block="latest",
            argument_filters={"to": self.account_address},
        ).get_all_entries()

        if events:
            return int(events[-1]["args"]["tokenId"])
        return None

    def get_position_ticks(self, position_id):
        position = self.npm_contract.functions.positions(position_id).call()
        return position[4], position[5]

    def calculate_new_ticks(self, current_tick, range_config):
        """
        Calculate the new tick range based on the current tick and percentage range.

        :param current_tick: The current tick from the pool.
        :param range_config: Dictionary with 'lower', 'upper', and optional 'buffer'.
        :return: Tuple of (lower_tick, upper_tick).
        """
        lower = range_config["lower"]
        upper = range_config["upper"]
        buffer = range_config.get("buffer", 0)

        # Convert tick to price
        price = 1.0001 ** current_tick
        logging.info(f"Current Price: {price}")

        if price <= 0:
            raise ValueError(f"Invalid price calculated: {price}")

        # Expand range by buffer if needed
        lower_price = price * (1 - lower - buffer)
        upper_price = price * (1 + upper + buffer)

        logging.info(f"Lower Price: {lower_price}")
        logging.info(f"Upper Price: {upper_price}")

        if lower_price <= 0 or upper_price <= 0:
            raise ValueError(f"Invalid price range: lower={lower_price}, upper={upper_price}")

        # Convert prices to ticks
        lower_tick = int(self.price_to_tick(lower_price))
        upper_tick = int(self.price_to_tick(upper_price))

        # Adjust to nearest valid tick spacing
        if self.fee_tier == 0.01:
            tick_spacing = 1
        elif self.fee_tier == 0.05:
            tick_spacing = 10
        elif self.fee_tier == 0.3:
            tick_spacing = 60
        elif self.fee_tier == 1:
            tick_spacing = 200
        else:
            raise ValueError("Unsupported fee tier")

        lower_tick -= lower_tick % tick_spacing
        upper_tick -= upper_tick % tick_spacing

        # Ensure the ticks are not the same
        if lower_tick == upper_tick:
            lower_tick -= tick_spacing
            upper_tick += tick_spacing

        logging.info(f"Final Lower Tick: {lower_tick}, Final Upper Tick: {upper_tick}")
        return lower_tick, upper_tick



    def price_to_tick(self, price):
        import math
        return math.log(price, 1.0001)

    def remove_liquidity(self, position_id):
    # Fetch position details
        position_data = self.npm_contract.functions.positions(position_id).call()
        liquidity = position_data[7]

        if liquidity < 1000:
            logging.info("⚠️ Not enough liquidity to remove.")
            return None

        # Fetch nonce, balance, and check
        pending_nonce = self.w3.eth.get_transaction_count(self.account_address, 'pending')
        balance = self.w3.eth.get_balance(self.account_address)

        # estimated_gas_cost = self.w3.to_wei('200', 'gwei') * 1_000_000  # 200 gwei * 1M gas
        estimated_total_gas = 400_000  # 250k for decrease + 150k for collect
        gas_price = self.w3.to_wei('20', 'gwei')  # 20 gwei per gas
        estimated_gas_cost = estimated_total_gas * gas_price
        if balance < estimated_gas_cost:
            logging.info(f"❌ Insufficient ETH: {self.w3.from_wei(balance, 'ether')} ETH < {self.w3.from_wei(estimated_gas_cost, 'ether')} ETH needed")
            return None

        nonce = pending_nonce
        deadline = int(time.time()) + 1200  # 20 minutes

        # Gas fee settings
        base_fee = self.w3.eth.get_block('latest')['baseFeePerGas']
        # max_priority_fee = self.w3.to_wei('3', 'gwei')
        # max_fee_per_gas = base_fee + max_priority_fee

        max_priority_fee = self.w3.to_wei('2', 'gwei')   # priority fee 2 gwei
        max_fee_per_gas = self.w3.to_wei('20', 'gwei')    # total max fee per gas 20 gwei


        # Build decreaseLiquidity transaction
        decrease_txn = self.npm_contract.functions.decreaseLiquidity({
            'tokenId': position_id,
            'liquidity': liquidity,
            'amount0Min': 0,
            'amount1Min': 0,
            'deadline': deadline
        }).build_transaction({
            'from': self.account_address,
            'nonce': nonce,
            'gas': 500000,  # Increased gas limit
            'maxFeePerGas': max_fee_per_gas,
            'maxPriorityFeePerGas': max_priority_fee,
            'chainId': 11155111
        })

        # Sign and send the transaction
        signed_txn = self.w3.eth.account.sign_transaction(decrease_txn, self.private_key)
        try:
            txn_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            logging.info(f"🔵 DecreaseLiquidity tx sent: {txn_hash.hex()}")
            receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash, timeout=300)

            logs = self.npm_contract.events.DecreaseLiquidity().process_receipt(receipt)
            amount0 = sum(log['args']['amount0'] for log in logs)
            amount1 = sum(log['args']['amount1'] for log in logs)

            price = self.get_eth_price()
            removed_eth = (Decimal(amount0) / Decimal(10**6)) / Decimal(price) + (Decimal(amount1) / Decimal(1e18))

            agent_stat = db.query(AgentStat).filter(AgentStat.position_id == position_id).first()

            agent_stat.removed_eth= removed_eth

            db.add(agent_stat)
            db.commit()

            if receipt['status'] == 1:
                logging.info(f"✅ Liquidity removed. Tx: {txn_hash.hex()}")
                # Proceed to collect fees
                return self.collect_fees(position_id, nonce + 1)
            else:
                logging.info(f"❌ Liquidity removal failed. Receipt: {receipt}")
                return None

        except TimeExhausted:
            logging.info(f"⏳ Transaction {txn_hash.hex()} still pending after 300s. Check Sepolia Etherscan.")
            return {"pending_tx": txn_hash.hex()}
        except Exception as e:
            logging.info(f"🚨 Unexpected Error during remove_liquidity: {e}")
            return None

    def collect_fees(self, position_id, nonce):
    # Gas fee settings
        base_fee = self.w3.eth.get_block('latest')['baseFeePerGas']
        # max_priority_fee = self.w3.to_wei('3', 'gwei')
        # max_fee_per_gas = base_fee + max_priority_fee

        max_priority_fee = self.w3.to_wei('2', 'gwei')   # priority fee 2 gwei
        max_fee_per_gas = self.w3.to_wei('20', 'gwei')    # total max fee per gas 20 gwei


        # Build collect transaction
        collect_txn = self.npm_contract.functions.collect({
            'tokenId': position_id,
            'recipient': self.account_address,
            'amount0Max': 2**128 - 1,
            'amount1Max': 2**128 - 1
        }).build_transaction({
            'from': self.account_address,
            'nonce': nonce,
            'gas': 200000,  # Gas limit for collect
            'maxFeePerGas': max_fee_per_gas,
            'maxPriorityFeePerGas': max_priority_fee,
            'chainId': 11155111
        })

        # Sign and send the transaction
        signed_txn = self.w3.eth.account.sign_transaction(collect_txn, self.private_key)
        try:
            txn_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            logging.info(f"🔵 Collect tx sent: {txn_hash.hex()}")
            receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash, timeout=300)

            logs = self.npm_contract.events.Collect().process_receipt(receipt)
            amount0 = sum(log['args']['amount0'] for log in logs)
            amount1 = sum(log['args']['amount1'] for log in logs)

            price = self.get_eth_price()
            rewards_eth = (Decimal(amount0) / Decimal(10**6)) / Decimal(price) + (Decimal(amount1) / Decimal(1e18))

            agent_stat = db.query(AgentStat).filter(AgentStat.id == self.agent_id, AgentStat.position_id == position_id).first()
            invested_eth = agent_stat.invested_eth or Decimal('0')
            removed_eth = agent_stat.removed_eth or Decimal('0')
            final_eth = removed_eth + rewards_eth

            # Impermanent loss = (removed ETH + rewards earned) - invested ETH
            # If this value is negative, it means a loss compared to HODLing
            impermanent_loss = final_eth - invested_eth
            
            agent_stat.reward_earned=rewards_eth
            agent_stat.final_eth = final_eth
            agent_stat.impermanent_loss = impermanent_loss

            db.add(agent_stat)
            db.commit()

            if receipt['status'] == 1:
                logging.info(f"✅ Fees collected. Tx: {txn_hash.hex()}")
                return receipt
            else:
                logging.info(f"❌ Fee collection failed. Receipt: {receipt}")
                return None

        except TimeExhausted:
            logging.info(f"⏳ Transaction {txn_hash.hex()} still pending after 300s. Check Sepolia Etherscan.")
            return {"pending_tx": txn_hash.hex()}
        except Exception as e:
            logging.info(f"🚨 Unexpected Error during collect_fees: {e}")
            return None
        
    def burn_position(self, position_id, nonce=None):
        # Make sure you already removed all liquidity and collected all fees!

        # Get fresh gas info
        base_fee = self.w3.eth.get_block('latest')['baseFeePerGas']
        max_priority_fee = self.w3.to_wei('3', 'gwei')
        max_fee_per_gas = base_fee + max_priority_fee + self.w3.to_wei('10', 'gwei')

        # If nonce not provided, fetch it
        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.account_address, 'pending')

        # Build the burn transaction
        burn_txn = self.npm_contract.functions.burn(position_id).build_transaction({
            'from': self.account_address,
            'nonce': nonce,
            'gas': 300_000,  # burning is cheap
            'maxFeePerGas': max_fee_per_gas,
            'maxPriorityFeePerGas': max_priority_fee,
            'chainId': 11155111  # Sepolia
        })

        # Sign and send
        signed_txn = self.w3.eth.account.sign_transaction(burn_txn, private_key=self.private_key)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"🔵 Sent burn position txn: {txn_hash.hex()}")

        # Wait for receipt
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash, timeout=300)
            if receipt['status'] == 1:
                print(f"✅ Successfully burned position NFT. TxHash: {txn_hash.hex()}")
                return receipt
            else:
                print(f"❌ Burn transaction failed. Receipt: {receipt}")
                return None
        except Exception as e:
            print(f"⚠️ Error while waiting for burn receipt: {e}")
            return None
        
    def approve_token(self, token_contract, amount):
        allowance = token_contract.functions.allowance(self.account_address, self.npm_contract.address).call()
        if allowance < amount:
            nonce = self.w3.eth.get_transaction_count(self.account_address)
            tx = token_contract.functions.approve(self.npm_contract.address, amount).build_transaction({
                'from': self.account_address,
                'nonce': nonce,
                'gas': 100000,
                'maxFeePerGas': self.w3.to_wei('20', 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei('2', 'gwei'),
                'chainId':self.w3.eth.chain_id
            })
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
    def refund_unused_eth(self, amount):
        tx = {
            'to': self.account_address,
            'value': int(amount),
            'gas': 21000,
            'maxFeePerGas': self.w3.to_wei('20', 'gwei'),
            'maxPriorityFeePerGas': self.w3.to_wei('2', 'gwei'),
            'nonce': self.w3.eth.get_transaction_count(self.account_address),
            'chainId': self.w3.eth.chain_id
        }
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
    
    def add_liquidity(self, tick_lower, tick_upper, amount_eth, slippage):
        eth_balance = self.w3.eth.get_balance(self.account_address)

        if amount_eth > eth_balance:
            logging.error(f"Insufficient funds- Required {amount_eth}")
            return None
          
        logging.info(f"Adding liquidity for {amount_eth} ETH")
        price = self.get_eth_price()
        logging.info(f"Current ETH/USDC price: {price}")

        half_eth = Decimal(amount_eth) / 2
        amount_weth_wei = self.w3.to_wei(half_eth, 'ether')
        amount_usdc = int(half_eth * price * 10**6)  # USDC has 6 decimals

        token0 = self.pool_contract.functions.token0().call()
        token1 = self.pool_contract.functions.token1().call()
        slot0 = self.pool_contract.functions.slot0().call()
        current_tick = slot0[1]
        liquidity = self.pool_contract.functions.liquidity().call()
        logging.info(f"Token0: {token0}, Token1: {token1}")
        logging.info(f"Current tick: {current_tick}, Tick Lower: {tick_lower}, Tick Upper: {tick_upper}, Pool Liquidity: {liquidity}")

        if liquidity == 0:
            logging.info("Warning: Pool has no liquidity. This might be an uninitialized pool.")

        # Check token approvals and balances
        usdc_contract = self.w3.eth.contract(address=token0, abi=ERC20_ABI)
        weth_contract = self.w3.eth.contract(address=token1, abi=ERC20_ABI)

        usdc_balance = self.get_token_balance(usdc_contract)
        weth_balance = self.get_token_balance(weth_contract)
        eth_balance = self.w3.eth.get_balance(self.account_address)

        # Wrap ETH to WETH if needed
        if weth_balance < amount_weth_wei:
            wrap_amount = amount_weth_wei - weth_balance
            wrap_tx = weth_contract.functions.deposit().build_transaction({
                'from': self.account_address,
                'value': wrap_amount,
                'nonce': self.w3.eth.get_transaction_count(self.account_address),
                'gas': 100000,
                'maxFeePerGas': self.w3.to_wei('20', 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei('2', 'gwei'),
                'chainId': self.w3.eth.chain_id
            })
            signed_wrap = self.w3.eth.account.sign_transaction(wrap_tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_wrap.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # Approve tokens
        self.approve_token(usdc_contract, amount_usdc)
        self.approve_token(weth_contract, amount_weth_wei)

        deadline = int(time.time()) + 1200

        logging.info(f"USDC balance: {usdc_balance}, WETH balance: {weth_balance}")
        logging.info(f"Desired: USDC={amount_usdc}, WETH={amount_weth_wei}") 

        # Static call to simulate mint
        try:
            liquidity_preview = self.npm_contract.functions.mint({
                'token0': token0,
                'token1': token1,
                'fee': 3000,
                'tickLower': tick_lower,
                'tickUpper': tick_upper,
                'amount0Desired': amount_usdc,
                'amount1Desired': amount_weth_wei,
                'amount0Min': 0,
                'amount1Min': 0,
                'recipient': self.account_address,
                'deadline': deadline
            }).call({ 'from': self.account_address })

            logging.info(f"Previewed liquidity result: {liquidity_preview}")
        except Exception as e:
            logging.error(f"Static call to mint failed: {e}")
            return None
        
        amount0_used = liquidity_preview[2]  # amount0 (USDC)
        amount1_used = liquidity_preview[3] 

        # Actual mint transaction
        mint_tx = self.npm_contract.functions.mint({
            'token0': token0,
            'token1': token1,
            'fee': 3000,
            'tickLower': tick_lower,
            'tickUpper': tick_upper,
            'amount0Desired': amount_usdc,
            'amount1Desired': amount_weth_wei,
            'amount0Min': int(amount_usdc * (1 - slippage)),
            'amount1Min': int(amount_weth_wei * (1 - slippage)),
            'recipient': self.account_address,
            'deadline': deadline
        }).build_transaction({
            'from': self.account_address,
            'nonce': self.w3.eth.get_transaction_count(self.account_address),
            'gas': 1000000,
            'maxFeePerGas': self.w3.to_wei('50', 'gwei'),
            'maxPriorityFeePerGas': self.w3.to_wei('5', 'gwei'),
            'chainId': self.w3.eth.chain_id
        })

        signed = self.w3.eth.account.sign_transaction(mint_tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        logging.info(f"Liquidity added, tx hash: {tx_hash.hex()}")

        # Parse actual amounts used from Mint event
        logs = self.npm_contract.events.IncreaseLiquidity().process_receipt(receipt)
        used_usdc = 0
        used_weth = 0
        for log in logs:
            used_usdc += log['args']['amount0']
            used_weth += log['args']['amount1']

        # Refund unused tokens if any
        if amount_usdc > used_usdc:
            refund_amount_usdc = amount_usdc - used_usdc
            tx = usdc_contract.functions.transfer(self.account_address, refund_amount_usdc).build_transaction({
                'from': self.account_address,
                'nonce': self.w3.eth.get_transaction_count(self.account_address),
                'gas': 100000,
                'maxFeePerGas': self.w3.to_wei('20', 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei('2', 'gwei'),
                'chainId': self.w3.eth.chain_id
            })
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            self.w3.eth.send_raw_transaction(signed.raw_transaction)
            logging.info(f"Refunded {refund_amount_usdc} USDC")

        if amount_weth_wei > used_weth:
            refund_amount_weth = amount_weth_wei - used_weth
            tx = weth_contract.functions.transfer(self.account_address, refund_amount_weth).build_transaction({
                'from': self.account_address,
                'nonce': self.w3.eth.get_transaction_count(self.account_address),
                'gas': 100000,
                'maxFeePerGas': self.w3.to_wei('20', 'gwei'),
                'maxPriorityFeePerGas': self.w3.to_wei('2', 'gwei'),
                'chainId': self.w3.eth.chain_id
            })
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            self.w3.eth.send_raw_transaction(signed.raw_transaction)
            logging.info(f"Refunded {self.w3.from_wei(refund_amount_weth, 'ether')} WETH")

        normalized_usdc = Decimal(used_usdc) / Decimal(1e6)
        normalized_weth = Decimal(used_weth) / Decimal(1e18)
        invested_eth = (normalized_usdc / Decimal(price)) + normalized_weth
        position_id = self.get_latest_position_id()

        agent_stat = AgentStat(
            agent_id=self.agent_id,
            user_id=self.user_id,
            amount_eth =amount_eth,
            token0=token0,
            token1=token1,
            amount0=normalized_usdc,
            amount1=normalized_weth,
            price_at_entry=Decimal(price),
            invested_eth=invested_eth,
            tick_lower=tick_lower,
            tick_upper=tick_upper,
            position_id=position_id,
            pool_details=self.pool_details,
            is_active = True
        )

        db.add(agent_stat)
        db.commit()
        return receipt    


    def get_user_positions(self):
        """Fetch all active position IDs owned by the account."""
        position_ids = []

        # NPM doesn't have a direct "get all positions" function, so we scan recent tokens
        # Simplified: Check up to tokenId 10000 (adjust based on network activity)
        for token_id in range(1, 10000):  # Adjust range as needed
            try:
                owner = self.npm_contract.functions.ownerOf(token_id).call()

                if owner.lower() == self.account_address:
                    position = self.npm_contract.functions.positions(token_id).call()
                    if position[5] > 0:  # Liquidity > 0 means active
                        position_ids.append(token_id)
            except:
                break  # Stop if token doesn't exist
        return position_ids


def get_pool_address(pool_details):
    w3 = Web3(Web3.HTTPProvider(GOERLI_ENDPOINT))
    USDC_ADDRESS = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"  # Test USDC
    WETH_ADDRESS = "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14"
    WBTC_ADDRESS = "0xA0a5Ad2296B38Bd3b0A8090a10D74750D206B706" 
    FACTORY_ADDRESS = "0x0227628f3F023bb0B980b67D528571c95c6DaC1c"  # Uniswap V3 Factory on Sepolia
    FACTORY_ABI = [
        {
            "inputs": [
                {"internalType": "address", "name": "tokencA", "type": "address"},
                {"internalType": "address", "name": "tokenB", "type": "address"},
                {"internalType": "uint24", "name": "fee", "type": "uint24"}
            ],
            "name": "getPool",
            "outputs": [{"internalType": "address", "name": "pool", "type": "address"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]

    token_pair = pool_details["token_pair"]
    fee_tier = pool_details["fee_tier"]

    if token_pair == "ETH/USDC":
        tokenA, tokenB =  USDC_ADDRESS, WETH_ADDRESS
    elif token_pair == "BTC/USDC":
        tokenA, tokenB = USDC_ADDRESS, WBTC_ADDRESS
    else:
        raise ValueError("Invalid token pair. Use 'WETH/USDC' or 'WBTC/USDC'.")
    
    factory_contract = w3.eth.contract(address=FACTORY_ADDRESS, abi=FACTORY_ABI)

    FEE_TIER_MAPPING = {
        0.01: 100,   # 0.01% → 100
        0.05: 500,   # 0.05% → 500
        0.3: 3000,   # 0.3% → 3000
        1: 10000,    # 1% → 10000
    }

    fee_tier = FEE_TIER_MAPPING[fee_tier]  # 0.3% fee tier (3000 = 0.3%)

    pool_address = factory_contract.functions.getPool(
        tokenA,
        tokenB, 
        fee_tier         
    ).call()
    return pool_address
