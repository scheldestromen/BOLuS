# Maken van loads o.b.v. bepaalde instellingen bv. karakteristieke punten
from typing import Literal

from pydantic import BaseModel

from dstability_toolbox.geometry import CharPointType


class Load(BaseModel):
    """Representation of a uniform load"""
    name: str
    magnitude: float
    angle: float
    width: float
    position: CharPointType
    direction: Literal['inward', 'outward']


class LoadCollection(BaseModel):
    loads: list[Load]

    def get_by_name(self, name) -> Load:
        """Returns the load with the given name"""
        for load in self.loads:
            if load.name == name:
                return load

        raise NameError(f"Could not find load with name {name}")

    @classmethod
    def from_list(cls, loads_dicts: list):
        """Parses the dictionary into a LoadCollection

        Args:
            loads_dicts: List with load dicts to parse. The keys should match
              the Load attributes (name, magnitude, angle).
        """
        loads = [Load.model_validate(load_dict) for load_dict in loads_dicts]

        return cls(loads=loads)
