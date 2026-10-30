import argparse,getpass,json,os
from pathlib import Path
from .host import Host
from .assets import Assets,restore_host

def main():
    parser=argparse.ArgumentParser(description='OnlineCOC file-backed first test')
    parser.add_argument('--data-dir',required=True)
    sub=parser.add_subparsers(dest='operation',required=True)
    sub.add_parser('init');serve=sub.add_parser('serve');serve.add_argument('--port',type=int,default=8765)
    backup=sub.add_parser('backup');backup.add_argument('--output',required=True);backup.add_argument('--include-identity',action='store_true')
    restore=sub.add_parser('restore');restore.add_argument('--bundle',required=True);restore.add_argument('--identity-dir')
    create=sub.add_parser('account-create');create.add_argument('account');create.add_argument('--role',choices=['kp','player'],default='player')
    sub.add_parser('collect-assets')
    password=sub.add_parser('password');password.add_argument('account')
    args=parser.parse_args()
    if args.operation=='restore':print(restore_host(args.bundle,args.data_dir,args.identity_dir));return
    password_value=None
    if args.operation=='init':password_value=os.environ.get('ONLINECOC_BOOTSTRAP_PASSWORD') or getpass.getpass('首测账号初始密码（至少 8 位）：')
    host=Host(args.data_dir,bootstrap=password_value)
    try:
        if args.operation=='init':print('已创建房间及 kp/player1/player2 账号。')
        elif args.operation=='password':host.identity.password(args.account,getpass.getpass('新密码：'))
        elif args.operation=='account-create':
            host.identity.create(args.account,getpass.getpass('账号密码：'))
            s=host.state();host.manage(s,'kp','member.add',{'accountId':args.account,'role':args.role});host.commit(s)
        elif args.operation=='collect-assets':print(Assets(host).collect_orphans('kp'))
        elif args.operation=='backup':print(Assets(host).backup('kp',args.output,args.include_identity))
        else:
            import uvicorn
            from .server import create_app
            uvicorn.run(create_app(host,args.port),host='127.0.0.1',port=args.port,log_level='warning',ws_max_size=65536)
    finally:host.close()
