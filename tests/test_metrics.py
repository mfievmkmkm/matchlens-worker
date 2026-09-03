from matchlens.metrics import calculate_player_metrics
from matchlens.radar import radar_svg


def frames():
    return [
      {"players":[{"tracker_id":7,"x":10+i,"y":20,"confidence":.9}],"ball":{"x":10+i,"y":20.5,"confidence":.9}}
      for i in range(20)]

def test_metrics_use_visible_coordinates():
    result=calculate_player_metrics(frames(),7,10)
    assert result["distance_m"] == 19
    assert result["coverage_percent"] == 100
    assert result["touches_observed"] == 1
    assert result["confidence"] == "estimated"

def test_radar_is_svg_and_contains_player():
    result=radar_svg(frames(),7)
    assert result.startswith("<svg")
    assert "PLAYER 7" in result

def test_cpu_pixel_tracking_never_claims_metres_or_speed():
    result=calculate_player_metrics(frames(),7,10,coordinate_system="image_pixels")
    assert result["distance_m"] is None
    assert result["max_speed_kmh"] is None
    assert result["confidence"] == "tracking_only"
