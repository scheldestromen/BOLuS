from pydantic import BaseModel, model_validator, Field
from typing import Self

from dstability_toolbox.geometry import  SurfaceLine


class SoilLayer(BaseModel):
    """Representation of a 1D soil layer"""
    soil_type: str
    top: float


class SoilProfile(BaseModel):
    """Representation of a 1D soil profile"""
    name: str
    layers: list[SoilLayer]

    @model_validator(mode='after')
    def check_descending_tops(self) -> Self:
        tops = [layer.top for layer in self.layers]

        if tops != sorted(tops, reverse=True):
            raise ValueError(
                f"The soil layers in the soil profile {self.name} are not in descending order. "
                f"Make sure each top is lower than the previous one."
            )

        return self


class SoilProfileCollection(BaseModel):
    """Collection of 1D soil profiles of type SoilProfile"""
    profiles: list[SoilProfile]

    @classmethod
    def from_dict(cls, soil_profile_dict: dict):
        profiles = []

        for name, layer_dicts in soil_profile_dict.items():
            layers = [SoilLayer.model_validate(layer_dict) for layer_dict in layer_dicts]
            profiles.append(SoilProfile(name=name, layers=layers))

        return cls(profiles=profiles)


class SoilPolygon(BaseModel):
    """Representation of a 2D soil layer"""
    # TODO: Deze is misschien niet nodig, gezien geolib een gelijke heeft. Misschien ook wel.
    pass


class Subsoil(BaseModel):
    """Representation of a 2D subsoil schematization. This is a collection of (multiple)
    SoilPolygon's belonging to the same cross-sectional schematization."""
    polygons: list[SoilPolygon]

    # TODO: Validate non-overlapping


def subsoil_from_soil_profiles(
        soil_profiles: list[SoilProfile],
        transitions: list[float],
        surface_line: SurfaceLine
) -> Subsoil:
    """Creates an instance of Subsoil from one or more SoilProfile objects."""
    if len(soil_profiles) != len(transitions) - 1:
        raise ValueError("The number of soil profiles does not match the number of transitions.")

    # TODO: verder gaan. Eerst grenzen uit surf