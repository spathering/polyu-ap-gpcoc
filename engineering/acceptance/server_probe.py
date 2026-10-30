import faulthandler,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'backend/src'),str(root/'data-management')]
if __name__=='__main__':
    faulthandler.dump_traceback_later(15,repeat=True)
    from onlinecoc.cli import main
    main()
