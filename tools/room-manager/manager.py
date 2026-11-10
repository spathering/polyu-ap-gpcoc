"""Source and PyInstaller entry. Network module is an independent package."""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if not getattr(sys, 'frozen', False):
    sys.path[:0] = [str(ROOT / 'python'), str(ROOT.parents[1] / 'engineering/network-lan/src')]

def main():
    import tkinter as tk
    from room_manager.gui import Manager
    from room_manager.state import Settings
    parser = argparse.ArgumentParser()
    parser.add_argument('--settings-dir', default=str(Path(os.getenv('LOCALAPPDATA', str(Path.home()))) / 'OnlineCOC/RoomManager'))
    parser.add_argument('--lan', action='store_true')
    args = parser.parse_args()
    if args.lan:
        from onlinecoc_lan.gui import main as lan
        return lan()
    root = tk.Tk()
    Manager(root, Settings(args.settings_dir))
    root.mainloop()

if __name__ == '__main__':
    main()
