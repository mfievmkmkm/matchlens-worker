import json
from pathlib import Path

from .metrics import calculate_player_metrics
from .radar import radar_svg


def build_report(job_dir:Path,result:dict,tracker_id:int):
    frames=result["frames"]; metrics=calculate_player_metrics(frames,tracker_id,float(result["fps"]),coordinate_system=result.get("coordinate_system","unknown"))
    svg=radar_svg(frames,tracker_id); (job_dir/"radar.svg").write_text(svg,encoding="utf-8")
    (job_dir/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
    accuracy="Высокая" if metrics["coverage_percent"]>=75 else "Средняя" if metrics["coverage_percent"]>=40 else "Ограниченная"
    html=f'''<!doctype html><html lang="ru"><meta charset="utf-8"><title>MatchLens</title>
<style>body{{font:18px Arial;background:#07150d;color:#fff;max-width:900px;margin:40px auto}}.card{{background:#11281a;padding:24px;border-radius:20px;margin:18px 0}}b{{color:#b6ff00}}</style>
<h1>⚽ MatchLens · игрок #{tracker_id}</h1><div class="card"><b>Достоверность: {accuracy}</b><p>Видимость игрока: {metrics['coverage_percent']}%</p></div>
<div class="card"><h2>Цифры</h2><p>≈ Дистанция в кадре: <b>{str(metrics['distance_m'])+' м' if metrics['distance_m'] is not None else 'не измерена'}</b></p><p>≈ Максимальная скорость: <b>{str(metrics['max_speed_kmh'])+' км/ч' if metrics['max_speed_kmh'] is not None else 'не измерена'}</b></p><p>✅ Наблюдаемые касания: <b>{metrics['touches_observed']}</b></p></div>
<div class="card"><h2>Карта движения</h2>{svg}</div>
<div class="card"><h2>Что важно</h2><p>Метрики не достраиваются в моменты, когда игрок или мяч отсутствуют в кадре. Это видеоаналитика, а не официальная GPS-статистика.</p></div></html>'''
    (job_dir/"report.html").write_text(html,encoding="utf-8")
    return metrics
