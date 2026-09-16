"""Detector con YOLO (ultralytics). Reconoce la clase 'cat' de COCO.

En Raspberry Pi conviene exportar el modelo a NCNN una vez:
    yolo export model=yolov8n.pt format=ncnn imgsz=320
y luego apuntar detector.model a 'yolov8n_ncnn_model'.
"""
from __future__ import annotations

import numpy as np

from .base import Detection


class YoloDetector:
    def __init__(self, model: str = "yolov8n.pt", confidence: float = 0.45, imgsz: int = 320,
                 classes: list[str] | None = None):
        try:
            from ultralytics import YOLO  # type: ignore
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise RuntimeError(
                "Falta 'ultralytics'. Instalar con: pip install 'fuera-gatos[yolo]'"
            ) from exc
        self._model = YOLO(model)
        self.confidence = float(confidence)
        self.imgsz = int(imgsz)
        self._names = self._model.names
        self._class_ids = None
        if classes:
            wanted = set(classes)
            self._class_ids = [i for i, n in self._names.items() if n in wanted]

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self._model.predict(
            frame,
            conf=self.confidence,
            imgsz=self.imgsz,
            classes=self._class_ids,
            verbose=False,
        )
        dets: list[Detection] = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
                dets.append(Detection(str(self._names[cls]), round(conf, 3), (x1, y1, x2, y2)))
        return dets
