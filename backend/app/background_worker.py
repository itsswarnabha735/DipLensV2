"""
Background worker for DipLens v2

Runs scheduled tasks for updating sector snapshots and other periodic jobs.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging
import pytz

logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler()

# IST timezone
IST = pytz.timezone('Asia/Kolkata')


def update_sector_snapshots_job():
    """
    Job to update sector snapshot cache.
    
    This pre-computes sector metrics to avoid expensive calculations on every API call.
    """
    try:
        logger.info("Running scheduled sector snapshot update...")
        
        # Import here to avoid circular dependencies
        from app.routers.sector_snapshots import _update_snapshot_cache
        
        # Update cache
        _update_snapshot_cache()
        
        logger.info("Scheduled sector snapshot update completed successfully")
        
    except Exception as e:
        logger.error(f"Error in scheduled sector snapshot update: {e}", exc_info=True)


def update_sector_candidates_job():
    """
    Job to update sector candidates cache.
    
    This pre-computes candidate rankings to avoid expensive calculations on every detail page load.
    """
    try:
        logger.info("Running scheduled sector candidates update...")
        
        # Import here to avoid circular dependencies
        from app.routers.suggestions import _update_candidates_cache
        
        # Update cache for all sectors
        _update_candidates_cache()
        
        logger.info("Scheduled sector candidates update completed successfully")
        
    except Exception as e:
        logger.error(f"Error in scheduled sector candidates update: {e}", exc_info=True)


def check_alerts_job():
    """
    Job to evaluate alert rules against real-time market data.
    """
    try:
        # Import here to avoid circular dependencies
        from app.alerts.worker import check_alerts_cycle
        check_alerts_cycle()
    except Exception as e:
        logger.error(f"Error in alert check job: {e}", exc_info=True)


def is_market_open() -> bool:
    """
    Check if Indian market is currently open.
    
    Market hours: Monday-Friday, 9:15 AM - 3:30 PM IST
    """
    now = datetime.now(IST)
    
    # Check if it's a weekday
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    
    # Check time (9:15 AM to 3:30 PM)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    return market_open <= now <= market_close


def start_background_jobs():
    """
    Start all background jobs.
    
    Should be called on application startup.
    """
    logger.info("Starting background scheduler...")
    
    # Update sector snapshots every 15 minutes during market hours (9:15 AM - 3:30 PM IST)
    # Monday-Friday only
    scheduler.add_job(
        update_sector_snapshots_job,
        trigger=CronTrigger(
            minute='*/15',  # Every 15 minutes
            hour='9-15',    # Between 9 AM and 3 PM
            day_of_week='mon-fri',  # Weekdays only
            timezone=IST
        ),
        id='sector_snapshot_update',
        name='Update Sector Snapshots',
        replace_existing=True,
        max_instances=1  # Prevent overlapping runs
    )

    # Check alerts every 2 minutes (during market hours + pre/post)
    # For now, running always for testing
    scheduler.add_job(
        check_alerts_job,
        trigger=CronTrigger(
            minute='*/2',
            timezone=IST
        ),
        id='check_alerts',
        name='Check Alerts',
        replace_existing=True,
        max_instances=1
    )
    
    # ALWAYS run initial update on startup to pre-populate cache
    # This takes ~2-3 minutes with NSE provider but happens in background
    logger.info("Running initial sector data update on startup (snapshots + candidates, ~3-4 minutes)...")
    try:
        import threading
        # Run in separate thread to not block startup
        def initial_update():
            try:
                logger.info("Updating sector snapshots...")
                update_sector_snapshots_job()
                logger.info("Updating sector candidates...")
                update_sector_candidates_job()
                logger.info("Initial sector cache fully populated successfully")
            except Exception as e:
                logger.error(f"Initial sector cache update failed: {e}", exc_info=True)
        
        thread = threading.Thread(target=initial_update, name="InitialCacheUpdate", daemon=True)
        thread.start()
    except Exception as e:
        logger.error(f"Failed to start initial cache update: {e}")
    
    # Start the scheduler
    scheduler.start()
    logger.info("Background scheduler started successfully")


def stop_background_jobs():
    """
    Stop all background jobs.
    
    Should be called on application shutdown.
    """
    logger.info("Stopping background scheduler...")
    scheduler.shutdown(wait=False)
    logger.info("Background scheduler stopped")
