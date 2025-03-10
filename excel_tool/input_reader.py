"""
Reads the input file
"""

from pathlib import Path
from typing import Any

import openpyxl
from geolib.models.dstability.internal import OptionsType
from geolib.soils.soil import ShearStrengthModelTypePhreaticLevel, Soil as GLSoil           
from pydantic import BaseModel

from dstability_toolbox.geometry import (CharPointsProfileCollection,
                                         CharPointType, Side,
                                         SurfaceLine, SurfaceLineCollection,
                                         CharPointsProfile)
from dstability_toolbox.loads import LoadCollection, Load
from dstability_toolbox.soils import SoilCollection, Soil
from dstability_toolbox.subsoil import SoilProfileCollection, SoilLayer, SoilProfile
from dstability_toolbox.water import WaterLineType, WaternetCollection, HeadLine, ReferenceLine, Waternet
from dstability_toolbox.calculation_settings import (GridSettingsSetCollection,
                                                     GridSettingsSet,
                                                     SlipPlaneModel,
                                                     UpliftVanParticleSwarm,
                                                     BishopBruteForce)
from excel_tool.excel_utils import (parse_key_row, parse_key_value_cols,
                                    parse_row_instance,
                                    parse_row_instance_remainder)
from excel_tool.user_input import (GeneralSettings, UserInputStructure,
                                   ModelConfig)
from utils.dict_utils import (group_dicts_by_key, list_to_nested_dict,
                              remove_key, check_for_missing_keys)
from utils.list_utils import (check_list_of_dicts_for_duplicate_values,
                              unique_in_order)

INPUT_SHEETS = {
    "settings": "Instellingen",
    "surface_lines": "Dwarsprofielen",
    "char_points": "Kar. punten",
    "soil_params": "Sterkteparameters",
    "soil_profiles": "Bodemprofielen",
    "soil_profile_positions": "Bodemopbouw",
    "loads": "Belasting",
    "hydraulic_pressure": "Waterspanningsschematisatie",
    "grid_settings": "Gridinstellingen",
    "model_configs": "Berekeningen",
}

SETTINGS_COLS = {"setting": "Instelling", "value": "Waarde"}

SETTINGS_NAMES = {
    "Minimale diepte ondergrond": "min_soil_profile_depth",
    "Rekenen": "execute_calculations",
}

CHAR_POINT_COLS = {
    "name": "LOCATIONID",
    "x_surface_level_water_side": "X_Maaiveld buitenwaarts",
    "y_surface_level_water_side": "Y_Maaiveld buitenwaarts",
    "z_surface_level_water_side": "Z_Maaiveld buitenwaarts",
    "x_toe_canal": "X_Teen geul",
    "y_toe_canal": "Y_Teen geul",
    "z_toe_canal": "Z_Teen geul",
    "x_start_canal": "X_Insteek geul",
    "y_start_canal": "Y_Insteek geul",
    "z_start_canal": "Z_Insteek geul",
    "x_dike_toe_water_side": "X_Teen dijk buitenwaarts",
    "y_dike_toe_water_side": "Y_Teen dijk buitenwaarts",
    "z_dike_toe_water_side": "Z_Teen dijk buitenwaarts",
    "x_berm_crest_water_side": "X_Kruin buitenberm",
    "y_berm_crest_water_side": "Y_Kruin buitenberm",
    "z_berm_crest_water_side": "Z_Kruin buitenberm",
    "x_berm_start_water_side": "X_Insteek buitenberm",
    "y_berm_start_water_side": "Y_Insteek buitenberm",
    "z_berm_start_water_side": "Z_Insteek buitenberm",
    "x_dike_crest_water_side": "X_Kruin buitentalud",
    "y_dike_crest_water_side": "Y_Kruin buitentalud",
    "z_dike_crest_water_side": "Z_Kruin buitentalud",
    "x_traffic_load_water_side": "X_Verkeersbelasting kant buitenwaarts",
    "y_traffic_load_water_side": "Y_Verkeersbelasting kant buitenwaarts",
    "z_traffic_load_water_side": "Z_Verkeersbelasting kant buitenwaarts",
    "x_traffic_load_land_side": "X_Verkeersbelasting kant binnenwaarts",
    "y_traffic_load_land_side": "Y_Verkeersbelasting kant binnenwaarts",
    "z_traffic_load_land_side": "Z_Verkeersbelasting kant binnenwaarts",
    "x_dike_crest_land_side": "X_Kruin binnentalud",
    "y_dike_crest_land_side": "Y_Kruin binnentalud",
    "z_dike_crest_land_side": "Z_Kruin binnentalud",
    "x_berm_start_land_side": "X_Insteek binnenberm",
    "y_berm_start_land_side": "Y_Insteek binnenberm",
    "z_berm_start_land_side": "Z_Insteek binnenberm",
    "x_berm_crest_land_side": "X_Kruin binnenberm",
    "y_berm_crest_land_side": "Y_Kruin binnenberm",
    "z_berm_crest_land_side": "Z_Kruin binnenberm",
    "x_dike_toe_land_side": "X_Teen dijk binnenwaarts",
    "y_dike_toe_land_side": "Y_Teen dijk binnenwaarts",
    "z_dike_toe_land_side": "Z_Teen dijk binnenwaarts",
    "x_ditch_start_water_side": "X_Insteek sloot dijkzijde",
    "y_ditch_start_water_side": "Y_Insteek sloot dijkzijde",
    "z_ditch_start_water_side": "Z_Insteek sloot dijkzijde",
    "x_ditch_bottom_water_side": "X_Slootbodem dijkzijde",
    "y_ditch_bottom_water_side": "Y_Slootbodem dijkzijde",
    "z_ditch_bottom_water_side": "Z_Slootbodem dijkzijde",
    "x_ditch_bottom_land_side": "X_Slootbodem polderzijde",
    "y_ditch_bottom_land_side": "Y_Slootbodem polderzijde",
    "z_ditch_bottom_land_side": "Z_Slootbodem polderzijde",
    "x_ditch_start_land_side": "X_Insteek sloot polderzijde",
    "y_ditch_start_land_side": "Y_Insteek sloot polderzijde",
    "z_ditch_start_land_side": "Z_Insteek sloot polderzijde",
    "x_surface_level_land_side": "X_Maaiveld binnenwaarts",
    "y_surface_level_land_side": "Y_Maaiveld binnenwaarts",
    "z_surface_level_land_side": "Z_Maaiveld binnenwaarts",
}

SOIL_COLS = {
    "name": "Naam",
    "unsaturated_weight": "Onverzadigd gewicht",
    "saturated_weight": "Verzadigd gewicht",
    "strength_model_above": "Sterktemodel boven",
    "strength_model_below": "Sterktemodel onder",
    "c": "Cohesie c",
    "phi": "Wrijvingshoek φ",
    "shear_stress_ratio_s": "Schuifspanningsratio S",
    "strength_exponent_m": "Sterkte-exponent m",
    "pop": "POP",
    "consolidation_traffic_load": "Consolidatie belasting",
}

SOIL_PROFILE_COLS = {
    "name": "Naam grondprofiel",
    "soil_type": "Grondsoort",
    "top": "Bovenkant",
}

LOAD_COLS = {
    "name": "Naam belasting",
    "magnitude": "Grootte",
    "angle": "Spreiding",
    "width": "Breedte",
    "position": "Positie",
    "direction": "Richting",
}

HYDRAULIC_PRESSURE_COLS = {
    "calc_name": "Berekening",
    "scenario": "Scenario",
    "stage": "Stage",
    "type": "Type",
    "line_name": "Naam",
    "head_line_top": "PL-lijn bovenzijde",
    "head_line_bottom": "PL-lijn onderzijde",
}

GRID_SETTINGS_COLS = {
    "name_set": "Naam set",
    "grid_setting_name": "Naam gridinstelling",
    "slip_plane_model": "Model",
    "grid_position": "Positie grid",
    "grid_direction": "Richting grid",
    "grid_offset_horizontal": "Offset grid horizontaal",
    "grid_offset_vertical": "Offset grid verticaal",
    "grid_points_horizontal": "Aantal gridpunten horizontaal",
    "grid_points_vertical": "Aantal gridpunten verticaal",
    "grid_points_per_m": "Dichtheid gridpunten",
    "bottom_tangent_line": "Onderste tangentlijn",
    "tangent_line_count": "Aantal tangentlijnen",
    "tangent_lines_per_m": "Dichtheid tangentlijnen",
    "move_grid": "Grid verplaatsen",
    "grid_1_position": "Positie grid 1",
    "grid_1_direction": "Richting grid 1",
    "grid_1_offset_horizontal": "Offset horizontaal grid 1",
    "grid_1_offset_vertical": "Offset verticaal grid 1",
    "grid_1_width": "Breedte grid 1",
    "grid_1_height": "Hoogte grid 1",
    "grid_2_position": "Positie grid 2",
    "grid_2_direction": "Richting grid 2",
    "grid_2_offset_horizontal": "Offset horizontaal grid 2",
    "grid_2_offset_vertical": "Offset verticaal grid 2",
    "grid_2_height": "Hoogte grid 2",
    "grid_2_width": "Breedte grid 2",
    "top_tangent_area": "Bovenzijde tangentvlak",
    "height_tangent_area": "Hoogte tangentvlak",
    "search_mode": "Zoekmodus",
    "apply_minimum_slip_plane_dimensions": "Minimale glijvlakdimensies toepassen",
    "minimum_slip_plane_depth": "Minimale glijvlakdiepte",
    "minimum_slip_plane_length": "Minimale glijvlaklengte",
    "apply_constraint_zone_a": "In-/uittredezone A toepassen",
    "zone_a_position": "Positie zone A",
    "zone_a_direction": "Richting zone A",
    "zone_a_width": "Breedte zone A",
    "apply_constraint_zone_b": "In-/uittredezone B toepassen",
    "zone_b_position": "Positie zone B",
    "zone_b_direction": "Richting zone B",
    "zone_b_width": "Breedte zone B",
}

CALCULATION_COLS = {
    "calc_name": "Naam",
    "scenario_name": "Scenario",
    "stage_name": "Stage",
    "geometry_name": "Geometrie",
    "soil_profile_position_name": "Bodemopbouw",
    "apply_state_points": "State points toepassen",
    "load_name": "Belasting",
    "grid_settings_set_name": "Glijvlakinstellingen",
    "evaluate": "Berekenen",
}

INPUT_TO_BOOL = {
    "Ja": True,
    "Nee": False,
}

INPUT_TO_CHAR_POINTS = {
    "Maaiveld buitenwaarts": CharPointType.SURFACE_LEVEL_WATER_SIDE,
    "Teen geul": CharPointType.TOE_CANAL,
    "Insteek geul": CharPointType.START_CANAL,
    "Teen dijk buitenwaarts": CharPointType.DIKE_TOE_WATER_SIDE,
    "Kruin buitenberm": CharPointType.BERM_CREST_WATER_SIDE,
    "Insteek buitenberm": CharPointType.BERM_START_WATER_SIDE,
    "Kruin buitentalud": CharPointType.DIKE_CREST_WATER_SIDE,
    "Verkeersbelasting kant buitenwaarts": CharPointType.TRAFFIC_LOAD_WATER_SIDE,
    "Verkeersbelasting kant binnenwaarts": CharPointType.TRAFFIC_LOAD_LAND_SIDE,
    "Kruin binnentalud": CharPointType.DIKE_CREST_LAND_SIDE,
    "Insteek binnenberm": CharPointType.BERM_START_LAND_SIDE,
    "Kruin binnenberm": CharPointType.BERM_CREST_LAND_SIDE,
    "Teen dijk binnenwaarts": CharPointType.DIKE_TOE_LAND_SIDE,
    "Insteek sloot dijkzijde": CharPointType.DITCH_START_WATER_SIDE,
    "Slootbodem dijkzijde": CharPointType.DITCH_BOTTOM_WATER_SIDE,
    "Slootbodem polderzijde": CharPointType.DITCH_BOTTOM_LAND_SIDE,
    "Insteek sloot polderzijde": CharPointType.DITCH_START_LAND_SIDE,
    "Maaiveld binnenwaarts": CharPointType.SURFACE_LEVEL_LAND_SIDE,
}

INPUT_TO_SIDE = {
    "Binnenwaarts": Side.LAND_SIDE,
    "Buitenwaarts": Side.WATER_SIDE,
}

INPUT_TO_WATER_LINE_TYPE = {
    "Stijghoogtelijn": WaterLineType.HEADLINE,
    "Referentielijn": WaterLineType.REFERENCE_LINE,
}

INPUT_TO_SLIP_PLANE_MODEL = {
    "Uplift Van": SlipPlaneModel.UPLIFT_VAN_PARTICLE_SWARM,
    "Bishop": SlipPlaneModel.BISHOP_BRUTE_FORCE,
}

INPUT_TO_SEARCH_MODE = {
    "Normal": OptionsType.DEFAULT,
    "Thorough": OptionsType.THOROUGH,
}

NAME_PHREATIC_LINE = "Freatisch"


class RawUserInput(BaseModel):
    """Represents the raw user input"""

    settings: dict[str, str | float]
    surface_lines: dict[str, list[float]]
    char_points: dict[str, dict[str, float]]
    soil_params: list[dict[str, float | str | None]]
    soil_profiles: dict[str, list]
    soil_profile_positions: dict[str, dict[str, float | None]]
    loads: list[dict]
    hydraulic_pressure: dict
    grid_settings: dict[str, list]
    model_configs: list[dict]


class ExcelInputReader(BaseModel):
    """Represents the Input Excel file"""

    @staticmethod
    def read_from_file(file_path: str | Path) -> RawUserInput:
        """Creates an instance from an input file"""

        workbook = openpyxl.load_workbook(file_path, data_only=True, read_only=True)

        return RawUserInput(
            settings=ExcelInputReader.parse_settings(workbook),
            surface_lines=ExcelInputReader.parse_surface_lines(workbook),
            char_points=ExcelInputReader.parse_char_points(workbook),
            soil_params=ExcelInputReader.parse_soil_params(workbook),
            soil_profiles=ExcelInputReader.parse_soil_profiles(workbook),
            soil_profile_positions=ExcelInputReader.parse_soil_profile_positions(workbook),
            loads=ExcelInputReader.parse_loads(workbook),
            hydraulic_pressure=ExcelInputReader.parse_hydraulic_pressure(workbook),
            grid_settings=ExcelInputReader.parse_grid_settings(workbook),
            model_configs=ExcelInputReader.parse_model_configs(workbook),
        )

    @staticmethod
    def parse_settings(workbook: Any) -> dict[str, str | float]:
        settings = parse_key_value_cols(
            sheet=workbook[INPUT_SHEETS["settings"]],
            header_row=1,
            skip_rows=1,
            key_col="setting",
            value_col="value",
            col_dict=SETTINGS_COLS,
            key_dict=SETTINGS_NAMES,
        )
        settings["execute_calculations"] = INPUT_TO_BOOL[
            settings["execute_calculations"]
        ]
        return settings

    @staticmethod
    def parse_surface_lines(workbook: Any) -> dict[str, list[float]]:
        surface_lines = parse_key_row(
            sheet=workbook[INPUT_SHEETS["surface_lines"]], skip_rows=1
        )
        return surface_lines

    @staticmethod
    def parse_char_points(workbook: Any) -> dict[str, dict[str, float]]:
        char_points = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["char_points"]],
            header_row=1,
            skip_rows=1,
            col_dict=CHAR_POINT_COLS,
        )
        check_list_of_dicts_for_duplicate_values(
            char_points, "name"
        )  # Check uniqueness of names
        char_points = {
            char_dict["name"]: remove_key(char_dict, "name")
            for char_dict in char_points
        }
        return char_points

    @staticmethod
    def parse_soil_params(workbook: Any) -> list[dict[str, float | str | None]]:
        soil_params = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["soil_params"]],
            header_row=1,
            skip_rows=2,
            col_dict=SOIL_COLS,
        )
        return soil_params

    @staticmethod
    def parse_soil_profiles(workbook: Any) -> dict[str, list]:
        soil_profiles = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["soil_profiles"]],
            header_row=1,
            skip_rows=2,
            col_dict=SOIL_PROFILE_COLS,
        )
        soil_profiles = group_dicts_by_key(soil_profiles, group_by_key="name")
        return soil_profiles

    @staticmethod
    def parse_soil_profile_positions(
        workbook: Any,
    ) -> dict[str, dict[str, float | None]]:
        soil_profile_positions_raw = parse_key_row(
            sheet=workbook[INPUT_SHEETS["soil_profile_positions"]],
            skip_rows=2,
        )
        # Process soil profile positions
        soil_profile_positions = {}

        for name, value_list in soil_profile_positions_raw.items():
            # The first does not have a coordinate
            positions = {value_list.pop(0): None}

            for profile_name, l in zip(value_list[::2], value_list[1::2]):
                positions[profile_name] = l

            soil_profile_positions[name] = positions

        return soil_profile_positions

    @staticmethod
    def parse_loads(workbook: Any):
        loads = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["loads"]],
            header_row=1,
            skip_rows=2,
            col_dict=LOAD_COLS,
        )

        for line_dict in loads:
            line_dict["direction"] = INPUT_TO_SIDE.get(line_dict["direction"])
            line_dict["position"] = INPUT_TO_CHAR_POINTS.get(line_dict["position"])

        return loads

    @staticmethod
    def parse_hydraulic_pressure(workbook: Any):
        hydraulic_pressure = parse_row_instance_remainder(
            sheet=workbook[INPUT_SHEETS["hydraulic_pressure"]],
            header_row=1,
            skip_rows=3,
            col_dict=HYDRAULIC_PRESSURE_COLS,
            key_remainder="values",
        )

        # Preprocess hydraulic_pressure
        for line_dict in hydraulic_pressure:
            line_dict["type"] = INPUT_TO_WATER_LINE_TYPE.get(line_dict["type"])

        # Create structured dict {calc_name: {scenario: {stage: {...}}}}
        hydraulic_pressure = list_to_nested_dict(
            hydraulic_pressure,
            keys=["calc_name", "scenario", "stage"],
            remove_group_key=True,
        )
        return hydraulic_pressure

    @staticmethod
    def parse_grid_settings(workbook: Any) -> dict[str, list]:
        grid_settings = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["grid_settings"]],
            header_row=2,
            skip_rows=4,
            col_dict=GRID_SETTINGS_COLS,
        )
        for line_dict in grid_settings:
            line_dict["slip_plane_model"] = INPUT_TO_SLIP_PLANE_MODEL.get(
                line_dict["slip_plane_model"]
            )
            line_dict["search_mode"] = INPUT_TO_SEARCH_MODE.get(line_dict["search_mode"])

            for key in [
                "grid_direction",
                "grid_1_direction",
                "grid_2_direction",
                "zone_a_direction",
                "zone_b_direction",
            ]:
                line_dict[key] = INPUT_TO_SIDE.get(line_dict[key])

            for key in [
                "grid_position",
                "grid_1_position",
                "grid_2_position",
                "zone_a_position",
                "zone_b_position",
            ]:
                line_dict[key] = INPUT_TO_CHAR_POINTS.get(line_dict[key])

            for key in [
                "move_grid",
                "apply_minimum_slip_plane_dimensions",
                "apply_constraint_zone_a",
                "apply_constraint_zone_b",
            ]:
                line_dict[key] = INPUT_TO_BOOL.get(line_dict[key])

        grid_settings = group_dicts_by_key(grid_settings, group_by_key="name_set")
        return grid_settings

    @staticmethod
    def parse_model_configs(workbook: Any) -> list[dict]:
        model_config_rows = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["model_configs"]],
            header_row=2,
            skip_rows=4,
            col_dict=CALCULATION_COLS,
        )

        # Preprocess model_configs
        for model_dict in model_config_rows:
            model_dict["apply_state_points"] = INPUT_TO_BOOL.get(
                model_dict["apply_state_points"]
            )

        calc_names = unique_in_order(
            [calc_row["calc_name"] for calc_row in model_config_rows]
        )
        model_configs = []

        # Create structured list [{calc_name: "name", "scenarios": [{"scenario_name": "name", "stages": {"stage_name":..
        for calc_name in calc_names:
            # Get all row of calculation calc_name
            calc_rows = [
                calc_row
                for calc_row in model_config_rows
                if calc_row["calc_name"] == calc_name
            ]
            scenario_names = unique_in_order(
                [row["scenario_name"] for row in calc_rows]
            )
            scenarios = []

            for scenario_name in scenario_names:
                # Get al rows belonging to the scenario
                scenario_rows = [
                    row for row in calc_rows if row["scenario_name"] == scenario_name
                ]
                grid_settings_set_name_list = [
                    row["grid_settings_set_name"]
                    for row in scenario_rows
                    if row["grid_settings_set_name"] is not None
                ]

                if len(grid_settings_set_name_list) > 1:
                    raise ValueError(
                        f"Calculation {calc_name} has more than one grid_settings_set_name for scenario {scenario_name}"
                    )

                elif len(grid_settings_set_name_list) == 1:
                    grid_settings_set_name = grid_settings_set_name_list[0]

                else:
                    grid_settings_set_name = None

                scenario = {
                    "scenario_name": scenario_name,
                    "stages": scenario_rows,
                    "grid_settings_set_name": grid_settings_set_name,
                }
                scenarios.append(scenario)

            model_configs.append({"calc_name": calc_name, "scenarios": scenarios})

        return model_configs


class RawInputToUserInputStructure:
    @staticmethod
    def convert(raw_input: ExcelInputReader) -> UserInputStructure:
        """Converts the raw user input into a UserInputStructure
        
        Args:
            raw_input: The raw user input

        Returns:
            The converted UserInputStructure"""

        return UserInputStructure(
            settings=RawInputToUserInputStructure.convert_settings(raw_input.settings),
            surface_lines=RawInputToUserInputStructure.convert_surface_lines(raw_input.surface_lines),
            char_points=RawInputToUserInputStructure.convert_char_points(raw_input.char_points),
            soils=RawInputToUserInputStructure.convert_soil_collection(raw_input.soil_params),
            soil_profiles=RawInputToUserInputStructure.convert_soil_profile_collection(raw_input.soil_profiles),
            soil_profile_positions=RawInputToUserInputStructure.convert_soil_profile_positions(
                raw_input.soil_profile_positions
            ),
            loads=RawInputToUserInputStructure.convert_loads(raw_input.loads),
            waternets=RawInputToUserInputStructure.convert_waternet_collection(
                raw_input.hydraulic_pressure, name_phreatic_line=NAME_PHREATIC_LINE
            ),
            grid_settings=RawInputToUserInputStructure.convert_grid_settings_set_collection(raw_input.grid_settings),
            model_configs=RawInputToUserInputStructure.convert_model_configs(raw_input.model_configs),
        )

    @staticmethod
    def convert_settings(settings: dict[str, str | float]) -> GeneralSettings:
        """Converts the settings into a GeneralSettings
        
        Args:
            settings: The settings

        Returns:
            The converted GeneralSettings"""
        
        return GeneralSettings.model_validate(settings)

    @staticmethod
    def convert_surface_lines(surface_lines_dict: dict[str, list[float]]) -> SurfaceLineCollection:
        """Parses the dictionary into a SurfaceLineCollection

        Args:
            surface_lines_dict (dict): The dictionary to parse. The keys should be the profile names
              and the values a flat list of points of that profile [x1, y1, z1, x2, y2, z2, ...]
        """

        surface_lines: list[SurfaceLine] = []

        for name, point_list in surface_lines_dict.items():
            surface_line = SurfaceLine.from_list(name=name, point_list=point_list)
            surface_lines.append(surface_line)

        return SurfaceLineCollection(surface_lines=surface_lines)

    @staticmethod
    def convert_char_points(char_points_dict: dict[str, dict[str, float]]) -> CharPointsProfileCollection:
        """Parses the dictionary into a CharPointsProfileCollection

        Args:
            char_points_dict: The dictionary to parse. The keys should be the
              profile names and the values dicts with the characteristic points,3
              for example {x_surface_level_water_side: 0, y_surface_level_water_side:
              0, z_surface_level_water_side: 0, ...}"""

        char_point_profiles: list[CharPointsProfile] = []

        for name, char_points in char_points_dict.items():
            char_points_profile = CharPointsProfile.from_dict(
                name=name, char_points_dict=char_points
            )
            char_point_profiles.append(char_points_profile)

        return CharPointsProfileCollection(char_points_profiles=char_point_profiles)

    @staticmethod
    def convert_soil_collection(soil_list: list[dict[str, float | str | None]]) -> SoilCollection:
        """Initiates a SoilCollection from a list of soil dictionaries.

        Each dict should have keys:
          name: str
          unsaturated_weight: float
          saturated_weight: float
          strength_model_above: Literal["Shansep", "Mohr-Coulomb", "Su Table"]
          strength_model_below: Literal["Shansep", "Mohr-Coulomb", "Su Table"]
          c: float
          phi: float
          shear_stress_ratio_s: float
          strength_exponent_m: float
          pop: float

        Args:
            soil_list: list of dictionaries with the soil properties
        """
        req_keys = [
            "name",
            "unsaturated_weight",
            "saturated_weight",
            "strength_model_above",
            "strength_model_below",
            "c",
            "phi",
            "shear_stress_ratio_s",
            "strength_exponent_m",
            "pop",
            "consolidation_traffic_load",
        ]

        strength_model = {
            "Shansep": ShearStrengthModelTypePhreaticLevel.SHANSEP,
            "Mohr-Coulomb": ShearStrengthModelTypePhreaticLevel.MOHR_COULOMB,
            "Su Table": ShearStrengthModelTypePhreaticLevel.SUTABLE,
        }

        soils: list[Soil] = []

        # Check that soil names are unique
        check_list_of_dicts_for_duplicate_values(soil_list, "name")

        for soil_dict in soil_list:
            # Check that all the required keys are present
            check_for_missing_keys(soil_dict, req_keys)

            gl_soil = GLSoil()
            gl_soil.name = soil_dict["name"]
            gl_soil.code = soil_dict["name"]
            gl_soil.soil_weight_parameters.unsaturated_weight = soil_dict[
                "unsaturated_weight"
            ]
            gl_soil.soil_weight_parameters.saturated_weight = soil_dict[
                "saturated_weight"
            ]
            gl_soil.shear_strength_model_above_phreatic_level = strength_model[
                soil_dict["strength_model_above"]
            ]
            gl_soil.shear_strength_model_below_phreatic_level = strength_model[
                soil_dict["strength_model_below"]
            ]
            gl_soil.mohr_coulomb_parameters.cohesion.mean = soil_dict["c"]
            gl_soil.mohr_coulomb_parameters.friction_angle.mean = soil_dict["phi"]
            gl_soil.undrained_parameters.shear_strength_ratio.mean = soil_dict[
                "shear_stress_ratio_s"
            ]
            gl_soil.undrained_parameters.strength_increase_exponent.mean = soil_dict[
                "strength_exponent_m"
            ]

            soil = Soil(
                gl_soil=gl_soil,
                pop=soil_dict["pop"],
                consolidation_traffic_load=soil_dict["consolidation_traffic_load"],
            )
            soils.append(soil)

        return SoilCollection(soils=soils)
    
    @staticmethod
    def convert_soil_profile_collection(soil_profile_dict: dict[str, list]) -> SoilProfileCollection:
        """Parses the dictionary into a SoilProfileCollection

        Args:
            soil_profile_dict: The dictionary to parse. The keys should be the
              profile names and the values a list of layer dictionaries"""

        profiles: list[SoilProfile] = []

        for name, layer_dicts in soil_profile_dict.items():
            layers = [
                SoilLayer.model_validate(layer_dict) for layer_dict in layer_dicts
            ]
            profiles.append(SoilProfile(name=name, layers=layers))

        return SoilProfileCollection(profiles=profiles)

    @staticmethod
    def convert_soil_profile_positions(soil_profile_positions_dict: dict[str, dict[str, float | None]]):
        # positions: list[SoilProfilePosition] = []

        # for name, l_coords in soil_profile_positions_dict.items():
        #     positions.append(SoilProfilePosition(name=name, l_coords=l_coords))
        # TODO: Omkatten naar SoilProfilePositionCollection

        return soil_profile_positions_dict

    @staticmethod
    def convert_loads(loads_dicts: list[dict[str, Any]]) -> LoadCollection:
        """Parses the dictionary into a LoadCollection

        Args:
            loads_dicts: List with load dicts to parse. The keys should match
              the Load attributes (name, magnitude, angle)."""
        
        loads = [Load.model_validate(load_dict) for load_dict in loads_dicts]

        return LoadCollection(loads=loads)
    
    @staticmethod
    def parse_head_lines(
        lines: list[dict[str, Any]], name_phreatic_line: str
    ) -> list[HeadLine]:
        """Parse the head lines from the dictionary

        Args:
            lines (list[dict[str, Any]]): The lines to parse
            name_phreatic_line (str): The name of the phreatic line

        Returns:
            The parsed head lines"""

        head_lines: list[HeadLine] = []
        for line in lines:
            if line["type"] == WaterLineType.HEADLINE:
                head_lines.append(
                    HeadLine(
                        name=line["line_name"],
                        is_phreatic=line["line_name"] == name_phreatic_line,
                        l=line["values"][0::2],
                        z=line["values"][1::2],
                    )
                )

        return head_lines

    @staticmethod
    def parse_ref_lines(lines: list[dict[str, Any]]) -> list[ReferenceLine]:
        ref_lines: list[ReferenceLine] = []

        for line in lines:
            if line["type"] == WaterLineType.REFERENCE_LINE:
                if line["head_line_top"] is None:
                    raise ValueError(
                        f"Head line top is not set for reference line {line['line_name']}"
                    )

                if line["head_line_bottom"] is None:
                    line["head_line_bottom"] = line["head_line_top"]

                ref_lines.append(
                    ReferenceLine(
                        name=line["line_name"],
                        l=line["values"][0::2],
                        z=line["values"][1::2],
                        head_line_top=line["head_line_top"],
                        head_line_bottom=line["head_line_bottom"],
                    )
                )

        return ref_lines

    @staticmethod
    def convert_waternet_collection(
        waternets_dict: dict[str, dict[str, dict[str, list[dict[str, Any]]]]], 
        name_phreatic_line: str
    ) -> WaternetCollection:
        """Parse dict to WaternetCollection

        Args:
            waternets_dict: Dictionary with structure {calc_name: {scenario: {stage: [line_dicts]}}}
            name_phreatic_line: The name of the phreatic line

        Returns:
            WaternetCollection: Collection of waternet objects"""

        waternets: list[Waternet] = []

        for calc_name, calc_dict in waternets_dict.items():
            for scenario_name, scenario_dict in calc_dict.items():
                for stage_name, lines in scenario_dict.items():
                    head_lines = RawInputToUserInputStructure.parse_head_lines(lines, name_phreatic_line)
                    ref_lines = RawInputToUserInputStructure.parse_ref_lines(lines)
                    waternets.append(
                        Waternet(
                            calc_name=calc_name,
                            scenario_name=scenario_name,
                            stage_name=stage_name,
                            head_lines=head_lines,
                            ref_lines=ref_lines,
                        )
                    )

        return WaternetCollection(waternets=waternets)

    @staticmethod
    def grid_settings_from_dict(grid_setting_dict: dict):
        """Returns an instance of the child class of GridSettings based
        on the slip plane model.

        Args:
            input_dict: The dictionary to parse. Should at least have the
              keys and values for the attributes needed for the specific
              slip plane model."""
        
        slip_plane_model_to_class = {
            SlipPlaneModel.UPLIFT_VAN_PARTICLE_SWARM: UpliftVanParticleSwarm,
            SlipPlaneModel.BISHOP_BRUTE_FORCE: BishopBruteForce,
        }

        slip_plane_model = grid_setting_dict["slip_plane_model"]
        class_ = slip_plane_model_to_class.get(slip_plane_model)

        if class_ is None:
            raise ValueError(f"Unknown slip plane model {slip_plane_model}")

        return class_.model_validate(grid_setting_dict)

    @staticmethod
    def convert_grid_settings_set_collection(
            grid_settings_dicts: dict[str, list[dict[str, Any]]]
    ) -> GridSettingsSetCollection:
        """Parses the dictionary into a GridSettingsSetCollection

        Args:
            grid_settings_dicts (dict): The dictionary to parse"""
        
        grid_settings_sets = []

        for set_name, grid_settings_list in grid_settings_dicts.items():
            grid_settings = [
                RawInputToUserInputStructure.grid_settings_from_dict(grid_settings_dict)
                for grid_settings_dict in grid_settings_list
            ]
            grid_settings_sets.append(
                GridSettingsSet(name=set_name, grid_settings=grid_settings)
            )

        return GridSettingsSetCollection(grid_settings_sets=grid_settings_sets)

    @staticmethod
    def convert_model_configs(model_config_list: list[dict]) -> list[ModelConfig]:
        return [
            ModelConfig.model_validate(model_config) for model_config in model_config_list
        ]
