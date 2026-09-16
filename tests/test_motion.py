import numpy as np

from fuera_gatos.detection.motion import MotionDetector


def make_frame(h=240, w=320, blob=None):
    f = np.full((h, w, 3), 80, dtype=np.uint8)
    if blob:
        x, y, bw, bh = blob
        f[y : y + bh, x : x + bw] = 20
    return f


def test_detects_cat_sized_blob_and_ignores_small_and_huge():
    det = MotionDetector(threshold=25, min_area=1000, max_area=20000, warmup_frames=2)
    for _ in range(4):
        det.detect(make_frame())
    assert det.detect(make_frame(blob=(100, 100, 60, 40))) != []
    det2 = MotionDetector(threshold=25, min_area=1000, max_area=20000, warmup_frames=2)
    for _ in range(4):
        det2.detect(make_frame())
    assert det2.detect(make_frame(blob=(100, 100, 8, 8))) == []
    det3 = MotionDetector(threshold=25, min_area=1000, max_area=20000, warmup_frames=2)
    for _ in range(4):
        det3.detect(make_frame())
    assert det3.detect(make_frame(blob=(10, 10, 300, 200))) == []


def test_bbox_covers_blob():
    det = MotionDetector(threshold=25, min_area=500, max_area=50000, warmup_frames=1)
    det.detect(make_frame())
    det.detect(make_frame())
    dets = det.detect(make_frame(blob=(100, 120, 60, 40)))
    assert len(dets) == 1
    x1, y1, x2, y2 = dets[0].bbox
    assert x1 <= 100 and y1 <= 120 and x2 >= 160 and y2 >= 160
    assert dets[0].label == "cat"


def test_static_scene_produces_nothing():
    det = MotionDetector(warmup_frames=1)
    for _ in range(10):
        assert det.detect(make_frame()) == []
