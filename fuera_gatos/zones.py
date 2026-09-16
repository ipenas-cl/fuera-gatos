"""Zonas de actuación: polígonos en píxeles donde el sistema sí responde."""
from __future__ import annotations

from .config import ZoneConfig
from .detection.base import Detection


def point_in_polygon(x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
    """Ray casting clásico. Los bordes cuentan como dentro de forma aproximada."""
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y):
            x_cross = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def assign_zones(detections: list[Detection], zones: list[ZoneConfig]) -> list[Detection]:
    """Devuelve solo las detecciones cuyo punto de apoyo cae en alguna zona.

    Sin zonas configuradas, todo el cuadro es zona (se etiqueta como 'todo').
    """
    if not zones:
        for d in detections:
            d.zone = "todo"
        return list(detections)
    kept = []
    for d in detections:
        x, y = d.anchor
        for z in zones:
            if point_in_polygon(x, y, z.polygon):
                d.zone = z.name
                kept.append(d)
                break
    return kept
