import argparse
import json
import os
import sys
from pathlib import Path
from .platform_driver import make_driver
from .engine import Engine
from .planner import OllamaPlanner
from .server import serve


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="OpenClerk local desktop computer-use runner")
    parser.add_argument("command", choices=["serve", "doctor", "permissions", "demo", "apps"], nargs="?", default="serve")
    parser.add_argument("--port", type=int, default=8768)
    parser.add_argument("--bridge", default=str(root / "build" / "desktop-bridge"))
    parser.add_argument("--allow-app", action="append", default=[])
    args = parser.parse_args()
    if args.command == "demo":
        from .demo import main as demo
        demo(); return
    driver = make_driver(sys.platform, args.bridge)
    if args.command == "apps":
        print(json.dumps(driver.apps(), indent=2)); driver.close(); return
    if args.command == "doctor":
        print(json.dumps(driver.doctor(), indent=2)); driver.close(); return
    if args.command == "permissions":
        if sys.platform != "darwin":
            print("Use your OS desktop session permissions. Linux requires X11; Windows cannot control elevated apps."); return
        print(json.dumps(driver.call({"command": "permissions"}), indent=2)); driver.close(); return
    allowed = args.allow_app or (["io.openclerk.clinicdemo"] if sys.platform == "darwin" else [os.path.normcase(os.path.realpath(sys.executable))])
    engine = Engine(driver, OllamaPlanner(), allowed, root / ".runtime" / "events.jsonl")
    try: serve(engine, args.port)
    finally: driver.close()


if __name__ == "__main__":
    main()
