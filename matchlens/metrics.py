import math
from collections import Counter


def distance(a,b): return math.hypot(b[0]-a[0],b[1]-a[1])


def calculate_player_metrics(frames:list[dict],tracker_id:int,fps:float,confidence_threshold:float=.55):
    """Calculate only observable metrics from normalized pitch coordinates in metres."""
    points=[]; visible=0; touches=0; zones=Counter(); last_touch_frame=-10_000
    for frame_index,frame in enumerate(frames):
        player=next((p for p in frame.get("players",[]) if p.get("tracker_id")==tracker_id),None)
        if not player or float(player.get("confidence",0))<confidence_threshold: continue
        x,y=float(player["x"]),float(player["y"]); visible+=1; points.append((frame_index,x,y))
        zones[f"{min(5,max(0,int(x/17.5)))}:{min(3,max(0,int(y/17)))}"]+=1
        ball=frame.get("ball")
        if ball and float(ball.get("confidence",0))>=confidence_threshold and distance((x,y),(float(ball["x"]),float(ball["y"])))<=2.0:
            if frame_index-last_touch_frame>max(1,int(fps*.3)): touches+=1
            last_touch_frame=frame_index
    total_distance=0.; speeds=[]
    for previous,current in zip(points,points[1:]):
        elapsed=(current[0]-previous[0])/fps
        if elapsed<=0 or elapsed>2: continue
        moved=distance(previous[1:],current[1:]); speed=moved/elapsed
        if speed<=12.5: total_distance+=moved; speeds.append(speed)
    duration=(len(frames)/fps) if fps else 0
    return {"tracker_id":tracker_id,"confidence":"estimated","visible_seconds":round(visible/fps,1) if fps else 0,
            "coverage_percent":round(visible/len(frames)*100,1) if frames else 0,
            "distance_m":round(total_distance,1),"max_speed_kmh":round(max(speeds,default=0)*3.6,1),
            "touches_observed":touches,"dominant_zones":[z for z,_ in zones.most_common(3)],
            "video_duration_seconds":round(duration,1),"limitations":["Distance excludes periods outside the frame",
            "Touches are ball-proximity events, not official event data"]}
