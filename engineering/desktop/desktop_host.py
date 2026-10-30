"""Desktop supervisor bridge. Only inherited stdin can request graceful shutdown."""
import argparse
import asyncio
import os
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend/src"), str(ROOT / "data-management")]

def main():
    import uvicorn
    from onlinecoc.host import Host
    from onlinecoc.server import create_app

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    # Remove the one-time bootstrap password before Lua subprocesses are spawned.
    password = os.environ.pop("ONLINECOC_BOOTSTRAP_PASSWORD", None)
    host = Host(args.data_dir, bootstrap=password)
    password = None
    server = uvicorn.Server(uvicorn.Config(create_app(host, args.port), host="127.0.0.1",
                                           port=args.port, log_level="warning", ws_max_size=65536))
    def read_control():
        sys.stdin.readline()  # explicit stop or EOF when supervisor exits
        server.should_exit = True
    threading.Thread(target=read_control, daemon=True).start()

    async def serve():
        async def ready():
            while not server.started and not server.should_exit:
                await asyncio.sleep(0.05)
            if server.started:
                print("ONLINECOC_READY", flush=True)
        notifier = asyncio.create_task(ready())
        try:
            await server.serve()
        finally:
            notifier.cancel()
            try:
                await notifier
            except asyncio.CancelledError:
                pass
    try:
        asyncio.run(serve())
    finally:
        host.close()

if __name__ == "__main__":
    main()
