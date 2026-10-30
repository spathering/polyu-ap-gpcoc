import hashlib,secrets,time
from pwdlib import PasswordHash
from onlinecoc_data import FileDataStore
from .errors import require,DomainError

class Identity:
    def __init__(self,path,store_factory=FileDataStore):
        self.store=store_factory(path);self.hasher=PasswordHash.recommended()
        if self.store.snapshot()[1] is None:self.store.commit(0,{"accounts":{},"sessions":{}})
    def create(self,login,password):
        require(1<=len(login)<=80 and len(password)>=8)
        g,s=self.store.snapshot();require(login not in s["accounts"],"ACCOUNT_EXISTS")
        s["accounts"][login]={"accountId":login,"loginName":login,"nickname":login,"passwordHash":self.hasher.hash(password),"disabled":False}
        self.store.commit(g,s)
    def login(self,login,password):
        g,s=self.store.snapshot();a=s["accounts"].get(login)
        require(a and not a["disabled"],"AUTH_FAILED")
        try:ok=self.hasher.verify(password,a["passwordHash"])
        except Exception:ok=False
        require(ok,"AUTH_FAILED")
        token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
        s["sessions"][hashlib.sha256(token.encode()).hexdigest()]={"accountId":login,"expires":time.time()+86400,"csrf":csrf}
        self.store.commit(g,s);return token,csrf
    def authenticate(self,token):
        s=self.store.snapshot()[1];session=s["sessions"].get(hashlib.sha256(token.encode()).hexdigest())
        require(session and session["expires"]>time.time(),"AUTH_REQUIRED")
        require(not s["accounts"][session["accountId"]]["disabled"],"AUTH_REQUIRED")
        return session
    def logout(self,token):
        g,s=self.store.snapshot();s["sessions"].pop(hashlib.sha256(token.encode()).hexdigest(),None);self.store.commit(g,s)
    def password(self,account,password):
        require(len(password)>=8);g,s=self.store.snapshot();require(account in s["accounts"])
        s["accounts"][account]["passwordHash"]=self.hasher.hash(password)
        s["sessions"]={k:v for k,v in s["sessions"].items() if v["accountId"]!=account};self.store.commit(g,s)
    def close(self):self.store.close()
