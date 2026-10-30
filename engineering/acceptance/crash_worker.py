import sys,os,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'backend/src'),str(root/'data-management')]
from onlinecoc.host import Host
from onlinecoc_data import FileDataStore

def main():
    kind,path,stage,*extra=sys.argv[1:]
    def fault(point):
        if point==stage:os._exit(70)
    if kind=='store':
        with FileDataStore(path,fault=fault) as store:store.commit(store.generation,{'n':2})
    else:
        host=Host(path,fault=fault)
        message=json.loads(Path(extra[0]).read_text());message['payload']['authorityEpoch']=host.epoch;Path(extra[0]).write_text(json.dumps(message));host.command('player1',message)
if __name__=='__main__':main()
