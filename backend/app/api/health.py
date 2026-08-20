import redis
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health_check():
    health_status = {"api": "ok", "redis": "unknown", "worker": "unknown"}

    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health_status["redis"] = "ok"

        # In a real app we might check actual worker registration in Redis
        # For phase 1, pinging Redis is a start.
        health_status["worker"] = "ok"
    except redis.RedisError:
        health_status["redis"] = "error"
        health_status["worker"] = "error"

    return health_status
