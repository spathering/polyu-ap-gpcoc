"""Create isolated real-host fixtures and run the browser acceptance suite."""
import json,os,secrets,socket,subprocess,sys,time,urllib.request,uuid
from pathlib import Path
PACK=Path(__file__).resolve().parents[1];ROOT=PACK.parents[1]
sys.path.insert(0,str(PACK/'tools'))
from client import Client
from package import install
from verify_ui import main as verify
def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def main():
    out=PACK/'tests/output'/('ui-'+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
    pw=secrets.token_urlsafe(20);secret=out/'password.txt';secret.write_text(pw,encoding='utf-8')
    env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',ONLINECOC_BOOTSTRAP_PASSWORD=pw,PYTHONIOENCODING='utf-8')
    run=[sys.executable,'-B',str(ROOT/'engineering/backend/scripts/run.py'),'--data-dir',str(out/'room')]
    hp,fp=port(),port();base='http://127.0.0.1:'+str(fp);processes=[]
    try:
        subprocess.run(run+['init'],env=env,capture_output=True,check=True,timeout=30)
        processes.append(subprocess.Popen(run+['serve','--port',str(hp)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        processes.append(subprocess.Popen([sys.executable,'-B',str(PACK/'tools/launch.py'),'--backend','http://127.0.0.1:'+str(hp),'--port',str(fp),'--data-dir',str(out/'frontend-room'),'--no-browser'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        for _ in range(100):
            try:urllib.request.urlopen(base,timeout=1);break
            except OSError:time.sleep(.1)
        k=Client(base,'kp',pw);install(k)
        a=k.command('entity.create',{'configurationId':'md.character','owner':'player1','visibility':'owner','name':'观察员'})
        k.invoke('md.profile',actor=a,constitution=3,strength=2,speed=4,observation=5,spirit=3,intellect=3)
        k.command('entity.create',{'configurationId':'md.world','owner':'kp','visibility':'public'})
        def package_post(client,path,body):
            req=urllib.request.Request(base+'/package/'+path,data=json.dumps(body).encode(),headers={'Origin':base,'Content-Type':'application/json','X-CSRF-Token':client.csrf})
            with client.opener.open(req,timeout=30) as r:return json.load(r)
        package_post(k,'automation',{'enabled':True})
        player=Client(base,'player1',pw)
        package_post(player,'action',{'id':str(uuid.uuid4()),'actor':a,'kind':'explore','destination':1})
        k.command('progress.set',{'ownerKind':'member','ownerId':'member-player1','eventKey':'md.known','value':{'locations':[{'id':'loc-basement','name':'地下室','index':22}]}})
        sys.argv=[sys.argv[0],base,str(secret)];verify()
    finally:
        for p in reversed(processes):p.terminate();p.wait(timeout=15)
        secret.unlink(missing_ok=True)
if __name__=='__main__':main()
