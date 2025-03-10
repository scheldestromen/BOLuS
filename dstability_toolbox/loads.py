from typing import Any

from pydantic import BaseModel

from dstability_toolbox.geometry import CharPointType, Side


class Load(BaseModel):
    """Representation of a uniform load.

    Attributes:
        name: The name of the load.
        magnitude: The magnitude of the load.
        angle: The angle of the load distribution.
        width: The width of the load.
        position: The position of the load, characterised by a CharPointType.
        direction: The direction of the load, either "inward" or "outward"."""

    name: str
    magnitude: float
    angle: float
    width: float
    position: CharPointType
    direction: Side


class LoadCollection(BaseModel):
    """Represents a collection of load instances.

    Attributes:
        loads: A list containing instances of the Load class.
    """

    loads: list[Load]

    def get_by_name(self, name: str) -> Load:
        """Returns the load with the given name"""
        for load in self.loads:
            if load.name == name:
                return load

        raise NameError(f"Could not find load with name {name}")

    @classmethod
    def from_list(cls, loads_dicts: list[dict[str, Any]]) -> "LoadCollection":
        """Parses the dictionary into a LoadCollection

        Args:
            loads_dicts: List with load dicts to parse. The keys should match
              the Load attributes (name, magnitude, angle).
        """
        loads = [Load.model_validate(load_dict) for load_dict in loads_dicts]

        return cls(loads=loads)
