from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketState
import uvicorn
import os, sys, logging, time
from pathlib import Path
import Config
import cv2
import numpy as np
import asyncio
import base64

ROOT = Path(__file__).resolve().parents[0]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

logging.basicConfig(level = logging.INFO)
logging.info("webserver receive image initial")

for file in os.listdir(ROOT / Config.UPLOAD_FOLDER):
    os.remove(ROOT / Config.UPLOAD_FOLDER / file)

app = FastAPI()

cam_info = {}
for cam_id in range(Config.N_CAM):
    cam_info[cam_id] = {"timestamp":0, "save":False, "video":None, "frame":None, "realtime":False}

# video_name = timestamp_camID.ExtName
def name_video(cam_id, current_time):
    return str(current_time) + "_" + str(cam_id) + Config.EXT_VIDEO

# create video file
def create_video(cam_id, current_time):
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    file_name = name_video(cam_id, current_time)
    out = cv2.VideoWriter(str(ROOT / Config.UPLOAD_FOLDER / file_name), fourcc, Config.FPS, (Config.WIDTH, Config.HEIGHT))
    return out

# decode image data from espcam
def preprocess(img):
    img = np.frombuffer(img, np.uint8)
    img = cv2.imdecode(img, cv2.IMREAD_COLOR)
    return img

# move video file when finish recording
def move_file(file):
    src_file = Path(ROOT / Config.UPLOAD_FOLDER / file)
    dst_file = Path(ROOT / Config.VIDEO_TEMP_FOLDER / file)
    src_file.rename(dst_file)

# receive video and save to video file for each camera id
def receive_video(data, cam_id):
    img = preprocess(data)
    current_time = round(time.time())
    # if not save video, create new video file
    if not cam_info[cam_id]["save"]:
        cam_info[cam_id]["timestamp"] = current_time
        cam_info[cam_id]["save"] = True
        cam_info[cam_id]["video"] = create_video(cam_id, current_time)
    
    # if camera was requested to stream video, save frame to memory else not save
    if cam_info[cam_id]["realtime"]:
        cam_info[cam_id]["frame"] = img
    else:
        cam_info[cam_id]["frame"] = None
    cam_info[cam_id]["video"].write(img)
    
    # check if video length time is reached, release video file
    if current_time - cam_info[cam_id]["timestamp"] > Config.video_length_time:
        cam_info[cam_id]["save"] = False
        cam_info[cam_id]["video"].release()
        move_file(name_video(cam_id, cam_info[cam_id]["timestamp"]))


@app.websocket("/upload_image")
async def video_stream(websocket: WebSocket):
    try:
        # accept connection
        await websocket.accept()
        # Receive chip ID from client
        chip_id = await websocket.receive_text()
        cam_id = Config.CHIP_ID.get(chip_id)
        if cam_id is None:
            await websocket.send_text("Invalid chip ID")
            await websocket.close()
            return
        # while connection is open
        while (websocket.application_state == WebSocketState.CONNECTED and websocket.client_state == WebSocketState.CONNECTED):
            try:
                # Receive image data from ESP32-CAM
                data = await websocket.receive_bytes()
                if data:
                    receive_video(data, cam_id)
                    await websocket.send_text(f"Timestamp: {str(time.time())}, Image received")
            except Exception as e:
                print(f"Error receiving image: {e}")
                await websocket.send_text('Invalid data received')
        await websocket.close()
        return f"Connection closed for cam_id {cam_id}"
    except Exception as e:
        print(str(e))
        await websocket.send_text('something went wrong')
        await websocket.close()
        return str(e), 500


@app.websocket('/stream')
async def stream(websocket: WebSocket):
    try:
        # accept connection
        await websocket.accept()
        cam_id = await websocket.receive_text()
        if cam_id is None:
            await websocket.send_text("Invalid chip ID")
            await websocket.close()
            return
        cam_id = int(cam_id)
        print(f"Start streaming cam_id {cam_id}")
        # while connection is open
        while (websocket.application_state == WebSocketState.CONNECTED and websocket.client_state == WebSocketState.CONNECTED):
            # if frame is saved in memory, send frame to server
            if cam_info[cam_id]["frame"] is not None:
                _, buffer = cv2.imencode('.jpg', cam_info[cam_id]["frame"])
                base64_frame = base64.b64encode(buffer).decode("utf-8")
                await websocket.send_text(base64_frame)
            # if frame is not saved in memory, send text to server
            else:
                cam_info[cam_id]['realtime'] = True
                await websocket.send_text('Wait camera')
            await asyncio.sleep(0.5)
        await websocket.close()
        return f"cam_id {cam_id} stopped streaming"
    except Exception as e:
        print(str(e))
        await websocket.close()
        cam_info[cam_id]['realtime'] = False
        return str(e), 500
    
if __name__ == "__main__":
    uvicorn.run("app:app", 
                host='0.0.0.0', 
                port=8080, 
                log_level="info", 
                reload=False
                )