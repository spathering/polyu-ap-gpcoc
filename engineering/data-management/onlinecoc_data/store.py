"""Framework-free, single-writer JSON snapshot store. No business algorithms."""
import copy
import hashlib
import json
import os
import threading
import uuid
from pathlib import Path

class StoreError(Exception):
    pass

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def digest(data):
    return hashlib.sha256(data).hexdigest()

class FileDataStore:
    FORMAT = 1
    def __init__(self, directory, *, max_bytes=512*1024*1024, fault=None):
        self.path = Path(directory)
        self.path.mkdir(parents=True, exist_ok=True)
        self.generations = self.path / "generations"
        self.generations.mkdir(exist_ok=True)
        self.staging = self.path / "staging"
        self.staging.mkdir(exist_ok=True)
        self.max_bytes, self.fault = max_bytes, fault
        self.mutex = threading.RLock()
        self.lock = open(self.path / "writer.lock", "a+b")
        self.lock.seek(0)
        if (self.path / "writer.lock").stat().st_size == 0:
            self.lock.write(b"0"); self.lock.flush()
        self.lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            self.lock.close()
            raise StoreError("STORE_LOCKED") from e
        self.generation, self.head, self.value = 0, None, None
        self.closed = False
        try:
            for file in sorted(self.generations.glob("*.json")):
                raw = file.read_bytes()
                env = json.loads(raw)
                if (env.get("format") != self.FORMAT or env.get("generation") != self.generation+1
                    or file.name != f"{self.generation+1:012d}.json"
                    or env.get("parent") != self.head
                    or env.get("digest") != digest(canonical(env.get("payload")))
                    or env.get("length") != len(canonical(env.get("payload")))):
                    raise StoreError("STORE_CORRUPT")
                self.generation += 1
                self.head, self.value = digest(raw), env["payload"]
        except Exception as e:
            self.close()
            raise StoreError("STORE_CORRUPT_OR_UNSUPPORTED") from e

    def _fault(self, stage):
        if self.fault: self.fault(stage)

    def snapshot(self):
        with self.mutex:
            if self.closed: raise StoreError("STORE_CLOSED")
            return self.generation, copy.deepcopy(self.value)

    def commit(self, expected_generation, value):
        with self.mutex:
            if self.closed: raise StoreError("STORE_CLOSED")
            if expected_generation != self.generation: raise StoreError("VERSION_CONFLICT")
            data = canonical(value)
            env = {"format":self.FORMAT,"generation":self.generation+1,"parent":self.head,
                   "digest":digest(data),"length":len(data),"payload":value}
            raw = canonical(env)
            used = sum(p.stat().st_size for p in self.generations.glob("*.json"))
            if used + len(raw)*2 > self.max_bytes: raise StoreError("STORE_FULL")
            tmp = self.staging / (uuid.uuid4().hex + ".tmp")
            self._fault("before_write")
            try:
                with open(tmp,"xb") as f:
                    f.write(raw[:len(raw)//2]); self._fault("half_write")
                    f.write(raw[len(raw)//2:]); f.flush(); self._fault("before_sync")
                    os.fsync(f.fileno()); self._fault("before_publish")
                target = self.generations / f"{self.generation+1:012d}.json"
                if target.exists(): raise StoreError("GENERATION_EXISTS")
                os.replace(tmp,target)
                # Publication is visible. Preserve in-memory consistency even if the caller loses its reply.
                self.generation += 1
                self.head, self.value = digest(raw), copy.deepcopy(value)
                if os.name != "nt":
                    fd=os.open(self.generations,os.O_RDONLY)
                    try: os.fsync(fd)
                    finally: os.close(fd)
                self._fault("after_publish")
                return self.generation
            finally:
                if tmp.exists(): tmp.unlink()

    def query(self, collection, **equals):
        _, state=self.snapshot()
        values=(state or {}).get(collection,{})
        if not isinstance(values,dict): raise StoreError("INVALID_COLLECTION")
        return [copy.deepcopy(v) for v in values.values() if all(v.get(k)==x for k,x in equals.items())]

    def get_receipt(self, account, command):
        return (self.snapshot()[1] or {}).get("commands",{}).get(account+":"+command)

    def export_snapshot(self, target):
        with self.mutex:
            generation,payload=self.snapshot()
            env={"format":1,"sourceGeneration":generation,"payload":payload,"digest":digest(canonical(payload))}
            path=Path(target)
            with open(path,"xb") as f:
                f.write(canonical(env)); f.flush(); os.fsync(f.fileno())

    @classmethod
    def restore(cls, bundle, directory):
        env=json.loads(Path(bundle).read_bytes())
        if env.get("format")!=1 or env.get("digest")!=digest(canonical(env.get("payload"))):
            raise StoreError("BACKUP_INVALID")
        path=Path(directory)
        if path.exists(): raise StoreError("RESTORE_TARGET_EXISTS")
        with cls(path) as store: store.commit(0,env["payload"])

    def inspect(self):
        return {"format":1,"generation":self.generation,"bytes":sum(p.stat().st_size for p in self.generations.glob("*.json"))}

    def close(self):
        if getattr(self,"closed",False): return
        self.closed=True
        if not self.lock.closed:
            self.lock.seek(0)
            if os.name=="nt":
                import msvcrt
                msvcrt.locking(self.lock.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.lock.fileno(),fcntl.LOCK_UN)
            self.lock.close()
    def __enter__(self): return self
    def __exit__(self,*args): self.close()

class MemoryDataStore:
    """Contract test implementation; deliberately not a durable production store."""
    def __init__(self,directory=None): self.generation,self.value=0,None
    def snapshot(self): return self.generation,copy.deepcopy(self.value)
    def commit(self,expected_generation,value):
        if expected_generation!=self.generation: raise StoreError("VERSION_CONFLICT")
        canonical(value)
        self.generation+=1; self.value=copy.deepcopy(value); return self.generation

    query = FileDataStore.query
    get_receipt = FileDataStore.get_receipt
    def close(self): pass
