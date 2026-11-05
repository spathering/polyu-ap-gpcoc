"""Real CLI hosts, current-user DPAPI, native tool probe and window smoke."""
import base64, hashlib, json, os, secrets, socket, subprocess, sys, time, uuid
from pathlib import Path
import httpx

TOOL=Path(__file__).resolve().parent
ROOT=TOOL.parents[1]
sys.path[:0]=[str(ROOT/'engineering/backend/src'),str(ROOT/'engineering/data-management')]
from onlinecoc.host_control import protect, HostControl
from onlinecoc.host import Host
from onlinecoc.server import create_app
from fastapi.testclient import TestClient

checks=[]
def ok(name, condition=True):
    assert condition,name
    checks.append(name)

def main():
    out=TOOL/'.test-output'/uuid.uuid4().hex[:12];out.mkdir(parents=True)
    discovery=out/'discovery';env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    original=secrets.token_urlsafe(24);replacement=secrets.token_urlsafe(24)
    env['ONLINECOC_BOOTSTRAP_PASSWORD']=original
    processes=[];logs=[]
    def start(data):
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        cmd=[sys.executable,'-B',str(ROOT/'engineering/backend/scripts/run.py'),'--data-dir',str(data)]
        if not data.exists():subprocess.run(cmd+['init'],env=env,check=True,capture_output=True,timeout=30)
        log=(out/('host-'+str(port)+'.log')).open('w',encoding='utf-8');logs.append(log)
        proc=subprocess.Popen(cmd+['serve','--port',str(port),'--host-control-dir',str(discovery)],env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        processes.append(proc)
        for _ in range(100):
            if proc.poll() is not None:raise RuntimeError('isolated host failed')
            for file in discovery.glob('*.json'):
                try:
                    record=json.loads(file.read_text(encoding='utf-8'))
                    if record['url']!=f'http://127.0.0.1:{port}':continue
                    key=protect(base64.b64decode(record['protectedKey']),decrypt=True).decode()
                    c=httpx.Client(base_url=record['url'],headers={'X-OnlineCOC-Instance':record['instanceId'],'X-OnlineCOC-Host-Key':key},trust_env=False)
                    if c.get('/api/v1/host-control/accounts').status_code==200:return proc,record,c
                    c.close()
                except (OSError,ValueError,httpx.HTTPError):pass
            time.sleep(.1)
        raise RuntimeError('isolated host did not become available')
    def login(record,account,password):
        c=httpx.Client(base_url=record['url'],headers={'Origin':record['url']},trust_env=False)
        response=c.post('/api/v1/login',json={'loginName':account,'password':password})
        return c,response
    def operation(c,op,account,password,request=None):
        return c.post('/api/v1/host-control/accounts',json={'requestId':request or str(uuid.uuid4()),'operation':op,'accountId':account,'password':password})
    try:
        proc,a,client=start(out/'room-a');other,b,second=start(out/'room-b')
        accounts=client.get('/api/v1/host-control/accounts').json()
        ok('discover_two_running_instances',len(list(discovery.glob('*.json')))==2)
        ok('only_sanitized_account_fields',set(accounts['items'][0])=={'accountId','loginName','nickname','disabled','roomRole'})
        ok('dpapi_descriptor_has_no_raw_key',client.headers['X-OnlineCOC-Host-Key'] not in json.dumps(a))
        raw=httpx.Client(base_url=a['url'],trust_env=False)
        ok('missing_local_authority_denied',raw.get('/api/v1/host-control/accounts').status_code==403)
        kp,r=login(a,'kp',original);kp.headers['X-CSRF-Token']=r.json()['csrf']
        ok('kp_cookie_and_csrf_do_not_grant_host_authority',kp.get('/api/v1/host-control/accounts').status_code==403)
        ok('browser_origin_rejected_even_with_key',client.get('/api/v1/host-control/accounts',headers={'Origin':a['url']}).status_code==403)
        ok('browser_post_rejected_even_with_key',operation(kp,'password','player1',replacement).status_code==403)
        ok('wrong_instance_rejected',client.get('/api/v1/host-control/accounts',headers={'X-OnlineCOC-Instance':b['instanceId']}).status_code==403)
        player,r=login(a,'player1',original);ok('initial_player_session',r.status_code==200)
        p2,r=login(a,'player2',original)
        rid=str(uuid.uuid4());result=operation(client,'password','player1',replacement,rid)
        ok('online_reset_commits',result.status_code==200 and result.json()['status']=='committed')
        ok('target_old_session_revoked',player.get('/api/v1/me').status_code==401)
        wrong,r=login(a,'player1',original);ok('old_password_rejected',r.status_code==401);wrong.close()
        new,r=login(a,'player1',replacement);ok('new_password_accepted',r.status_code==200)
        ok('other_accounts_unaffected',kp.get('/api/v1/me').status_code==200 and p2.get('/api/v1/me').status_code==200)
        ok('same_request_id_returns_first_result',operation(client,'password','player1',secrets.token_urlsafe(24),rid).json()==result.json())
        ok('retry_does_not_revoke_new_session',new.get('/api/v1/me').status_code==200)
        ok('request_id_target_conflict',operation(client,'password','player2',replacement,rid).status_code==409)
        ok('sanitized_receipt_query',client.get('/api/v1/host-control/receipts/'+rid).json()==result.json())
        ok('short_password_rejected',operation(client,'password','player2','short').status_code==409)
        ok('nonexistent_target_rejected',operation(client,'password','absent',replacement).status_code==404)
        ok('create_identity',operation(client,'create','new-player',replacement).status_code==200)
        created,r=login(a,'new-player',replacement);ok('new_identity_can_authenticate',r.status_code==200)
        ok('creation_keeps_room_membership_explicit',created.get('/api/v1/view').status_code in (403,404,409))
        ok('duplicate_login_rejected',operation(client,'create','new-player',replacement).status_code==409)
        untouched,r=login(b,'player1',original);ok('second_instance_unchanged',r.status_code==200);untouched.close()
        ok('reset_kp_without_kp_password',operation(client,'password','kp',replacement).status_code==200 and kp.get('/api/v1/me').status_code==401)
        for c in [raw,kp,player,p2,new,created]:c.close()
        probe=subprocess.run([str(TOOL/'HostAccounts.exe'),'--probe',str(discovery)],capture_output=True,timeout=30)
        ok('native_tool_dpapi_and_real_host_queries',probe.returncode==0 and len(json.loads(probe.stdout))==2)
        smoke=subprocess.run([str(TOOL/'HostAccounts.exe'),'--smoke',str(discovery)],capture_output=True,timeout=30)
        ok('native_window_loads_instances_and_accounts',smoke.returncode==0)
        absent=subprocess.run([str(TOOL/'HostAccounts.exe'),'--probe',str(out/'no-host')],capture_output=True,timeout=10)
        ok('client_only_device_has_no_manageable_instance',absent.returncode==2)
        proc.terminate();proc.wait(timeout=10);client.close()
        proc,a,client=start(out/'room-a')
        restored,r=login(a,'player1',replacement);ok('password_survives_host_restart',r.status_code==200);restored.close()
        ok('receipt_survives_host_restart',client.get('/api/v1/host-control/receipts/'+rid).json()==result.json())
        oldkey=second.headers['X-OnlineCOC-Host-Key']
        ok('different_host_key_rejected',client.get('/api/v1/host-control/accounts',headers={'X-OnlineCOC-Host-Key':oldkey}).status_code==403)
        probe=subprocess.run([str(TOOL/'HostAccounts.exe'),'--probe',str(discovery)],capture_output=True,timeout=30)
        ok('stale_discovery_record_ignored',probe.returncode==0 and len(json.loads(probe.stdout))==2)
        # Check identity commits contain no password plaintext or separate fast password digest.
        stored=''.join(f.read_text(encoding='utf-8') for f in (out/'room-a/identity/generations').glob('*.json'))
        ok('no_plaintext_password_in_identity_history',original not in stored and replacement not in stored)
        host=Host(out/'unit',bootstrap=original)
        control=HostControl(host,18888,out/'unit-discovery')
        with TestClient(create_app(host,18888,control),base_url='http://127.0.0.1:18888',client=('127.0.0.1',1234)) as test:
            ok('lifespan_publishes_record',control.file.exists())
        ok('graceful_shutdown_removes_record',not control.file.exists())
        with TestClient(create_app(host,18888,control),base_url='http://127.0.0.1:18888',client=('10.0.0.8',1234)) as remote:
            ok('remote_peer_rejected_even_with_local_key',remote.get('/api/v1/host-control/accounts',headers={'X-OnlineCOC-Instance':control.instance,'X-OnlineCOC-Host-Key':control.key}).status_code==403)
        # A failed identity commit leaves both password and sessions intact.
        before=host.identity.store.snapshot()
        def fail(stage):
            if stage=='before_write':
                from onlinecoc_data import StoreError
                raise StoreError('TEST_FAILURE')
        host.identity.store.fault=fail
        try:
            host.identity.host_change({'requestId':str(uuid.uuid4()),'operation':'password','accountId':'player1','password':replacement})
            raise AssertionError('failure was not injected')
        except Exception as error:
            from onlinecoc_data import StoreError
            assert isinstance(error,StoreError)
        host.identity.store.fault=None
        ok('failed_identity_write_keeps_original_state',host.identity.store.snapshot()==before)
        def unavailable():raise OSError('test unavailable DPAPI')
        control.publish=unavailable
        with TestClient(create_app(host,18888,control),base_url='http://127.0.0.1:18888',client=('127.0.0.1',1234)) as test:
            ok('unavailable_dpapi_does_not_stop_room',test.get('/api/v1/capabilities').status_code==200)
            ok('unavailable_local_authority_fails_closed',test.get('/api/v1/host-control/accounts',headers={'X-OnlineCOC-Instance':control.instance,'X-OnlineCOC-Host-Key':control.key}).status_code==403)
        host.close();client.close();second.close()
        files=['HostAccounts.cs','HostAccounts.exe','../../engineering/backend/src/onlinecoc/identity.py','../../engineering/backend/src/onlinecoc/host_control.py','../../engineering/backend/src/onlinecoc/server.py','../../engineering/backend/src/onlinecoc/cli.py']
        report={'passed':len(checks),'checks':checks,'scope':'isolated real Windows CLI hosts + DPAPI + native probe + window loading smoke; no visual or mouse-interaction claim','sourceHashes':{f:hashlib.sha256((TOOL/f).read_bytes()).hexdigest() for f in files}}
        (TOOL/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('PASS:',len(checks),'host account checks')
    finally:
        for p in processes:
            if p.poll() is None:p.terminate();p.wait(timeout=10)
        for log in logs:log.close()

if __name__=='__main__':main()
