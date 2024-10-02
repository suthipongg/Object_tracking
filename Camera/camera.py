import logging

from services.redis_service import RedisClient
from services.capture_service import CaptureService

RedisClient.connecct()
if not RedisClient.check_redis_connection():
    RedisClient.clear_redis_data('frame')
    raise Exception("Redis connection failed")

logging.basicConfig(level = logging.DEBUG)
logging.info("create video service initial")

camera = CaptureService()
camera.run_camera()