from typing import Protocol

class CustomService:
    def get_version(self) -> str:
        return "1.0"

class Repository(Protocol):
    def get_config(self) -> CustomService: ...

def protocol_hint_exemption(repo: Repository) -> None:
    # Allowed: repo is a Protocol; we trust its contract.
    _res: str = repo.get_config().get_version()
