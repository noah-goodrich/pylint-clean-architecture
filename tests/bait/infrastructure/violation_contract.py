from tests.bait.domain.protocols import MyProtocol

class MyRepository(MyProtocol):
    def execute(self) -> None:
        pass

    def extra_method(self): # This should trigger W9201
        pass
