from typing import Protocol

class ApplicationGateway(Protocol):
    def command(self, account: str, message: dict) -> dict: ...
    def project(self, account: str) -> dict: ...
    def receipt(self, account: str, command_id: str) -> dict: ...

    def chat_members(self, account: str) -> list: ...
    def chat_history(self, account: str, channel_id: str, before=None, limit=50) -> dict: ...

class InProcessTransport:
    def __init__(self, gateway: ApplicationGateway, account: str):
        self.gateway, self.account = gateway, account
    def command(self, message):return self.gateway.command(self.account,message)
    def snapshot(self):return self.gateway.project(self.account)
    def receipt(self, command_id):return self.gateway.receipt(self.account,command_id)
    def chat_history(self, channel_id, before=None, limit=50):return self.gateway.chat_history(self.account,channel_id,before,limit)
    def chat_members(self):return self.gateway.chat_members(self.account)
