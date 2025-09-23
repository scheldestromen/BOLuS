"""
Creating calculation settings and grids
"""

from abc import ABC, abstractmethod
from enum import StrEnum, auto
from typing import Optional

from geolib.geometry.one import Point as GLPoint
from geolib.models.dstability.analysis import (
    DStabilityBishopBruteForceAnalysisMethod, DStabilitySearchArea,
    DStabilitySearchGrid, DStabilitySlipPlaneConstraints,
    DStabilityUpliftVanParticleSwarmAnalysisMethod)
from geolib.models.dstability.internal import OptionsType
from pydantic import BaseModel, model_validator

from bolus.toolbox.geometry import CharPointsProfile, CharPointType, Side


class SlipPlaneModel(StrEnum):
    UPLIFT_VAN_PARTICLE_SWARM = auto()
    BISHOP_BRUTE_FORCE = auto()


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
    def check_required_constraints_input(self):
        """Checks the required input depending on which constraints are used."""

        required_fields = {
            "apply_minimum_slip_plane_dimensions": [
                "minimum_slip_plane_length",
                "minimum_slip_plane_depth",
            ],
            "apply_constraint_zone_a": [
                "zone_a_position",
                "zone_a_direction",
                "zone_a_width",
            ],
            "apply_constraint_zone_b": [
                "zone_b_position",
                "zone_b_direction",
                "zone_b_width",
            ],
        }

        for condition, fields in required_fields.items():
            if getattr(self, condition):
                for field in fields:
                    if getattr(self, field) is None:
                        raise ValueError(
                            f"{field} is required when {condition} is True"
                        )

        return self

    @abstractmethod
    def to_geolib(self, char_points_profile: CharPointsProfile):
        """Exports the grid settings to a GEOLib class"""

    def slip_plane_constraints_to_geolib(self, char_points_profile: CharPointsProfile):
        slip_plane_constraints = DStabilitySlipPlaneConstraints()

        if self.apply_constraint_zone_a is True:
            # Determine zone edges based on settings
            sign = char_points_profile.determine_l_direction_sign(self.zone_a_direction)
            ref_point_zone_a = char_points_profile.get_point_by_type(
                self.zone_a_position
            )
            zone_a_l1 = ref_point_zone_a.l
            zone_a_l2 = ref_point_zone_a.l + sign * self.zone_a_width

            # Assign values for Zone A
            slip_plane_constraints.is_zone_a_constraints_enabled = True
            slip_plane_constraints.x_left_zone_a = min(
                zone_a_l1, zone_a_l2
            )  # Min because unknown which is the left
            slip_plane_constraints.width_zone_a = self.zone_a_width

        if self.apply_constraint_zone_b is True:
            # Determine zone edges based on settings
            sign = char_points_profile.determine_l_direction_sign(self.zone_b_direction)
            ref_point_zone_b = char_points_profile.get_point_by_type(
                self.zone_b_position
            )
            zone_b_l1 = ref_point_zone_b.l
            zone_b_l2 = ref_point_zone_b.l + sign * self.zone_b_width

            # Assign values for Zone B
            slip_plane_constraints.is_zone_b_constraints_enabled = True
            slip_plane_constraints.x_left_zone_b = min(
                zone_b_l1, zone_b_l2
            )  # Min because unknown which is the left
            slip_plane_constraints.width_zone_b = self.zone_b_width

        if self.apply_minimum_slip_plane_dimensions is True:
            # Assign values for minimum dimensions
            slip_plane_constraints.is_size_constraints_enabled = True
            slip_plane_constraints.minimum_slip_plane_length = (
                self.minimum_slip_plane_length
            )
            slip_plane_constraints.minimum_slip_plane_depth = (
                self.minimum_slip_plane_depth
            )

        return slip_plane_constraints


class UpliftVanParticleSwarm(GridSettings):
    """Defines the grid settings needed for creating an Uplift Van particle swarm grid"""

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
    tangent_area_position: CharPointType
    tangent_area_offset: float
    height_tangent_area: float
    search_mode: OptionsType

    def to_geolib(self, char_points_profile: CharPointsProfile):
        # Create the first search area
        grid_1_ref_point = char_points_profile.get_point_by_type(self.grid_1_position)
        grid_1_sign = char_points_profile.determine_l_direction_sign(
            self.grid_1_direction
        )

        grid_1_l1 = grid_1_ref_point.l + grid_1_sign * self.grid_1_offset_horizontal
        grid_1_l2 = grid_1_l1 + grid_1_sign * self.grid_1_width
        grid_1_top = (
            grid_1_ref_point.z + self.grid_1_offset_vertical + self.grid_1_height
        )

        search_area_a = DStabilitySearchArea(
            height=self.grid_1_height,
            width=self.grid_1_width,
            top_left=GLPoint(x=min(grid_1_l1, grid_1_l2), z=grid_1_top),
        )

        # Create the second search area
        grid_2_ref_point = char_points_profile.get_point_by_type(self.grid_2_position)
        grid_2_sign = char_points_profile.determine_l_direction_sign(
            self.grid_2_direction
        )

        grid_2_l1 = grid_2_ref_point.l + grid_2_sign * self.grid_2_offset_horizontal
        grid_2_l2 = grid_2_l1 + grid_2_sign * self.grid_2_width
        grid_2_top = (
            grid_2_ref_point.z + self.grid_2_offset_vertical + self.grid_2_height
        )

        search_area_b = DStabilitySearchArea(
            height=self.grid_2_height,
            width=self.grid_2_width,
            top_left=GLPoint(x=min(grid_2_l1, grid_2_l2), z=grid_2_top),
        )

        # Create the tangent area
        tangent_area_ref_point = char_points_profile.get_point_by_type(self.tangent_area_position)
        tangent_area_top = tangent_area_ref_point.z + self.tangent_area_offset

        # Slip plane constraints
        slip_plane_constraints = self.slip_plane_constraints_to_geolib(
            char_points_profile
        )

        # Create the analysis method
        analysis_method = DStabilityUpliftVanParticleSwarmAnalysisMethod(
            options_type=self.search_mode,
            search_area_a=search_area_a,
            search_area_b=search_area_b,
            tangent_area_height=self.height_tangent_area,
            tangent_area_top_z=tangent_area_top,
            slip_plane_constraints=slip_plane_constraints,
        )

        return analysis_method


class BishopBruteForce(GridSettings):
    """Defines the grid settings for creating a Bishop brute force grid"""

    grid_position: CharPointType
    grid_direction: Side
    grid_offset_horizontal: float
    grid_offset_vertical: float
    grid_points_horizontal: int
    grid_points_vertical: int
    grid_points_per_m: int
    tangent_line_position: CharPointType
    tangent_line_offset: float
    tangent_line_count: int
    tangent_lines_per_m: int
    move_grid: bool

    def to_geolib(
        self, char_points_profile: CharPointsProfile
    ) -> DStabilityBishopBruteForceAnalysisMethod:
        grid_ref_point = char_points_profile.get_point_by_type(self.grid_position)
        sign = char_points_profile.determine_l_direction_sign(self.grid_direction)
        grid_width = (
            self.grid_points_horizontal - 1
        ) / self.grid_points_per_m  # n points means n - 1 gaps

        grid_l1 = grid_ref_point.l + sign * self.grid_offset_horizontal
        grid_l2 = grid_l1 + sign * grid_width
        grid_bottom = grid_ref_point.z + self.grid_offset_vertical

        search_grid = DStabilitySearchGrid(
            bottom_left=GLPoint(
                x=min(grid_l1, grid_l2), z=grid_bottom
            ),  # Min because unknown which is the left
            number_of_points_in_x=self.grid_points_horizontal,
            number_of_points_in_z=self.grid_points_vertical,
            space=1 / self.grid_points_per_m,
        )

        # Create the tangent line
        tangent_lines_ref_point = char_points_profile.get_point_by_type(self.tangent_line_position)
        tangent_lines_top = tangent_lines_ref_point.z + self.tangent_line_offset
        tangent_lines_bottom = tangent_lines_top - (self.tangent_line_count - 1) / self.tangent_lines_per_m

        # Slip plane constraints
        slip_plane_constraints = self.slip_plane_constraints_to_geolib(
            char_points_profile
        )

        analysis_method = DStabilityBishopBruteForceAnalysisMethod(
            extrapolate_search_space=self.move_grid,
            search_grid=search_grid,
            slip_plane_constraints=slip_plane_constraints,
            bottom_tangent_line_z=tangent_lines_bottom,
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

    @model_validator(mode="after")
    def check_duplicate_grid_settings_name(self):
        grid_settings_names = [
            grid_setting.grid_setting_name for grid_setting in self.grid_settings
        ]

        if len(grid_settings_names) != len(set(grid_settings_names)):
            raise ValueError(
                f"Duplicate grid settings names are not allowed.\n"
                f"Grid settings set name: {self.name}\n"
                f"Grid settings names: {grid_settings_names}\n"
            )

        return self


class GridSettingsSetCollection(BaseModel):
    """Represents all the available grid settings sets

    Attributes:
        grid_settings_sets (list): List of GridSettingsSet instances"""

    grid_settings_sets: list[GridSettingsSet]

    def get_by_name(self, name: str) -> GridSettingsSet:
        """Get the grid settings set with the given name"""
        for grid_settings_set in self.grid_settings_sets:
            if grid_settings_set.name == name:
                return grid_settings_set

        raise ValueError(f"Could not find grid settings set with name {name}")
