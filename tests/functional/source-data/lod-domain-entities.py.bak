from dataclasses import dataclass


@dataclass(frozen=True)
class UserDTO:
    id: int
    name: str

@dataclass(frozen=True)
class Session:
    user: UserDTO

def domain_layer_exemption(session: Session) -> None:
    # Allowed: session and user are frozen dataclasses (Domain Entities)
    _username: str = session.user.name
