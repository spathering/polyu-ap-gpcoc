import argparse
import time
from .gateway import Config, Gateway

def main():
    parser = argparse.ArgumentParser(description='独立 LAN HTTP/WebSocket 网关')
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('--upstream', default='http://127.0.0.1:8765')
    parser.add_argument('--bind', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8877)
    args = parser.parse_args()
    if args.gui:
        from .gui import main as gui
        return gui()
    gateway = Gateway(Config(args.upstream, args.bind, args.port))
    try:
        gateway.start()
        print('LAN ready:', gateway.config.url, flush=True)
        while gateway.running:
            time.sleep(.5)
    except KeyboardInterrupt:
        pass
    finally:
        gateway.stop()

if __name__ == '__main__':
    main()
