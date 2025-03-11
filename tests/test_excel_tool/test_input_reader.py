"""Tests for the input reader functionality"""

# TODO: nalopen en herzien

import os
from pathlib import Path
from unittest import TestCase

import openpyxl
from geolib.models.dstability.internal import OptionsType

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
                    "y_surface_level_water_side": 0,
                    "z_surface_level_water_side": 0,
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
            soil_profiles={"Profile 1": [{"soil_type": "Clay", "top": 0.0}]},
            soil_profile_positions={"Profile 1": {"l_coord": 0.0}},
            loads=[{
                "name": "Traffic",
                "magnitude": 13.0,
                "angle": 0.0,
                "width": 2.5,
                "position": "Kruin binnentalud",
                "direction": "Binnenwaarts",
            }],
            hydraulic_pressure={
                "calc1": {
                    "scenario1": {
                        "stage1": [{
                            "type": "Stijghoogtelijn",
                            "line_name": "phreatic",
                            "values": [0, 0, 1, 1],
                        }]
                    }
                }
            },
            grid_settings={
                "Set 1": [{
                    "grid_setting_name": "Bishop",
                    "slip_plane_model": "Bishop",
                    "grid_position": "Kruin binnentalud",
                    "grid_direction": "Binnenwaarts",
                }]
            },
            model_configs=[{
                "calc_name": "Calc 1",
                "scenario_name": "Scenario 1",
                "stage_name": "Stage 1",
                "geometry_name": "Profile 1",
                "soil_profile_position_name": "Profile 1",
                "apply_state_points": "Ja",
                "load_name": "Traffic",
                "grid_settings_set_name": "Set 1",
                "evaluate": "Ja",
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
        pass

    def test_convert_soil_collection(self):
        pass

    def test_convert_soil_profile_collection(self):
        pass

    def test_convert_soil_profile_positions(self):
        pass

    def test_convert_loads(self):
        """Test converting loads"""
        loads = RawInputToUserInputStructure.convert_loads(self.raw_input.loads)
        self.assertEqual(len(loads.loads), 1)
        self.assertEqual(loads.loads[0].name, "Traffic")
        self.assertEqual(loads.loads[0].magnitude, 13.0)
        self.assertEqual(loads.loads[0].position, CharPointType.DIKE_CREST_LAND_SIDE)
        self.assertEqual(loads.loads[0].direction, Side.LAND_SIDE)

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
        grid_settings = RawInputToUserInputStructure.convert_grid_settings_set_collection(
            self.raw_input.grid_settings
        )
        self.assertEqual(len(grid_settings.grid_settings_sets), 1)
        grid_set = grid_settings.grid_settings_sets[0]
        self.assertEqual(grid_set.name, "Set 1")
        self.assertEqual(len(grid_set.grid_settings), 1)
        self.assertEqual(grid_set.grid_settings[0].name, "Bishop")

    def test_convert_model_configs(self):
        """Test converting model configs"""
        configs = RawInputToUserInputStructure.convert_model_configs(self.raw_input.model_configs)
        self.assertEqual(len(configs), 1)
        config = configs[0]
        self.assertEqual(config.calc_name, "Calc 1")
        self.assertEqual(config.scenario_name, "Scenario 1")
        self.assertTrue(config.apply_state_points)
        self.assertTrue(config.evaluate)

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
