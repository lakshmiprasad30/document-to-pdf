import redis
from rq import Queue

from app.core.config import settings

redis_conn = redis.from_url(settings.REDIS_URL)
job_queue = Queue(connection=redis_conn)
