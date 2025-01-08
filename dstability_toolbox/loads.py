# Maken van loads o.b.v. bepaalde instellingen bv. karakteristieke punten
from pydantic import BaseModel


class Load(BaseModel):
    """Representation of a uniform load"""
    name: str
    magnitude: float
    angle: float


class LoadCollection(BaseModel):
    loads: list[Load]

    @classmethod
    def from_dict(cls, loads_dicts: list):
        """Parses the dictionary into a LoadCollection

        Args:
            loads_dicts: List with load dicts to parse. The keys should match
              the Load attributes (name, magnitude, angle).
        """
        loads = [Load.model_validate(load_dict) for load_dict in loads_dicts]

        return cls(loads=loads)
