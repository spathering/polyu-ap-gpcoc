class DomainError(Exception):
    def __init__(self, code, detail=""):
        self.code,self.detail=code,detail
        super().__init__(code)

def require(condition, code="INPUT_INVALID"):
    if not condition: raise DomainError(code)
