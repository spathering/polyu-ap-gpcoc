"""Acceptance-only host launcher: deny outbound non-loopback networking in Python."""
import sys,ipaddress,socket
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'backend/src'),str(root/'data-management')]
def local(address):
    if address in ('localhost',b'localhost',None):return True
    try:return ipaddress.ip_address(address).is_loopback
    except ValueError:return False

def network_guard(event,args):
    if event in ('socket.connect','socket.sendto'):
        address=args[-1]
        if isinstance(address,tuple) and not local(address[0]):raise PermissionError('WAN denied by acceptance guard')
    elif event=='socket.getaddrinfo' and not local(args[0]):raise PermissionError('WAN DNS denied by acceptance guard')
sys.addaudithook(network_guard)
if __name__=='__main__':
    with socket.socket() as probe:
        try:probe.connect(('1.1.1.1',443))
        except PermissionError:pass
        else:raise AssertionError('WAN guard is not active')
    from onlinecoc.cli import main
    main()
