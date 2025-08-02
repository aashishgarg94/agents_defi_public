import json
from datetime import datetime, timedelta
from src.aizen.signals.signals import Signals

with open("lp_rebalancing_config.json", "r") as f:
    config = json.load(f)

strategies = config["rebalance_strategies"]

# Evaluate conditions and decide action
action_taken = None
now = datetime.now().isoformat() + "Z"
last_day = now() - timedelta(days=28)

signals = Signals(ticker="eth", date_from=now, date_to=last_day)
current_signals = signals.get_current_signals()

current_signals["distance_to_edge"] = min(abs(current_signals["price"] - config["liquidity_range"]["min_price"]), abs(config["liquidity_range"]["max_price"] - current_signals["price"]))
current_signals["in_range"] = config["liquidity_range"]["min_price"] <= current_signals["price"] <= config["liquidity_range"]["max_price"]

# Make new entry
make_conditions = strategies["make_new_entry"]["conditions"]
if (config["existing_position"] is None and
    eval(f"{current_signals['rsi']} {make_conditions['rsi']}")):
    config["position_id"] = f"pos-{int(datetime.now().timestamp())}"
    config["existing_position"] = {"token_id": config["position_id"]}
    config["last_rebalanced_at"].append(now)
    action_taken = "make_new_entry"
    print(f"{now}: Executing make_new_entry - New position created: {config['position_id']}")

# Shift range (only if no prior action and position exists)
shift_conditions = strategies["shift_range"]["conditions"]
if (not action_taken and
    config["existing_position"] is not None and
    current_signals["in_range"] == shift_conditions["in_range"] and
    eval(f"{current_signals['distance_to_edge']} {shift_conditions['distance_to_edge']}")):
    # Simulate range shift (e.g., adjust by buffer); here we just log
    config["last_rebalanced_at"].append(now)
    action_taken = "shift_range"
    print(f"{now}: Executing shift_range - Range adjusted by buffer")

# Exit (only if no prior action and position exists)
exit_conditions = strategies["exit"]["conditions"]
if (not action_taken and
    config["existing_position"] is not None and
    eval(f"{current_signals['rsi']} {exit_conditions['rsi']}")):
    config["existing_position"] = None
    config["position_id"] = None
    config["last_rebalanced_at"].append(now)
    action_taken = "exit"
    print(f"{now}: Executing exit - Position cleared")

# Update last_checked_at
config["last_checked_at"] = now

# Save updated config
if action_taken:
    with open("lp_rebalancing_config.json", "w") as f:
        json.dump(config, f, indent=4)
        print(f"Config updated after {action_taken}")
else:
    print(f"{now}: No action taken - Conditions not met")