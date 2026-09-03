from html import escape


def radar_svg(frames:list[dict],tracker_id:int,width=1050,height=680):
    points=[]
    for frame in frames:
        player=next((p for p in frame.get("players",[]) if p.get("tracker_id")==tracker_id and p.get("confidence",0)>=.55),None)
        if player: points.append((float(player["x"])*10,float(player["y"])*10))
    circles="".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#b6ff00" fill-opacity=".22"/>' for x,y in points[::max(1,len(points)//600)])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1050 680" width="{width}" height="{height}">
<rect width="1050" height="680" rx="22" fill="#102e1c"/><rect x="10" y="10" width="1030" height="660" fill="none" stroke="white" stroke-width="4"/>
<line x1="525" y1="10" x2="525" y2="670" stroke="white" stroke-width="3"/><circle cx="525" cy="340" r="91.5" fill="none" stroke="white" stroke-width="3"/>
<rect x="10" y="138" width="165" height="404" fill="none" stroke="white" stroke-width="3"/><rect x="875" y="138" width="165" height="404" fill="none" stroke="white" stroke-width="3"/>
{circles}<text x="35" y="55" fill="white" font-family="Arial" font-size="28" font-weight="700">MATCHLENS · PLAYER {tracker_id}</text></svg>'''
