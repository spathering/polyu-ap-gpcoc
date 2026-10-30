import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"backend/src"),str(ROOT/"data-management")]
if __name__=="__main__":
    from onlinecoc.cli import main
    main()
