"""
Creating calculation settings and grids
"""
from abc import ABC, abstractmethod
from enum import auto, StrEnum
from typing import Optional

from pydantic import BaseModel, model_validator

from dstability_toolbox.geometry import CharPointsProfile, CharPointType, Side


class SlipPlaneModel(StrEnum):
    UPLIFT_VAN_PARTICLE_SWARM = auto()
    BISHOP_BRUTE_FORCE = auto()


class UpliftVanSearchMode(StrEnum):
    NORMAL = auto()
    THOROUGH = auto()


class GridSettings(ABC, BaseModel):
    grid_setting_name: str
    slip_plane_model: SlipPlaneModel
    apply_minimum_slip_plane_dimensions: bool
    minimum_slip_plane_depth: Optional[float] = None
    minimum_slip_plane_length: Optional[float] = None
    apply_constraint_zone_a: bool
    zone_a_position: Optional[CharPointType] = None
    zone_a_direction: Optional[Side] = None
    zone_a_width: Optional[float] = None
    apply_constraint_zone_b: bool
    zone_b_position: Optional[CharPointType] = None
    zone_b_direction: Optional[Side] = None
    zone_b_width: Optional[float] = None

    # TODO: Fix validatie - leidt tot problemen op deze wijze met @model_validator
    # @model_validator(mode="after")
    # def check_input(self):
    #     required_fields = {
    #         'apply_minimum_slip_plane_dimensions': ['minimum_slip_plane_length', 'minimum_slip_plane_depth'],
    #         'apply_constraint_zone_a': ['zone_a_position', 'zone_a_direction', 'zone_a_width'],
    #         'apply_constraint_zone_b': ['zone_b_position', 'zone_b_direction', 'zone_b_width']
    #     }
    #
    #     for condition, fields in required_fields.items():
    #         if getattr(self, condition):
    #             for field in fields:
    #                 if getattr(self, field) is None:
    #                     raise ValueError(f"{field} is required when {condition} is True")

    @classmethod
    def from_dict(cls, input_dict: dict):
        slip_plane_model = input_dict['slip_plane_model']

        if slip_plane_model == SlipPlaneModel.UPLIFT_VAN_PARTICLE_SWARM:
            return UpliftVanParticleSwarm.model_validate(input_dict)

        if slip_plane_model == SlipPlaneModel.BISHOP_BRUTE_FORCE:
            return BishopBruteForce.model_validate(input_dict)

        raise ValueError(f"Unknown slip plane model {slip_plane_model}")

    @abstractmethod
    def to_geolib(self, char_points_profile: CharPointsProfile):
        """Exports the grid settings to a GEOLib class"""
        pass


class UpliftVanParticleSwarm(GridSettings):
    """Defines the grid settings needed for creating a Uplift Van particle swarm grid"""
    grid_1_position: CharPointType
    grid_1_direction: Side
    grid_1_offset_horizontal: float
    grid_1_offset_vertical: float
    grid_1_width: float
    grid_1_height: float
    grid_2_position: CharPointType
    grid_2_direction: Side
    grid_2_offset_horizontal: float
    grid_2_offset_vertical: float
    grid_2_height: float
    grid_2_width: float
    top_tangent_area: float
    height_tangent_area: float
    search_mode: UpliftVanSearchMode

    def to_geolib(self, char_points_profile: CharPointsProfile):
        pass


class BishopBruteForce(GridSettings):
    """Defines the grid settings for creating a Bishop brute force grid"""
    grid_position: CharPointType
    grid_direction: Side
    grid_offset_horizontal: float
    grid_offset_vertical: float
    grid_points_horizontal: int
    grid_points_vertical: int
    grid_points_per_m: int
    bottom_tangent_line: float
    tangent_line_count: int
    tangent_lines_per_m: int
    move_grid: bool

    def to_geolib(self, char_points_profile: CharPointsProfile):
        pass


class GridSettingsSet(BaseModel):
    """Represents a set of grid settings which can be added to a scenario.
    Multiple GridSettings can be useful for finding the minimum
    safety factor.

    Attributes:
        name (str): Name of the grid settings set
        grid_settings (list): List of GridSettings instances"""

    name: str
    grid_settings: list[BishopBruteForce | UpliftVanParticleSwarm]


class GridSettingsCollection(BaseModel):
    """Represents all the available grid settings sets

    Attributes:
        grid_settings_sets (list): List of GridSettingsSet instances"""

    grid_settings_sets: list[GridSettingsSet]

    @classmethod
    def from_dict(cls, input_dict: dict):
        """Parses the dictionary into a" GridSettingsCollection

        Args:
            input_dict (dict): The dictionary to parse
        """
        grid_settings_sets = []

        for set_name, grid_settings_list in input_dict.items():
            grid_settings = [GridSettings.from_dict(grid_settings_dict) for grid_settings_dict in grid_settings_list]
            grid_settings_sets.append(GridSettingsSet(name=set_name, grid_settings=grid_settings))

        return cls(grid_settings_sets=grid_settings_sets)

    def get_by_name(self, name: str) -> GridSettingsSet:
        """Get the grid settings set with the given name"""
        for grid_settings_set in self.grid_settings_sets:
            if grid_settings_set.name == name:
                return grid_settings_set

        raise ValueError(f"Could not find grid settings set with name {name}")


