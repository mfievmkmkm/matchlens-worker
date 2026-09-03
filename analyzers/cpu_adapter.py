"""Low-cost preview tracker for short clips; never converts image pixels into metres."""
import argparse, json
from collections import Counter
from pathlib import Path
import cv2
from ultralytics import YOLO

def main(source,output,tracks):
    out=Path(output); out.mkdir(parents=True,exist_ok=True); model=YOLO("yolo11n.pt")
    cap=cv2.VideoCapture(source); fps=cap.get(cv2.CAP_PROP_FPS) or 25.; frames=[]; counts=Counter(); preview=None
    for result in model.track(source=source,stream=True,persist=True,classes=[0,32],conf=.3,imgsz=640,vid_stride=2,verbose=False):
        frame=result.orig_img; item={"players":[],"ball":None}
        if result.boxes is not None and result.boxes.id is not None:
            for box,tid,cls,conf in zip(result.boxes.xyxy.cpu().tolist(),result.boxes.id.int().cpu().tolist(),result.boxes.cls.int().cpu().tolist(),result.boxes.conf.cpu().tolist()):
                x1,y1,x2,y2=box
                if cls==0:
                    item["players"].append({"tracker_id":tid,"x":(x1+x2)/2,"y":y2,"confidence":conf}); counts[tid]+=1
                    cv2.putText(frame,f"#{tid}",(int(x1),max(25,int(y1)-8)),cv2.FONT_HERSHEY_SIMPLEX,.75,(0,255,170),2)
                elif cls==32: item["ball"]={"x":(x1+x2)/2,"y":(y1+y2)/2,"confidence":conf}
        frames.append(item)
        if preview is None and len(frames)>max(5,int(fps)): preview=frame.copy()
    cap.release()
    if preview is not None: cv2.imwrite(str(out/"preview.jpg"),preview)
    Path(tracks).write_text(json.dumps({"fps":fps/2,"frames":frames,"track_visibility":dict(counts),
      "coordinate_system":"image_pixels","accuracy":"tracking_only"}),encoding="utf-8")

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output",required=True); p.add_argument("--tracks",required=True); a=p.parse_args(); main(a.input,a.output,a.tracks)
