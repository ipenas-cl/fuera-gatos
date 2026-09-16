from fuera_gatos.config import ZoneConfig
from fuera_gatos.detection.base import Detection
from fuera_gatos.zones import assign_zones, point_in_polygon

SQUARE = [(0, 0), (10, 0), (10, 10), (0, 10)]


def test_point_in_polygon():
    assert point_in_polygon(5, 5, SQUARE)
    assert not point_in_polygon(15, 5, SQUARE)
    assert not point_in_polygon(-1, 5, SQUARE)
    tri = [(0, 0), (10, 0), (0, 10)]
    assert point_in_polygon(2, 2, tri)
    assert not point_in_polygon(8, 8, tri)


def test_assign_zones_uses_feet_anchor():
    zones = [ZoneConfig("basura", [(0, 200), (300, 200), (300, 480), (0, 480)])]
    inside = Detection("cat", 0.9, (100, 100, 180, 250))  # cabeza fuera, patas dentro
    outside = Detection("cat", 0.9, (100, 100, 180, 190))
    kept = assign_zones([inside, outside], zones)
    assert kept == [inside]
    assert inside.zone == "basura"


def test_no_zones_means_whole_frame():
    d = Detection("cat", 0.9, (0, 0, 10, 10))
    kept = assign_zones([d], [])
    assert kept == [d] and d.zone == "todo"
