"""Interfaz de línea de comandos."""
from __future__ import annotations

import argparse
import logging
import sys
import time

from . import __version__
from .config import ConfigError, load_config


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_run(args) -> int:
    from .pipeline import run

    cfg = load_config(args.config)
    return run(cfg, simulate=args.simulate, max_frames=args.max_frames)


def cmd_simulate(args) -> int:
    from .simulate import run_simulation

    cfg = load_config(args.config)
    if not args.verbose:
        logging.getLogger("fuera_gatos.deterrents").setLevel(logging.WARNING)
    print("Simulación con reloj acelerado (sin cámara ni GPIO)\n")
    events = run_simulation(cfg, start_hour=args.hour)
    activations = [e for e in events if e.kind == "activated"]
    print(f"\nResumen: {len(activations)} activaciones, "
          f"{sum(1 for e in events if e.kind == 'suppressed')} supresiones")
    return 0


def cmd_test_deterrents(args) -> int:
    from .deterrents import build_deterrents

    cfg = load_config(args.config)
    names = args.names or list(cfg.deterrents)
    dets = build_deterrents({n: cfg.deterrents[n] for n in names if n in cfg.deterrents},
                            simulate=args.simulate)
    for name, d in dets.items():
        print(f"Probando '{name}' durante {args.seconds} s...")
        d.start(args.seconds)
        time.sleep(args.seconds + 0.2)
        d.stop()
        d.close()
    print("Listo.")
    return 0


def cmd_check(args) -> int:
    """Muestra qué componentes opcionales están disponibles en este equipo."""
    checks = {
        "numpy": "numpy",
        "OpenCV (cámara USB/RTSP, capturas JPG)": "cv2",
        "ultralytics (YOLO)": "ultralytics",
        "picamera2 (cámara Pi)": "picamera2",
        "gpiozero (relés)": "gpiozero",
    }
    for label, mod in checks.items():
        try:
            __import__(mod)
            print(f"  [ok]    {label}")
        except Exception:
            print(f"  [falta] {label}")
    if args.config:
        try:
            cfg = load_config(args.config)
            print(f"  [ok]    configuración válida: {args.config} "
                  f"({len(cfg.zones)} zonas, {len(cfg.deterrents)} disuasores, "
                  f"{len(cfg.controller.escalation)} niveles)")
        except ConfigError as exc:
            print(f"  [error] configuración: {exc}")
            return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="fuera-gatos",
                                description="Detecta gatos y los ahuyenta sin dañarlos.")
    p.add_argument("--version", action="version", version=f"fuera-gatos {__version__}")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("run", help="Ejecutar el sistema con cámara y disuasores")
    s.add_argument("-c", "--config", default="config.yaml")
    s.add_argument("--simulate", action="store_true", help="No tocar GPIO ni sonido; solo registrar")
    s.add_argument("--max-frames", type=int, default=None, help=argparse.SUPPRESS)
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("simulate", help="Simular un guion de visitas con reloj acelerado")
    s.add_argument("-c", "--config", default="config.example.yaml")
    s.add_argument("--hour", type=int, default=15, help="Hora del día simulada (0-23)")
    s.set_defaults(func=cmd_simulate)

    s = sub.add_parser("test-deterrents", help="Activar cada disuasor unos segundos para probar el cableado")
    s.add_argument("-c", "--config", default="config.yaml")
    s.add_argument("--seconds", type=float, default=1.0)
    s.add_argument("--simulate", action="store_true")
    s.add_argument("names", nargs="*")
    s.set_defaults(func=cmd_test_deterrents)

    s = sub.add_parser("check", help="Verificar dependencias opcionales y configuración")
    s.add_argument("-c", "--config", default=None)
    s.set_defaults(func=cmd_check)

    args = p.parse_args(argv)
    _setup_logging(args.verbose)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"Error de configuración: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
