import os, sys, logging, time
from pathlib import Path
from datetime import datetime, date

ROOT = Path(__file__).resolve().parents[0]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from Configs.config import Config
from modules.manage_media import scan_video
from modules.object_tracking import ObjectTracking
from modules.post_data import post_camera, post_frame
from services.redis_service import RedisClient

logging.info("object tracking")


class ObjectTrackingService:
    def __init__(self):
        self.object_tracking = ObjectTracking()

    def check_video(self):
        logging.info("---> check video")
        for video in os.listdir(Config.VIDEO_CURRENT):
            if video.endswith(Config.EXT_VIDEO):
                current_video = Config.VIDEO_CURRENT / video
                break
            os.remove(Config.VIDEO_CURRENT / video)
            logging.info(f"remove {Config.VIDEO_CURRENT / video}")
        else:
            current_video = scan_video()
        return current_video

    def run_tracking(self):
        while True:
            logging.info("=====================================")
            current_video = self.check_video()
            if not current_video:
                logging.info("no video found")
                time.sleep(5)
                continue

            logging.info("start tracking")
            timestamp = int(current_video.stem)
            data_info = self.object_tracking.tracking_process(current_video)
            data_info['timestamp'] = timestamp

            time_device = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            # post_camera(data_info['count'], time_device)
            # post_frame(data_info['frame'], time_device)

            logging.info("end tracking")