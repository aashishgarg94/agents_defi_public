from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from src.aizen.jobs import fetch_and_store_crypto_data, liquidity_pool_rebalancing, process_marketplace_fees
import time
import logging

logging.basicConfig(level=logging.INFO)

def start_scheduler():
    logging.info("Scheduler starting...")
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_store_crypto_data, IntervalTrigger(minutes=5))
    # scheduler.add_job(liquidity_pool_rebalancing, IntervalTrigger(minutes=5))
    # scheduler.add_job(
    #     process_marketplace_fees, 
    #     CronTrigger(day_of_week='sun', hour=10, minute=0),
    #     id="weekly_marketplace_fee",
    #     replace_existing=True
    # )
    # scheduler.start()
    
    try:
        while True:
            logging.info("Scheduler is running...")
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Scheduler shutting down...")
        scheduler.shutdown()

if __name__ == "__main__":
    start_scheduler()
