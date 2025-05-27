"""
Main execution file for BetBot with scheduling using APScheduler
"""
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from pytz import timezone
from src.betbot import BetBot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bet_bot.log')
    ]
)
logger = logging.getLogger(__name__)

def execute_bot():
    """Executes a bot instance"""
    try:
        logger.info(f"Starting bot execution at {datetime.now(tz=timezone('America/Sao_Paulo')).strftime('%H:%M:%S')}")
        bot = BetBot()
        bot.execute()
    except Exception as e:
        logger.error(f"Error during bot execution: {e}")
    finally:
        logger.info(f"Execution finished at {datetime.now(tz=timezone('America/Sao_Paulo')).strftime('%H:%M:%S')}")

def job_listener(event):
    """Listener for scheduler events"""
    if event.exception:
        logger.error(f'Job failed: {event.job_id}')
    else:
        logger.info(f'Job completed: {event.job_id}')

def schedule_executions(scheduler):
    """Schedules bot executions every 2 hours"""
    schedules = [
        "00:20", "02:20", "04:20", "06:20", "08:20", "10:20",
        "12:20", "14:20", "16:20", "18:20", "20:20", "22:20"
    ]
    
    for schedule in schedules:
        hour, minute = map(int, schedule.split(':'))
        scheduler.add_job(
            execute_bot,
            CronTrigger(
                hour=hour,
                minute=minute,
                timezone=timezone('America/Sao_Paulo')
            ),
            id=f'execution_{schedule.replace(":", "_")}',
            name=f'Execution {schedule}'
        )
        logger.info(f"Scheduled execution for {schedule}")

def main():
    logger.info("Starting BetBot scheduling system...")
    
    scheduler = BlockingScheduler()
    scheduler.add_listener(job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)
    
    schedule_executions(scheduler)
    
    now = datetime.now(tz=timezone('America/Sao_Paulo'))
    current_hour = now.hour
    current_minute = now.minute
    
    # Execute immediately if within schedule window
    if (0 <= current_hour <= 22) and (current_hour % 2 == 0 or current_hour == 0):
        if (current_hour == 22 and current_minute <= 10) or current_minute <= 10:
            execute_bot()
    
    try:
        logger.info("Starting scheduler...")
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Shutting down system...")
        scheduler.shutdown()
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        scheduler.shutdown()

if __name__ == "__main__":
    main()
