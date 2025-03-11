"""Tests for the input reader functionality"""

# TODO: nalopen en herzien

import os
from pathlib import Path
from unittest import TestCase

import openpyxl
from geolib.models.dstability.internal import OptionsType
from geolib.soils import ShearStrengthModelTypePhreaticLevel

from excel_tool.input_reader import (ExcelInputReader, RawUserInput,
                                     RawInputToUserInputStructure,
                                     INPUT_TO_BOOL, INPUT_TO_CHAR_POINTS,
                                     INPUT_TO_SIDE, INPUT_TO_WATER_LINE_TYPE,
                                     INPUT_TO_SLIP_PLANE_MODEL)
from toolbox.geometry import CharPointType, Side
from toolbox.water import WaterLineType
from toolbox.calculation_settings import SlipPlaneModel

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURE_DIR = os.path.join(os.path.dirname(os.path.dirname(TEST_DIR)), "fixtures")
TEST_INPUT_FILE = os.path.join(FIXTURE_DIR, "test_input.xlsx")


class TestExcelInputReader(TestCase):
    """Tests for the ExcelInputReader class"""
    pass


class TestRawInputToUserInputStructure(TestCase):
    """Tests for the RawInputToUserInputStructure class"""

    def setUp(self):
        """Set up test data"""
        self.raw_settings = {"min_soil_profile_depth": 10.0, "execute_calculations": True}
        self.raw_input = RawUserInput(
            settings={"min_soil_profile_depth": 10.0, "execute_calculations": True},
            surface_lines={"Profile 1": [0, 0, 0, 1, 0, 1]},
            char_points={
                "Profile 1": {
                    "x_surface_level_water_side": 0,
                    "y_surface_level_water_side": -1,
                    "z_surface_level_water_side": -2,
                    "x_toe_canal": -1,
                    "y_toe_canal": -1,
                    "z_toe_canal": -1,
                    "x_start_canal": -1,
                    "y_start_canal": -1,
                    "z_start_canal": -1,
                    "x_dike_toe_water_side": -1,
                    "y_dike_toe_water_side": -1,
                    "z_dike_toe_water_side": -1,
                    "x_berm_crest_water_side": -1,
                    "y_berm_crest_water_side": -1,
                    "z_berm_crest_water_side": -1,
                    "x_berm_start_water_side": -1,
                    "y_berm_start_water_side": -1,
                    "z_berm_start_water_side": -1,
                    "x_dike_crest_water_side": -1,
                    "y_dike_crest_water_side": -1,
                    "z_dike_crest_water_side": -1,
                    "x_traffic_load_water_side": -1,
                    "y_traffic_load_water_side": -1,
                    "z_traffic_load_water_side": -1,
                    "x_traffic_load_land_side": -1,
                    "y_traffic_load_land_side": -1,
                    "z_traffic_load_land_side": -1,
                    "x_dike_crest_land_side": -1,
                    "y_dike_crest_land_side": -1,
                    "z_dike_crest_land_side": -1,
                    "x_berm_start_land_side": -1,
                    "y_berm_start_land_side": -1,
                    "z_berm_start_land_side": -1,
                    "x_berm_crest_land_side": -1,
                    "y_berm_crest_land_side": -1,
                    "z_berm_crest_land_side": -1,
                    "x_dike_toe_land_side": -1,
                    "y_dike_toe_land_side": -1,
                    "z_dike_toe_land_side": -1,
                    "x_ditch_start_water_side": -1,
                    "y_ditch_start_water_side": -1,
                    "z_ditch_start_water_side": -1,
                    "x_ditch_bottom_water_side": -1,
                    "y_ditch_bottom_water_side": -1,
                    "z_ditch_bottom_water_side": -1,
                    "x_ditch_bottom_land_side": -1,
                    "y_ditch_bottom_land_side": -1,
                    "z_ditch_bottom_land_side": -1,
                    "x_ditch_start_land_side": -1,
                    "y_ditch_start_land_side": -1,
                    "z_ditch_start_land_side": -1,
                    "x_surface_level_land_side": 1,
                    "y_surface_level_land_side": 2,
                    "z_surface_level_land_side": 3
                }
            },
            soil_params=[{
                "name": "Clay",
                "unsaturated_weight": 16.0,
                "saturated_weight": 18.0,
                "strength_model_above": "Mohr-Coulomb",
                "strength_model_below": "Mohr-Coulomb",
                "c": 5.0,
                "phi": 30.0,
                "shear_stress_ratio_s": 0.25,
                "strength_exponent_m": 0.8,
                "pop": 10.0,
                "consolidation_traffic_load": 50,
            }],
            soil_profiles={"Profile 1": [{"soil_type": "Clay", "top": 1.0}]},
            soil_profile_positions={"Calc 1": {"Profile 1": None}},
            loads=[{
                "name": "Traffic",
                "magnitude": 13.0,
                "angle": 0.0,
                "width": 2.5,
                "position": "dike_crest_land_side",
                "direction": "water_side",
            }],
            hydraulic_pressure={
                "calc1": {
                    "scenario1": {
                        "stage1": [{
                            "type": "Stijghoogtelijn",
                            "line_name": "phreatic",
                            "values": [0, 2, 50, 1],
                        }]
                    }
                }
            },
            grid_settings={"Set 1": [{
                "grid_setting_name": "Bishop",
                "slip_plane_model": "bishop_brute_force",
                "grid_position": "dike_crest_land_side",
                "grid_direction": "land_side",
                "grid_offset_horizontal": 1,
                "grid_offset_vertical": 4,
                "grid_points_horizontal": 20,
                "grid_points_vertical": 20,
                "grid_points_per_m": 2,
                "bottom_tangent_line": -10,
                "tangent_line_count": 20,
                "tangent_lines_per_m": 2,
                "move_grid": True,
                "grid_1_position": None,
                "grid_1_direction": None,
                "grid_1_offset_horizontal": None,
                "grid_1_offset_vertical": None,
                "grid_1_width": None,
                "grid_1_height": None,
                "grid_2_position": None,
                "grid_2_direction": None,
                "grid_2_offset_horizontal": None,
                "grid_2_offset_vertical": None,
                "grid_2_height": None,
                "grid_2_width": None,
                "top_tangent_area": None,
                "height_tangent_area": None,
                "search_mode": None,
                "apply_minimum_slip_plane_dimensions": False,
                "minimum_slip_plane_depth": None,
                "minimum_slip_plane_length": None,
                "apply_constraint_zone_a": False,
                "zone_a_position": None,
                "zone_a_direction": None,
                "zone_a_width": None,
                "apply_constraint_zone_b": False,
                "zone_b_position": None,
                "zone_b_direction": None,
                "zone_b_width": None}]
            },
            model_configs=[{
                "calc_name": "Calc 1",
                "scenarios": [{
                    "scenario_name": "Scenario 1",
                    "grid_settings_set_name": "Set 1",
                    "stages": [
                        {
                            "stage_name": "Stage 1",
                            "geometry_name": "Profile 1",
                            "soil_profile_position_name": "Calc 1",
                            "apply_state_points": True,
                            "load_name": "Traffic",
                            "evaluate": True
                        }
                    ]
                }]
            }]
        )

    def test_convert_settings(self):
        """Test converting settings"""
        settings = RawInputToUserInputStructure.convert_settings(self.raw_input.settings)
        self.assertEqual(settings.min_soil_profile_depth, 10.0)
        self.assertTrue(settings.execute_calculations)

    def test_convert_surface_lines(self):
        """Test converting surface lines"""
        surface_lines = RawInputToUserInputStructure.convert_surface_lines(self.raw_input.surface_lines)
        self.assertEqual(len(surface_lines.surface_lines), 1)
        self.assertEqual(surface_lines.surface_lines[0].name, "Profile 1")
        self.assertEqual(len(surface_lines.surface_lines[0].points), 2)

    def test_convert_char_points(self):
        """Test converting characteristic points"""
        char_point_col = RawInputToUserInputStructure.convert_char_points(self.raw_input.char_points)
        self.assertEqual(len(char_point_col.char_points_profiles), 1)
        self.assertEqual(char_point_col.char_points_profiles[0].name, "Profile 1")
        self.assertEqual(char_point_col.char_points_profiles[0].points[0].type, CharPointType.SURFACE_LEVEL_WATER_SIDE)
        self.assertEqual(char_point_col.char_points_profiles[0].points[0].x, 0.)
        self.assertEqual(char_point_col.char_points_profiles[0].points[0].z, -2.)

    def test_convert_soil_collection(self):
        """Test converting soil collection"""
        soils = RawInputToUserInputStructure.convert_soil_collection(self.raw_input.soil_params)
        self.assertEqual(len(soils.soils), 1)
        soil = soils.soils[0]
        self.assertEqual(soil.gl_soil.name, "Clay")
        self.assertEqual(soil.gl_soil.soil_weight_parameters.unsaturated_weight, 16.0)
        self.assertEqual(soil.gl_soil.soil_weight_parameters.saturated_weight, 18.0)
        self.assertEqual(soil.gl_soil.shear_strength_model_above_phreatic_level,
                         ShearStrengthModelTypePhreaticLevel.MOHR_COULOMB)
        self.assertEqual(soil.gl_soil.shear_strength_model_below_phreatic_level,
                         ShearStrengthModelTypePhreaticLevel.MOHR_COULOMB)
        self.assertEqual(soil.gl_soil.mohr_coulomb_parameters.cohesion.mean, 5.0)
        self.assertEqual(soil.gl_soil.mohr_coulomb_parameters.friction_angle.mean, 30.0)
        self.assertEqual(soil.gl_soil.undrained_parameters.shear_strength_ratio.mean, 0.25)
        self.assertEqual(soil.gl_soil.undrained_parameters.strength_increase_exponent.mean, 0.8)
        self.assertEqual(soil.pop, 10.0)
        self.assertEqual(soil.consolidation_traffic_load, 50.)

    def test_convert_soil_profile_collection(self):
        """Test converting soil profile collection"""
        profiles = RawInputToUserInputStructure.convert_soil_profile_collection(self.raw_input.soil_profiles)
        self.assertEqual(len(profiles.soil_profiles), 1)
        profile = profiles.soil_profiles[0]
        self.assertEqual(profile.name, "Profile 1")
        self.assertEqual(len(profile.layers), 1)
        self.assertEqual(profile.layers[0].soil_name, "Clay")
        self.assertEqual(profile.layers[0].top_level, 5.0)

    def test_convert_soil_profile_positions(self):
        """Test converting soil profile positions"""
        positions = RawInputToUserInputStructure.convert_soil_profile_positions(self.raw_input.soil_profile_positions)
        self.assertEqual(len(positions.soil_profile_positions), 1)
        position = positions.soil_profile_positions[0]
        self.assertEqual(position.name, "Calc 1")
        self.assertEqual(position.x_coordinate, 0.0)
        self.assertEqual(position.soil_profile_name, "Profile 1")

    def test_convert_loads(self):
        """Test converting loads"""
        loads = RawInputToUserInputStructure.convert_loads(self.raw_input.loads)
        self.assertEqual(len(loads.loads), 1)
        self.assertEqual(loads.loads[0].name, "Traffic")
        self.assertEqual(loads.loads[0].magnitude, 13.0)
        self.assertEqual(loads.loads[0].position, CharPointType.DIKE_CREST_LAND_SIDE)
        self.assertEqual(loads.loads[0].direction, Side.WATER_SIDE)

    def test_convert_waternet_collection(self):
        """Test converting waternet collection"""
        waternets = RawInputToUserInputStructure.convert_waternet_collection(
            self.raw_input.hydraulic_pressure,
            name_phreatic_line="phreatic"
        )
        self.assertEqual(len(waternets.waternets), 1)
        waternet = waternets.waternets[0]
        self.assertEqual(waternet.calc_name, "calc1")
        self.assertEqual(waternet.scenario_name, "scenario1")
        self.assertEqual(waternet.stage_name, "stage1")
        self.assertEqual(len(waternet.head_lines), 1)
        self.assertTrue(waternet.head_lines[0].is_phreatic)

    def test_convert_grid_settings_set_collection(self):
        """Test converting grid settings set collection"""
        grid_setting_set_collection = RawInputToUserInputStructure.convert_grid_settings_set_collection(
            self.raw_input.grid_settings
        )
        self.assertEqual(len(grid_setting_set_collection.grid_settings_sets), 1)
        grid_set = grid_setting_set_collection.grid_settings_sets[0]
        self.assertEqual(grid_set.name, "Set 1")
        self.assertEqual(len(grid_set.grid_settings), 1)
        self.assertEqual(grid_set.grid_settings[0].grid_setting_name, "Bishop")

    def test_convert_model_configs(self):
        """Test converting model configs"""
        configs = RawInputToUserInputStructure.convert_model_configs(self.raw_input.model_configs)
        self.assertEqual(len(configs), 1)
        config = configs[0]
        self.assertEqual(config.calc_name, "Calc 1")
        self.assertEqual(len(config.scenarios), 1)
        self.assertEqual(config.scenarios[0].scenario_name, "Scenario 1")
        self.assertTrue(config.scenarios[0].stages[0].apply_state_points)
        self.assertTrue(config.scenarios[0].evaluate)

    def test_convert(self):
        pass

# class TestInputMappings(TestCase):
#     """Tests for input mapping dictionaries"""
#
#     def test_bool_mapping(self):
#         """Test boolean value mapping"""
#         self.assertTrue(INPUT_TO_BOOL["Ja"])
#         self.assertFalse(INPUT_TO_BOOL["Nee"])
#
#     def test_char_points_mapping(self):
#         """Test characteristic points mapping"""
#         self.assertEqual(
#             INPUT_TO_CHAR_POINTS["Kruin binnentalud"],
#             CharPointType.DIKE_CREST_LAND_SIDE
#         )
#         self.assertEqual(
#             INPUT_TO_CHAR_POINTS["Maaiveld buitenwaarts"],
#             CharPointType.SURFACE_LEVEL_WATER_SIDE
#         )
#
#     def test_side_mapping(self):
#         """Test side mapping"""
#         self.assertEqual(INPUT_TO_SIDE["Binnenwaarts"], Side.LAND_SIDE)
#         self.assertEqual(INPUT_TO_SIDE["Buitenwaarts"], Side.WATER_SIDE)
#
#     def test_water_line_type_mapping(self):
#         """Test water line type mapping"""
#         self.assertEqual(
#             INPUT_TO_WATER_LINE_TYPE["Stijghoogtelijn"],
#             WaterLineType.HEADLINE
#         )
#         self.assertEqual(
#             INPUT_TO_WATER_LINE_TYPE["Referentielijn"],
#             WaterLineType.REFERENCE_LINE
#         )
#
#     def test_slip_plane_model_mapping(self):
#         """Test slip plane model mapping"""
#         self.assertEqual(
#             INPUT_TO_SLIP_PLANE_MODEL["Bishop"],
#             SlipPlaneModel.BISHOP_BRUTE_FORCE
#         )
#         self.assertEqual(
#             INPUT_TO_SLIP_PLANE_MODEL["Uplift Van"],
#             SlipPlaneModel.UPLIFT_VAN_PARTICLE_SWARM
#         )
