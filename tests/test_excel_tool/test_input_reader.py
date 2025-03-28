"""Tests for the input reader functionality"""

import os
from unittest import TestCase

from geolib.models.dstability.internal import OptionsType
from geolib.soils import ShearStrengthModelTypePhreaticLevel
from geolib.models.dstability.internal import PersistableShadingTypeEnum
from excel_tool.input_reader import (ExcelInputReader, RawUserInput,
                                     RawInputToUserInputStructure,
                                     INPUT_TO_BOOL, INPUT_TO_CHAR_POINTS,
                                     INPUT_TO_SIDE, INPUT_TO_WATER_LINE_TYPE,
                                     INPUT_TO_SLIP_PLANE_MODEL,
                                     WaterLineType)
from toolbox.geometry import CharPointType, Side, Point, SurfaceLineCollection, CharPointsProfileCollection, CharPoint
from toolbox.model import Stage
from toolbox.soils import SoilCollection, Soil
from toolbox.subsoil import SoilProfileCollection, SoilProfile, SoilProfilePositionSet,SoilProfilePositionSetCollection, SoilProfilePosition, RevetmentProfileBlueprintCollection, RevetmentProfileBlueprint, RevetmentLayerBlueprint
from toolbox.loads import LoadCollection, Load
from toolbox.water import WaternetCollection, Waternet, HeadLine
from toolbox.calculation_settings import SlipPlaneModel, GridSettingsSetCollection, GridSettingsSet, BishopBruteForce, \
    UpliftVanParticleSwarm
from toolbox.model_creator import GeneralSettings, ModelConfig, StageConfig, ScenarioConfig, UserInputStructure

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
        bishop_dict = {
            "grid_setting_name": "Bishop",
            "slip_plane_model": SlipPlaneModel.BISHOP_BRUTE_FORCE,
            "grid_position": CharPointType.DIKE_CREST_LAND_SIDE,
            "grid_direction": Side.LAND_SIDE,
            "grid_offset_horizontal": 1.0,
            "grid_offset_vertical": 2.0,
            "grid_points_horizontal": 10,
            "grid_points_vertical": 11,
            "grid_points_per_m": 2,
            "tangent_line_position": CharPointType.DIKE_TOE_LAND_SIDE,
            "tangent_line_offset": -1.0,
            "tangent_line_count": 12,
            "tangent_lines_per_m": 3,
            "move_grid": True,
        }
        uplift_dict = {
            "grid_setting_name": "Uplift",
            "slip_plane_model": SlipPlaneModel.UPLIFT_VAN_PARTICLE_SWARM,
            "grid_1_position": CharPointType.DIKE_CREST_WATER_SIDE,
            "grid_1_direction": Side.WATER_SIDE,
            "grid_1_offset_horizontal": 2.0,
            "grid_1_offset_vertical": 3.0,
            "grid_1_width": 12,
            "grid_1_height": 13,
            "grid_2_position": CharPointType.DIKE_TOE_WATER_SIDE,
            "grid_2_direction": Side.WATER_SIDE,
            "grid_2_offset_horizontal": 5.0,
            "grid_2_offset_vertical": 6.0,
            "grid_2_height": 7.0,
            "grid_2_width": 8.0,
            "tangent_area_position": CharPointType.DIKE_TOE_LAND_SIDE,
            "tangent_area_offset": -2.0,
            "top_tangent_area": 0.5,
            "height_tangent_area": 10.0,
            "search_mode": OptionsType.DEFAULT,
        }

        constraints_dict = {
            "apply_minimum_slip_plane_dimensions": True,
            "minimum_slip_plane_depth": 2.5,
            "minimum_slip_plane_length": 5.0,
            "apply_constraint_zone_a": True,
            "zone_a_position": CharPointType.DIKE_CREST_LAND_SIDE,
            "zone_a_direction": Side.WATER_SIDE,
            "zone_a_width": 3.0,
            "apply_constraint_zone_b": False,
            "zone_b_position": None,
            "zone_b_direction": None,
            "zone_b_width": None,
        }

        self.bishop_dict = bishop_dict | constraints_dict
        self.uplift_dict = uplift_dict | constraints_dict

        self.raw_input = RawUserInput(
            settings={
                "min_soil_profile_depth": 10.0, 
                "execute_calculations": True,
                "apply_waternet": True,
                "calculate_l_coordinates": True,
                "output_dir": None
                },
            surface_lines={"Profile 1": [0, 0, 0, 1, 0, 1]},  # [x, y, z, x, y, z]
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
                "probabilistic_strength_parameters": True,
                "c_mean": 5.0,
                "c_std": 0.0,
                "phi_mean": 30.0,
                "phi_std": 1.0,
                "psi_mean": 1.0,
                "psi_std": 0.0,
                "shear_stress_ratio_s_mean": 0.25,
                "shear_stress_ratio_s_std": 0.02,
                "strength_exponent_m_mean": 0.8,
                "strength_exponent_m_std": 0.0,
                "probabilistic_pop": True,
                "pop_mean": 10.0,
                "pop_std": 1.0,
                "correlation_c-phi": False,
                "correlation_s-m": False,
                "consolidation_traffic_load": 50,
                "color": "#80336600",
                "pattern": PersistableShadingTypeEnum.DIAGONAL_A,
            }],
            soil_profiles={
                "Profile 1": [
                    {"soil_type": "Clay", "top": 1.0},
                ],
                "Profile 2": [
                    {"soil_type": "Sand", "top": 2.0},
                    {"soil_type": "Clay", "top": -2.0},
                ],
            },
            soil_profile_positions={
                "Calc 1": {
                    "Soil Profile 1": None,
                    "Soil Profile 2": 20,
                },
            },
            revetment_profile_blueprints={
                "Grasbekleding": [
                    {"revetment_profile_name": "Grasbekleding",
                    "from_char_point": CharPointType.DIKE_CREST_LAND_SIDE,
                    "to_char_point": CharPointType.DIKE_TOE_LAND_SIDE,
                    "thickness": 0.5,
                    "soil_type": "Clay",
                    }
                ]
            },
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
                            "type": WaterLineType.HEADLINE,
                            "line_name": "phreatic",
                            "values": [0, 2, 50, 1],
                        }]
                    }
                }
            },
            grid_settings={"Set 1": [self.bishop_dict]
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
                            "revetment_profile_name": "Grasbekleding",
                            "load_name": "Traffic",
                            "grid_settings_set_name": "Set 1",
                        }
                    ]
                }]
            }]
        )

    def test_convert_settings(self):
        """Test converting settings"""

        settings = RawInputToUserInputStructure.convert_settings(self.raw_input.settings)
        self.assertIsInstance(settings, GeneralSettings)
        self.assertEqual(settings.min_soil_profile_depth, 10.0)
        self.assertTrue(settings.execute_calculations)
        self.assertTrue(settings.apply_waternet)
        self.assertTrue(settings.calculate_l_coordinates)
        self.assertEqual(settings.output_dir, None)

    def test_convert_surface_lines(self):
        """Test converting surface lines"""

        surface_lines = RawInputToUserInputStructure.convert_surface_lines(self.raw_input.surface_lines)
        self.assertIsInstance(surface_lines, SurfaceLineCollection)
        self.assertEqual(len(surface_lines.surface_lines), 1)
        self.assertEqual(surface_lines.surface_lines[0].name, "Profile 1")
        self.assertEqual(len(surface_lines.surface_lines[0].points), 2)
        self.assertEqual(surface_lines.surface_lines[0].points[0], Point(x=0., y=0., z=0.))
        self.assertEqual(surface_lines.surface_lines[0].points[1], Point(x=1., y=0., z=1.))

    def test_convert_char_points(self):
        """Test converting characteristic points"""

        char_point_col = RawInputToUserInputStructure.convert_char_points(self.raw_input.char_points)
        self.assertIsInstance(char_point_col, CharPointsProfileCollection)
        self.assertEqual(len(char_point_col.char_points_profiles), 1)
        self.assertEqual(char_point_col.char_points_profiles[0].name, "Profile 1")
        self.assertEqual(char_point_col.char_points_profiles[0].points[0].type, CharPointType.SURFACE_LEVEL_WATER_SIDE)
        self.assertIsInstance(char_point_col.char_points_profiles[0].points[0], CharPoint)
        self.assertEqual(char_point_col.char_points_profiles[0].points[0].x, 0.)
        self.assertEqual(char_point_col.char_points_profiles[0].points[0].y, -1.)
        self.assertEqual(char_point_col.char_points_profiles[0].points[0].z, -2.)

    def test_convert_soil_collection(self):
        """Test converting soil collection"""

        soils = RawInputToUserInputStructure.convert_soil_collection(self.raw_input.soil_params)
        self.assertIsInstance(soils, SoilCollection)
        self.assertIsInstance(soils.soils[0], Soil)
        self.assertEqual(len(soils.soils), 1)
        soil = soils.soils[0]
        self.assertEqual(soil.gl_soil.name, "Clay")
        self.assertEqual(soil.gl_soil.soil_weight_parameters.unsaturated_weight, 16.0)
        self.assertEqual(soil.gl_soil.soil_weight_parameters.saturated_weight, 18.0)
        self.assertEqual(soil.gl_soil.shear_strength_model_above_phreatic_level,
                         ShearStrengthModelTypePhreaticLevel.MOHR_COULOMB)
        self.assertEqual(soil.gl_soil.shear_strength_model_below_phreatic_level,
                         ShearStrengthModelTypePhreaticLevel.MOHR_COULOMB)
        self.assertTrue(soil.gl_soil.is_probabilistic)
        self.assertFalse(soil.gl_soil.mohr_coulomb_parameters.cohesion.is_probabilistic)  # std set to 0, so should be deterministic
        self.assertEqual(soil.gl_soil.mohr_coulomb_parameters.cohesion.mean, 5.0)
        self.assertEqual(soil.gl_soil.mohr_coulomb_parameters.cohesion.standard_deviation, 0.0)
        self.assertTrue(soil.gl_soil.mohr_coulomb_parameters.friction_angle.is_probabilistic) # std has value, so should be probabilistic
        self.assertEqual(soil.gl_soil.mohr_coulomb_parameters.friction_angle.mean, 30.0)
        self.assertEqual(soil.gl_soil.mohr_coulomb_parameters.friction_angle.standard_deviation, 1.0)
        self.assertFalse(soil.gl_soil.mohr_coulomb_parameters.dilatancy_angle.is_probabilistic)
        self.assertEqual(soil.gl_soil.mohr_coulomb_parameters.dilatancy_angle.mean, 1.0)
        self.assertEqual(soil.gl_soil.mohr_coulomb_parameters.dilatancy_angle.standard_deviation, 0.0)
        self.assertEqual(soil.gl_soil.undrained_parameters.shear_strength_ratio.mean, 0.25)
        self.assertEqual(soil.gl_soil.undrained_parameters.shear_strength_ratio.standard_deviation, 0.02)
        self.assertTrue(soil.gl_soil.undrained_parameters.shear_strength_ratio.is_probabilistic)
        self.assertFalse(soil.gl_soil.undrained_parameters.strength_increase_exponent.is_probabilistic)
        self.assertEqual(soil.gl_soil.undrained_parameters.strength_increase_exponent.mean, 0.8)
        self.assertEqual(soil.gl_soil.undrained_parameters.strength_increase_exponent.standard_deviation, 0.0)
        self.assertTrue(soil.probabilistic_pop)
        self.assertEqual(soil.pop_mean, 10.0)
        self.assertEqual(soil.pop_std, 1.0)
        self.assertFalse(soil.gl_soil.mohr_coulomb_parameters.cohesion_and_friction_angle_correlated)
        self.assertFalse(soil.gl_soil.undrained_parameters.shear_strength_ratio_and_shear_strength_exponent_correlated)
        self.assertEqual(soil.consolidation_traffic_load, 50.)

    def test_convert_soil_collection_duplicate_names(self):
        """Test converting soil collection with duplicate names"""

        soil_dicts = self.raw_input.soil_params * 2

        with self.assertRaises(ValueError):
            RawInputToUserInputStructure.convert_soil_collection(soil_dicts)

    def test_convert_soil_collection_missing_keys(self):
        """Test converting soil collection with duplicate names"""

        soils_dicts = [
            {
                "name": "soil1",
            }
        ]

        with self.assertRaises(ValueError):
            RawInputToUserInputStructure.convert_soil_collection(soils_dicts)

    def test_convert_soil_profile_collection(self):
        """Test converting soil profile collection"""

        profiles = RawInputToUserInputStructure.convert_soil_profile_collection(self.raw_input.soil_profiles)
        self.assertIsInstance(profiles, SoilProfileCollection)
        self.assertEqual(len(profiles.profiles), 2)
        soil_profile = profiles.profiles[0]
        self.assertIsInstance(soil_profile, SoilProfile)
        self.assertEqual(soil_profile.name, "Profile 1")
        self.assertEqual(len(soil_profile.layers), 1)
        self.assertEqual(soil_profile.layers[0].soil_type, "Clay")
        self.assertEqual(soil_profile.layers[0].top, 1.0)

    def test_convert_soil_profile_positions(self):
        """Test converting soil profile positions"""
        positions = RawInputToUserInputStructure.convert_soil_profile_positions(self.raw_input.soil_profile_positions)
        self.assertIsInstance(positions, SoilProfilePositionSetCollection)
        self.assertEqual(len(positions.sets), 1)
        position_set = positions.sets[0]
        self.assertIsInstance(position_set, SoilProfilePositionSet)
        self.assertEqual(position_set.set_name, "Calc 1")
        self.assertEqual(len(position_set.soil_profile_positions), 2)
        position = position_set.soil_profile_positions[0]
        self.assertIsInstance(position, SoilProfilePosition)
        self.assertEqual(position.profile_name, "Soil Profile 1")
        self.assertEqual(position.l_coord, None)
        position = position_set.soil_profile_positions[1]
        self.assertEqual(position.profile_name, "Soil Profile 2")
        self.assertEqual(position.l_coord, 20)

    def test_convert_revetment_profile_blueprint_collection(self):
        """Test converting revetment profile blueprint collection"""

        revetment_profile_blueprints = RawInputToUserInputStructure.convert_revetment_profile_blueprint_collection(
            self.raw_input.revetment_profile_blueprints
            )
        self.assertIsInstance(revetment_profile_blueprints, RevetmentProfileBlueprintCollection)
        self.assertEqual(len(revetment_profile_blueprints.profile_blueprints), 1)
        revetment_profile_blueprint = revetment_profile_blueprints.profile_blueprints[0]
        self.assertIsInstance(revetment_profile_blueprint, RevetmentProfileBlueprint)
        self.assertEqual(revetment_profile_blueprint.name, "Grasbekleding")
        revetment_layer = revetment_profile_blueprint.layer_blueprints[0]
        self.assertIsInstance(revetment_layer, RevetmentLayerBlueprint)
        self.assertEqual(revetment_layer.soil_type, "Clay")
        self.assertEqual(revetment_layer.thickness, 0.5)
        self.assertCountEqual(revetment_layer.char_point_types, (CharPointType.DIKE_CREST_LAND_SIDE, CharPointType.DIKE_TOE_LAND_SIDE))

    def test_convert_loads(self):
        """Test converting loads"""

        loads = RawInputToUserInputStructure.convert_loads(self.raw_input.loads)
        self.assertIsInstance(loads, LoadCollection)
        self.assertEqual(len(loads.loads), 1)
        load = loads.loads[0]
        self.assertIsInstance(load, Load)
        self.assertEqual(load.name, "Traffic")
        self.assertEqual(load.magnitude, 13.0)
        self.assertEqual(load.position, CharPointType.DIKE_CREST_LAND_SIDE)
        self.assertEqual(load.direction, Side.WATER_SIDE)

    def test_convert_waternet_collection(self):
        """Test converting waternet collection"""

        waternets = RawInputToUserInputStructure.convert_waternet_collection(
            self.raw_input.hydraulic_pressure,
            name_phreatic_line="phreatic"
        )
        self.assertIsInstance(waternets, WaternetCollection)
        self.assertEqual(len(waternets.waternets), 1)
        waternet = waternets.waternets[0]
        self.assertIsInstance(waternet, Waternet)
        self.assertEqual(waternet.calc_name, "calc1")
        self.assertEqual(waternet.scenario_name, "scenario1")
        self.assertEqual(waternet.stage_name, "stage1")
        self.assertEqual(len(waternet.head_lines), 1)
        head_line = waternet.head_lines[0]
        self.assertIsInstance(head_line, HeadLine)
        self.assertEqual(head_line.l, [0, 50])
        self.assertEqual(head_line.z, [2, 1])
        self.assertTrue(head_line.is_phreatic)
        self.assertEqual(head_line.name, "phreatic")

    def test_convert_waternet_collection_empty_lines(self):
        """Test creating a collection with empty lines list"""
        empty_dict = {"calc1": {"scenario1": {"stage1": []}}}

        collection = RawInputToUserInputStructure.convert_waternet_collection(
            empty_dict, name_phreatic_line="headline1"
        )
        waternet = collection.waternets[0]
        self.assertEqual(len(waternet.head_lines), 0)
        self.assertEqual(len(waternet.ref_lines), 0)

    def test_from_dict_uplift_van_particle_swarm(self):
        grid_settings = RawInputToUserInputStructure.grid_settings_from_dict(
            self.uplift_dict
            )

        self.assertIsInstance(grid_settings, UpliftVanParticleSwarm)

    def test_from_dict_bishop_brute_force(self):
        grid_settings = RawInputToUserInputStructure.grid_settings_from_dict(
            self.bishop_dict
            )
        self.assertIsInstance(grid_settings, BishopBruteForce)

    def test_from_dict_incomplete_constraints_input(self):
        self.bishop_dict["minimum_slip_plane_depth"] = None

        with self.assertRaises(ValueError):
            RawInputToUserInputStructure.grid_settings_from_dict(self.bishop_dict)

    def test_grid_settings_from_dict_unknown_slip_plane_model(self):
        input_dict = {"slip_plane_model": "unknown"}

        with self.assertRaises(ValueError):
            RawInputToUserInputStructure.grid_settings_from_dict(input_dict)


    def test_convert_grid_settings_set_collection(self):
        """Test converting grid settings set collection"""
        grid_setting_set_collection = RawInputToUserInputStructure.convert_grid_settings_set_collection(
            self.raw_input.grid_settings
        )
        self.assertIsInstance(grid_setting_set_collection, GridSettingsSetCollection)
        self.assertEqual(len(grid_setting_set_collection.grid_settings_sets), 1)
        grid_setting_set = grid_setting_set_collection.grid_settings_sets[0]
        self.assertEqual(grid_setting_set.name, "Set 1")
        self.assertEqual(len(grid_setting_set.grid_settings), 1)
        grid_setting = grid_setting_set.grid_settings[0]
        self.assertIsInstance(grid_setting, BishopBruteForce)
        self.assertEqual(grid_setting.grid_setting_name, "Bishop")
        self.assertEqual(grid_setting.slip_plane_model, SlipPlaneModel.BISHOP_BRUTE_FORCE)
        self.assertEqual(grid_setting.grid_position, CharPointType.DIKE_CREST_LAND_SIDE)
        self.assertEqual(grid_setting.grid_direction, Side.LAND_SIDE)
        self.assertEqual(grid_setting.grid_offset_horizontal, 1)
        self.assertEqual(grid_setting.grid_offset_vertical, 2)
        self.assertEqual(grid_setting.grid_points_horizontal, 10)
        self.assertEqual(grid_setting.grid_points_vertical, 11)
        self.assertEqual(grid_setting.grid_points_per_m, 2)
        self.assertEqual(grid_setting.tangent_line_position, CharPointType.DIKE_TOE_LAND_SIDE)
        self.assertEqual(grid_setting.tangent_line_offset, -1.0)
        self.assertEqual(grid_setting.tangent_line_count, 12)
        self.assertEqual(grid_setting.tangent_lines_per_m, 3)
        self.assertTrue(grid_setting.move_grid)

    def test_convert_model_configs(self):
        """Test converting model configs"""
        configs = RawInputToUserInputStructure.convert_model_configs(self.raw_input.model_configs)
        self.assertIsInstance(configs, list)
        self.assertEqual(len(configs), 1)
        config = configs[0]
        self.assertIsInstance(config, ModelConfig)
        self.assertEqual(config.calc_name, "Calc 1")
        self.assertEqual(len(config.scenarios), 1)
        scenario = config.scenarios[0]
        self.assertIsInstance(scenario, ScenarioConfig)
        self.assertEqual(scenario.scenario_name, "Scenario 1")
        self.assertEqual(len(scenario.stages), 1)
        self.assertEqual(scenario.grid_settings_set_name, "Set 1")

        stage = scenario.stages[0]
        self.assertIsInstance(stage, StageConfig)
        self.assertEqual(stage.stage_name, "Stage 1")
        self.assertTrue(stage.apply_state_points)
        self.assertEqual(stage.geometry_name, "Profile 1")
        self.assertEqual(stage.soil_profile_position_name, "Calc 1")
        self.assertEqual(stage.revetment_profile_name, "Grasbekleding")
        self.assertEqual(stage.load_name, "Traffic")

    def test_convert(self):
        """Integral test"""

        user_input_structure = RawInputToUserInputStructure.convert(self.raw_input)
        self.assertIsInstance(user_input_structure, UserInputStructure)
