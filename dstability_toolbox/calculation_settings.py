"""
Creating calculation settings and grids
"""
from pydantic import BaseModel, model_validator
from abc import ABC, abstractmethod
from enum import auto, StrEnum
from typing import Optional

from geolib.models.dstability.analysis import DStabilityBishopBruteForceAnalysisMethod, DStabilitySearchGrid, \
    DStabilityUpliftVanParticleSwarmAnalysisMethod, DStabilitySearchArea, DStabilitySlipPlaneConstraints
from geolib.geometry.one import Point as GLPoint

from dstability_toolbox.geometry import CharPointsProfile, CharPointType, Side


class SlipPlaneModel(StrEnum):
    UPLIFT_VAN_PARTICLE_SWARM = auto()
    BISHOP_BRUTE_FORCE = auto()


class UpliftVanSearchMode(StrEnum):
    NORMAL = auto()
    THOROUGH = auto()


class GridSettings(ABC, BaseModel):
    """Base class for all grid settings"""

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

    @model_validator(mode="after")
    def check_constraints_input(self):
        """Checks the required input depending on which constraints are used."""

        required_fields = {
            'apply_minimum_slip_plane_dimensions': ['minimum_slip_plane_length', 'minimum_slip_plane_depth'],
            'apply_constraint_zone_a': ['zone_a_position', 'zone_a_direction', 'zone_a_width'],
            'apply_constraint_zone_b': ['zone_b_position', 'zone_b_direction', 'zone_b_width']
        }

        for condition, fields in required_fields.items():
            if getattr(self, condition):
                for field in fields:
                    if getattr(self, field) is None:
                        raise ValueError(f"{field} is required when {condition} is True")

        return self

    @classmethod
    def from_dict(cls, input_dict: dict):
        """Returns an instance of the child class of GridSettings based
        on the slip plane model.

        Args:
            input_dict: The dictionary to parse. Should at least have the
              keys and values for the attributes needed for the specific
              slip plane model.
        """
        slip_plane_model = input_dict['slip_plane_model']

        if slip_plane_model == SlipPlaneModel.UPLIFT_VAN_PARTICLE_SWARM:
            return UpliftVanParticleSwarm.model_validate(input_dict)

        if slip_plane_model == SlipPlaneModel.BISHOP_BRUTE_FORCE:
            return BishopBruteForce.model_validate(input_dict)

        raise ValueError(f"Unknown slip plane model {slip_plane_model}")

    @abstractmethod
    def to_geolib(self, char_points_profile: CharPointsProfile):
        """Exports the grid settings to a GEOLib class"""

    def slip_plain_constraints_to_geolib(self, char_points_profile: CharPointsProfile):
        slip_plane_constraints = DStabilitySlipPlaneConstraints()

        if self.apply_constraint_zone_a is True:
            sign = char_points_profile.determine_l_direction_sign(self.zone_a_direction)
            ref_point_zone_a = char_points_profile.get_point_by_type(self.zone_a_position)
            zone_a_l1 = ref_point_zone_a.l
            zone_a_l2 = ref_point_zone_a.l + sign * self.zone_a_width

            # Assign values for Zone A
            slip_plane_constraints.is_zone_a_constraints_enabled = True
            slip_plane_constraints.x_left_zone_a = min(zone_a_l1, zone_a_l2)  # Min because unknown which is the left
            slip_plane_constraints.width_zone_a = self.zone_a_width

        if self.apply_constraint_zone_b is True:
            sign = char_points_profile.determine_l_direction_sign(self.zone_b_direction)
            ref_point_zone_b = char_points_profile.get_point_by_type(self.zone_b_position)
            zone_b_l1 = ref_point_zone_b.l
            zone_b_l2 = ref_point_zone_b.l + sign * self.zone_b_width

            # Assign values for Zone B
            slip_plane_constraints.is_zone_b_constraints_enabled = True
            slip_plane_constraints.x_left_zone_b = min(zone_b_l1, zone_b_l2)  # Min because unknown which is the left
            slip_plane_constraints.width_zone_b = self.zone_b_width

        if self.apply_minimum_slip_plane_dimensions is True:
            # Assign values for minimum dimensions
            slip_plane_constraints.is_size_constraints_enabled = True
            slip_plane_constraints.minimum_slip_plane_length = self.minimum_slip_plane_length
            slip_plane_constraints.minimum_slip_plane_depth = self.minimum_slip_plane_depth

        return slip_plane_constraints


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
        analysis_method = DStabilityUpliftVanParticleSwarmAnalysisMethod(
            search_area_a=DStabilitySearchArea(
                height=5.0, top_left=GLPoint(x=0.0, z=10.0), width=5.0
            ),
            search_area_b=DStabilitySearchArea(
                height=5.0, top_left=GLPoint(x=35.0, z=5.0), width=5.0
            ),
            tangent_area_height=2.0,
            tangent_area_top_z=-4.5,
        )


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

    def to_geolib(self, char_points_profile: CharPointsProfile) -> DStabilityBishopBruteForceAnalysisMethod:
        sign = char_points_profile.determine_l_direction_sign(self.grid_direction)
        grid_width = self.grid_points_horizontal / self.grid_points_per_m

        grid_ref_point = char_points_profile.get_point_by_type(self.grid_position)

        grid_l1 = grid_ref_point.l + sign * self.grid_offset_horizontal
        grid_l2 = grid_l1 + sign * grid_width
        grid_bottom = grid_ref_point.z + self.grid_offset_vertical

        search_grid = DStabilitySearchGrid(
                bottom_left=GLPoint(x=min(grid_l1, grid_l2), z=grid_bottom),  # Min because unknown which is the left
                number_of_points_in_x=self.grid_points_horizontal,
                number_of_points_in_z=self.grid_points_vertical,
                space=1 / self.grid_points_per_m,
            )

        slip_plane_constraints = self.slip_plain_constraints_to_geolib(char_points_profile)

        analysis_method = DStabilityBishopBruteForceAnalysisMethod(
            extrapolate_search_space=self.move_grid,
            search_grid=search_grid,
            slip_plane_constraints=slip_plane_constraints,
            bottom_tangent_line_z=self.bottom_tangent_line,
            number_of_tangent_lines=self.tangent_line_count,
            space_tangent_lines=1 / self.tangent_lines_per_m,
        )

        return analysis_method


class GridSettingsSet(BaseModel):
    """Represents a set of grid settings which can be added to a scenario.
    Multiple GridSettings can be useful for finding the minimum
    safety factor.

    Attributes:
        name (str): Name of the grid settings set
        grid_settings (list): List of GridSettings instances"""

    name: str
    grid_settings: list[BishopBruteForce | UpliftVanParticleSwarm]
    # TODO: Check for duplicate grid_settings_name


class GridSettingsSetCollection(BaseModel):
    """Represents all the available grid settings sets

    Attributes:
        grid_settings_sets (list): List of GridSettingsSet instances"""

    grid_settings_sets: list[GridSettingsSet]

    @classmethod
    def from_dict(cls, input_dict: dict):
        """Parses the dictionary into a" GridSettingsSetCollection

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


