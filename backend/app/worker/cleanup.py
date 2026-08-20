import asyncio
import logging
import shutil
import time
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


async def cleanup_task():
    logger.info("Starting cleanup task loop")
    while True:
        try:
            now = time.time()
            temp_dir = Path(settings.TEMP_STORAGE_PATH)

            if temp_dir.exists():
                count = 0
                for item in temp_dir.iterdir():
                    # Check age of file/directory
                    try:
                        mtime = item.stat().st_mtime
                        if now - mtime > settings.CLEANUP_TTL_SECONDS:
                            if item.is_dir():
                                shutil.rmtree(item, ignore_errors=True)
                            else:
                                item.unlink(missing_ok=True)
                            count += 1
                    except Exception as e:
                        logger.error(f"Failed to clean up {item}: {e}")

                if count > 0:
                    logger.info(f"Cleanup completed: removed {count} old items")
        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")

        # Sleep before next cleanup run (e.g. 10 minutes)
        await asyncio.sleep(600)
