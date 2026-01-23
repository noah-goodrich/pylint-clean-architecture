from dataclasses import dataclass, field
from typing import List, Dict, Union

@dataclass(frozen = True)
class LinterResult:
    """Standardized linter result."""
    code: str
    message: str
    locations: List[str] = field(default_factory=list)

    def add_location(self, location: str) -> 'LinterResult':
        """
        Add a location to the result.
        Since it's frozen, we return a new instance.
        """
        # JUSTIFICATION: Dataclass replacement is the idiomatic way to handle immutable state updates.
        new_locations = list(self.locations)
        new_locations.append(location)
        import dataclasses
        return dataclasses.replace(self, locations=new_locations)

    def to_dict(self) -> Dict[str, Union[str, List[str]]]:
        """Convert to dictionary for reporter."""
        return {
            "code": self.code,
            "message": self.message,
            "location": ", ".join(self.locations) if self.locations else "N/A",
            "locations": self.locations
        }
