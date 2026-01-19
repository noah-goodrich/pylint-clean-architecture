# No imports needed for Any removal if we use object

from ..interface.telemetry import ProjectTelemetry


class ExcelsiorContainer:
    def __init__(self):
        self._singletons = {}
        self.register_telemetry(project_name="EXCELSIOR", color="red", welcome_msg="Command Cruiser Online")

    def register_telemetry(self, project_name: str, color: str, welcome_msg: str):
        telemetry = ProjectTelemetry(project_name, color, welcome_msg)
        self.register_singleton("TelemetryPort", telemetry)

    def register_singleton(self, key: str, instance: object):
        self._singletons[key] = instance

    def get(self, key: str) -> object:
        if key in self._singletons:
            return self._singletons[key]
        raise ValueError(f"Dependency '{key}' not registered.")
