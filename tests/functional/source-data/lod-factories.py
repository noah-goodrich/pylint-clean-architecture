class CustomService:
    def get_version(self) -> str:
        return "1.0"

def factory_instantiation_exemption() -> None:
    # Objects created in local scope are 'friends'
    service: CustomService = CustomService()
    # Allowed: Chaining permitted on locally instantiated objects
    _res: str = service.get_version().lower()
