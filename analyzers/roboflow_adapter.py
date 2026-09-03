"""Roboflow Sports adapter: video -> normalized pitch tracks + annotated preview/video."""
import argparse
import json
import os
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLO

from sports.common.view import ViewTransformer
from sports.configs.soccer import SoccerPitchConfiguration

PLAYER_CLASS_ID=2; CONFIG=SoccerPitchConfiguration()

def transform(detections,keypoints):
    mask=(keypoints.xy[0][:,0]>1)&(keypoints.xy[0][:,1]>1)&(keypoints.confidence[0]>.5)
    if mask.sum()<4:return None
    view=ViewTransformer(source=keypoints.xy[0][mask].astype(np.float32),target=np.array(CONFIG.vertices)[mask].astype(np.float32))
    anchors=detections.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
    return view.transform_points(anchors)/100.0

def main(source,output,tracks,device):
    output=Path(output); output.mkdir(parents=True,exist_ok=True); models=Path(os.environ.get("MODEL_DIR","/models"))
    players_model=YOLO(models/"football-player-detection.pt").to(device)
    pitch_model=YOLO(models/"football-pitch-detection.pt").to(device)
    ball_model=YOLO(models/"football-ball-detection.pt").to(device)
    cap=cv2.VideoCapture(source); fps=cap.get(cv2.CAP_PROP_FPS) or 25.; width=int(cap.get(3)); height=int(cap.get(4))
    writer=cv2.VideoWriter(str(output/"annotated.mp4"),cv2.VideoWriter_fourcc(*"mp4v"),fps,(width,height))
    tracker=sv.ByteTrack(frame_rate=int(fps),minimum_consecutive_frames=3); frames=[]; counts=Counter(); preview=None; index=0
    while True:
        ok,frame=cap.read()
        if not ok:break
        keypoints=sv.KeyPoints.from_ultralytics(pitch_model(frame,verbose=False)[0])
        detections=sv.Detections.from_ultralytics(players_model(frame,imgsz=1280,verbose=False)[0])
        detections=tracker.update_with_detections(detections); players=detections[detections.class_id==PLAYER_CLASS_ID]
        player_xy=transform(players,keypoints) if len(players) else None
        ball_det=sv.Detections.from_ultralytics(ball_model(frame,imgsz=640,verbose=False)[0]).with_nms(.2)
        if len(ball_det)>1: ball_det=ball_det[np.array([int(np.argmax(ball_det.confidence))])]
        ball_xy=transform(ball_det,keypoints) if len(ball_det) else None
        item={"players":[],"ball":None}
        if player_xy is not None:
            anchors=players.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
            for det_index,(xy,track_id,confidence) in enumerate(zip(player_xy,players.tracker_id,players.confidence)):
                item["players"].append({"tracker_id":int(track_id),"x":round(float(xy[0]),3),"y":round(float(xy[1]),3),"confidence":round(float(confidence),3)})
                counts[int(track_id)]+=1; anchor=anchors[det_index]
                cv2.putText(frame,f"#{int(track_id)}",(int(anchor[0])-15,int(anchor[1])-15),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,255,180),2)
        if ball_xy is not None and len(ball_xy): item["ball"]={"x":round(float(ball_xy[0][0]),3),"y":round(float(ball_xy[0][1]),3),"confidence":round(float(ball_det.confidence[0]),3)}
        frames.append(item); writer.write(frame)
        if preview is None and index>=int(fps*5): preview=frame.copy()
        index+=1
    cap.release(); writer.release()
    if preview is not None: cv2.imwrite(str(output/"preview.jpg"),preview)
    result={"fps":fps,"frames":frames,"suggested_tracker_id":counts.most_common(1)[0][0] if counts else -1,
            "track_visibility":dict(counts),"coordinate_system":"metres_120x70","accuracy":"estimated"}
    Path(tracks).write_text(json.dumps(result,ensure_ascii=False),encoding="utf-8")

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--input",required=True); parser.add_argument("--output",required=True); parser.add_argument("--tracks",required=True); parser.add_argument("--device",default=os.getenv("DEVICE","cuda")); args=parser.parse_args()
    main(args.input,args.output,args.tracks,args.device)
