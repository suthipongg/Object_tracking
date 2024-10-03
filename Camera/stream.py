import uvicorn
from fastapi import FastAPI

import logging
    

from services.redis_service import RedisClient

logging.basicConfig(level = logging.INFO)
logging.info("stream service")

RedisClient.connecct()
if not RedisClient.check_redis_connection:
    raise Exception("Redis connection failed")
else:
    RedisClient.clear_redis_data('frame')
    RedisClient.set_redis_data('stream', {'status':False})

app = FastAPI(
    title="Project Object tracking", 
    description=f"Created by music",
    docs_url="/",
    version="1.0.0",
    debug=False
)

from services.stream_service import stream_route
app.include_router(stream_route)

def run_app():
    uvicorn.run("stream:app", 
                host='0.0.0.0', 
                port=9060, 
                log_level="info", 
                reload=False
                )

if __name__ == "__main__":
    run_app()