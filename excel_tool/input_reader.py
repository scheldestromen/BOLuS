"""
Reads the input file
"""

from pathlib import Path
from typing import Any
import warnings

import openpyxl
from geolib.models.dstability.internal import OptionsType
from geolib.soils.soil import ShearStrengthModelTypePhreaticLevel, Soil as GLSoil
from geolib.models.dstability.internal import PersistableShadingTypeEnum
from pydantic import BaseModel

from toolbox.geometry import (CharPointsProfileCollection,
                              CharPointType, Side,
                              SurfaceLine, SurfaceLineCollection,
                              CharPointsProfile)
from toolbox.loads import LoadCollection, Load
from toolbox.soils import SoilCollection, Soil
from toolbox.subsoil import SoilProfileCollection, SoilLayer, SoilProfile, SoilProfilePosition, \
    SoilProfilePositionSet, SoilProfilePositionSetCollection, RevetmentLayerBlueprint, RevetmentProfileBlueprint, \
    RevetmentProfileBlueprintCollection
from toolbox.waternet import WaterLineType, HeadLine, ReferenceLine
from toolbox.waternet_creator import RefLevelType, OffsetType, LineOffsetMethodCollection, LineOffsetMethod, LineOffsetPoint
from toolbox.waternet_config import WaterLevelCollection, HeadLineMethodType, RefLineMethodType, WaterLevelConfig, \
    HeadLineConfig, ReferenceLineConfig, WaternetConfig, WaternetConfigCollection
from toolbox.calculation_settings import (GridSettingsSetCollection,
                                          GridSettingsSet,
                                          SlipPlaneModel,
                                          UpliftVanParticleSwarm,
                                          BishopBruteForce)
from excel_tool.excel_utils import (parse_key_row, parse_key_value_cols,
                                    parse_row_instance,
                                    parse_row_instance_remainder)
from toolbox.model_creator import GeneralSettings, ModelConfig, UserInputStructure
from utils.dict_utils import (group_dicts_by_key, list_to_nested_dict,
                              remove_key, check_for_missing_keys)
from utils.list_utils import (check_list_of_dicts_for_duplicate_values,
                              unique_in_order)


# Filter to suppress only the specific warning about Data Validation extension
warnings.filterwarnings("ignore", message="Data Validation extension is not supported and will be removed",
                        category=UserWarning, module=r"openpyxl(\.|$)")

INPUT_SHEETS = {
    "settings": "Instellingen",
    "surface_lines": "Dwarsprofielen",
    "char_points": "Kar. punten",
    "soil_params": "Sterkteparameters",
    "soil_profiles": "Bodemprofielen",
    "soil_profile_positions": "Bodemopbouw",
    "water_levels": "Waterstanden",
    "water_level_configs": "Waterspanningsscenario's",
    "headline_offset_methods": "Offset methodes",
    "head_line_configs": "Stijghoogtes",
    "ref_line_configs": "Referentielijnen",
    "revetment_profile_blueprints": "Bekleding",
    "loads": "Belasting",
    # "hydraulic_pressure": "Waterspanningen",
    "grid_settings": "Gridinstellingen",
    "model_configs": "Berekeningen",
}

SETTINGS_COLS = {"setting": "Instelling", "value": "Waarde"}

SETTINGS_NAMES = {
    "Dimensie geometrie": "calculate_l_coordinates",
    "Minimale diepte ondergrond": "min_soil_profile_depth",
    "Rekenen": "execute_calculations",
    "Uitvoermap": "output_dir",
}

REQUIRED_SETTINGS = [
    "calculate_l_coordinates",
    "min_soil_profile_depth",
    "execute_calculations",
]

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

REQUIRED_CHAR_POINT_COLS = CHAR_POINT_COLS.keys()

SOIL_COLS = {
    "name": "Naam grondsoort",
    "unsaturated_weight": "Onverzadigd gewicht",
    "saturated_weight": "Verzadigd gewicht",
    "strength_model_above": "Sterktemodel boven",
    "strength_model_below": "Sterktemodel onder",
    "probabilistic_strength_parameters": "Probabilistische sterkteparameters",
    "c_mean": "c gem.",
    "c_std": "c std",
    "phi_mean": "φ gem.",
    "phi_std": "φ std",
    "psi_mean": "ψ gem.",
    "psi_std": "ψ std",
    "shear_stress_ratio_s_mean": "S gem.",
    "shear_stress_ratio_s_std": "S std",
    "strength_exponent_m_mean": "m gem.",
    "strength_exponent_m_std": "m std",
    "probabilistic_pop": "Probabilistische POP",
    "pop_mean": "POP gem.",
    "pop_std": "POP std",
    "correlation_c-phi": "c-φ",
    "correlation_s-m": "S-m",
    "consolidation_traffic_load": "Consolidatie belasting",
    "color": "Kleur",
    "pattern": "Patroon",
}

REQUIRED_SOIL_COLS = [
    "name",
    "unsaturated_weight",
    "saturated_weight",
    "strength_model_above",
    "strength_model_below",
    "probabilistic_strength_parameters",
    "consolidation_traffic_load",
    "color",
    "pattern",
]

SOIL_PROFILE_COLS = {
    "name": "Naam bodemprofiel",
    "soil_type": "Grondsoort",
    "top": "Bovenkant",
    "is_aquifer": "Watervoerend",
}

REQUIRED_SOIL_PROFILE_COLS = [
    "name",
    "soil_type",
    "top",
]

WATER_LEVEL_LOCATION_NAME_COL = "Naam locatie"

WATER_LEVEL_CONFIG_NAME_COL = "Naam waterspanningsscenario"

HEADLINE_OFFSET_METHODS_COLS = {
    "name": "Naam methode",
    "char_point_type": "Karakteristiek punt",
    "ref_level": "Referentieniveau",
    "offset_value": "Offset / Verhang"
}

REQUIRED_HEADLINE_OFFSET_METHODS_COLS = HEADLINE_OFFSET_METHODS_COLS.keys()

HEAD_LINE_CONFIG_COLS = {
    "name_waternet_scenario": "Naam waterspanningsscenario",
    "name_head_line": "Naam PL-lijn",
    "is_phreatic": "Freatisch",
    "head_line_method_type": "Methode stijghoogte",
    "offset_method_name": "Offset methode",
    "interpolate_from_waternet_name": "Stijghoogte afleiden uit scenario",
    "apply_minimal_surface_line_offset": "Minimale offset met het maaiveld toepassen",
    "minimal_surface_line_offset": "Waarde minimale offset",
    "minimal_offset_from_point": "Minimale offset vanaf punt",
    "minimal_offset_to_point": "Minimale offset tot punt",
}

REQUIRED_HEAD_LINE_CONFIG_COLS = [
    "name_waternet_scenario",
    "name_head_line",
    "is_phreatic",
    "head_line_method_type",
]

REF_LINE_CONFIG_COLS = {
    "name_waternet_scenario": "Naam waterspanningsscenario",
    "name_ref_line": "Naam referentielijn",
    "name_head_line_top": "PL-lijn bovenzijde",
    "name_head_line_bottom": "PL-lijn onderzijde",
    "ref_line_method_type": "Plaatsing referentielijn",
    "offset_method_name": "Offset methode",
    "intrusion_from_ref_line": "Indringing vanaf referentielijn",
    "intrusion_length": "Indringingslengte",
}

REQUIRED_REF_LINE_CONFIG_COLS = [
    "name_waternet_scenario",
    "name_ref_line",
    "name_head_line_top",
    "ref_line_method_type",
]

REVERTMENT_PROFILE_COLS = {
    "revetment_profile_name": "Naam bekledingsprofiel",
    "from_char_point": "Vanaf punt",
    "to_char_point": "Tot punt",
    "thickness": "Dikte",
    "soil_type": "Grondsoort",
}

REQUIRED_REVERTMENT_PROFILE_COLS = REVERTMENT_PROFILE_COLS.keys()

LOAD_COLS = {
    "name": "Naam belasting",
    "magnitude": "Grootte",
    "angle": "Spreiding",
    "width": "Breedte",
    "position": "Positie",
    "direction": "Richting",
}

REQUIRED_LOAD_COLS = LOAD_COLS.keys()

# HYDRAULIC_PRESSURE_COLS = {
#     "calc_name": "Berekening",
#     "scenario": "Scenario",
#     "stage": "Stage",
#     "type": "Type",
#     "line_name": "Naam",
#     "head_line_top": "PL-lijn bovenzijde",
#     "head_line_bottom": "PL-lijn onderzijde",
# }

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
    "tangent_line_position": "Positie tangentlijnen",
    "tangent_line_offset": "Offset tangentlijnen verticaal",
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
    "tangent_area_position": "Positie tangentvlak",
    "tangent_area_offset": "Offset tangentvlak verticaal",
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

# The remaining parameters are conditional on the slip_plane_model and are excluded here
REQUIRED_GRID_SETTINGS_COLS = [
    "name_set",
    "grid_setting_name",
    "slip_plane_model",
]

CALCULATION_COLS = {
    "calc_name": "Naam",
    "scenario_name": "Scenario",
    "stage_name": "Stage",
    "geometry_name": "Geometrie",
    "soil_profile_position_name": "Bodemopbouw",
    "apply_state_points": "State points toepassen",
    "waternet_scenario_name": "Waterspanningsscenario",
    "revetment_profile_name": "Bekledingsprofiel",
    "load_name": "Belasting",
    "grid_settings_set_name": "Gridinstellingen",
}

REQUIRED_CALCULATION_COLS = [
    "calc_name",
    "scenario_name",
    "stage_name",
    "geometry_name",
    "soil_profile_position_name",
    "apply_state_points",
]

INPUT_TO_BOOL = {
    "Ja": True,
    "Nee": False,
}

INPUT_TO_CALCULATE_L_COORDINATES = {
    "2D": False,
    "3D": True,
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

INPUT_TO_HEAD_LINE_METHOD_TYPE = {
    "Offset methode": HeadLineMethodType.OFFSETS,
    "Afleiden uit ander scenario": HeadLineMethodType.INTERPOLATE_FROM_WATERNET,
}

INPUT_TO_REF_LINE_METHOD_TYPE = {
    "Offset methode": RefLineMethodType.OFFSETS,
    "Watervoerende laag": RefLineMethodType.AQUIFER,
    "Watervoerende tussenlaag": RefLineMethodType.INTERMEDIATE_AQUIFER,
    "Indringingslengte": RefLineMethodType.INTRUSION,
}

INPUT_TO_SLIP_PLANE_MODEL = {
    "Uplift Van": SlipPlaneModel.UPLIFT_VAN_PARTICLE_SWARM,
    "Bishop": SlipPlaneModel.BISHOP_BRUTE_FORCE,
}

INPUT_TO_SEARCH_MODE = {
    "Normal": OptionsType.DEFAULT,
    "Thorough": OptionsType.THOROUGH,
}

INPUT_TO_PATTERN = {
    "Stip fijn": PersistableShadingTypeEnum.DOT_A,
    "Stip matig": PersistableShadingTypeEnum.DOT_B,
    "Stip grof": PersistableShadingTypeEnum.DOT_C,
    "Stip zeer grof": PersistableShadingTypeEnum.DOT_D,
    "Horizontaal fijn": PersistableShadingTypeEnum.HORIZONTAL_A,
    "Horizontaal grof": PersistableShadingTypeEnum.HORIZONTAL_B,
    "Diagonaal 1 fijn": PersistableShadingTypeEnum.DIAGONAL_A,
    "Diagonaal 1 grof": PersistableShadingTypeEnum.DIAGONAL_B,
    "Diagonaal 2 fijn": PersistableShadingTypeEnum.DIAGONAL_C,
    "Diagonaal 2 grof": PersistableShadingTypeEnum.DIAGONAL_D,
}

NAME_PHREATIC_LINE = "Freatisch"

INPUT_TO_REF_LEVEL_TYPE = {
    "NAP": RefLevelType.NAP,
    "Maaiveld": RefLevelType.SURFACE_LEVEL,
    "Verhang t.o.v. voorgaand punt": RefLevelType.RELATED_TO_OTHER_POINT,
}


def check_required_input(
        input_dict: dict[str, Any],
        required_keys: list[str],
        sheet_name: str,
        key_ui_dict: dict[str, str],
        ) -> bool:
    """Checks if the required keys are present in the input dictionary"""

    for key in required_keys:
        if input_dict[key] is None:
            raise ValueError(f"Missing value for: '{key_ui_dict[key]}' in sheet: '{sheet_name}'")
        
    return True


class RawUserInput(BaseModel):
    """Represents the raw user input"""
    # TODO: Dit beter toelichten? Deze hoort hier eigenlijk niet thuis. Dit is niet specifiek Excel-gerelateerd.
    #  - Refactor, toelichting en type-hints uitwerken
    # TODO: Dit is wellicht een goede plek om de validatie van de input te doen.
    # TODO: De type hints zijn wel een beetje overdreven. Overwegen om dit naar Any te zetten

    settings: dict[str, str | float | bool | None]
    surface_lines: dict[str, list[float]]
    char_points: dict[str, dict[str, float]]
    soil_params: list[dict[str, float | str | bool | None]]
    soil_profiles: dict[str, list[dict[str, float | str | bool | None]]]
    soil_profile_positions: dict[str, dict[str, float | None]]
    water_levels: dict[str, dict[str, float | None]]
    water_level_configs: dict[str, dict[str, str | None]]
    headline_offset_methods: dict[str, list[dict[str, str | float | None]]]
    head_line_configs: dict[str, list[dict[str, str | bool | float | CharPointType | None]]]
    ref_line_configs: dict[str, list[dict[str, str | float | None]]]
    revetment_profile_blueprints: dict[str, list[dict[str, str | float]]]
    loads: list[dict[str, str | float | None]]
    # hydraulic_pressure: dict[str, list[dict[str, str | float | None]]]
    grid_settings: dict[str, list[dict[str, str | float | None]]]
    model_configs: list[dict[str, Any]]   # To nested to be of use here


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
            water_levels=ExcelInputReader.parse_water_levels(workbook),
            water_level_configs=ExcelInputReader.parse_water_level_configs(workbook),
            headline_offset_methods=ExcelInputReader.parse_headline_offset_methods(workbook),
            head_line_configs=ExcelInputReader.parse_head_line_configs(workbook),
            ref_line_configs=ExcelInputReader.parse_ref_line_configs(workbook),
            revetment_profile_blueprints=ExcelInputReader.parse_revetment_profile_blueprints(workbook),
            loads=ExcelInputReader.parse_loads(workbook),
            # hydraulic_pressure=ExcelInputReader.parse_hydraulic_pressure(workbook),
            grid_settings=ExcelInputReader.parse_grid_settings(workbook),
            model_configs=ExcelInputReader.parse_model_configs(workbook),
        )

    @staticmethod
    def parse_settings(workbook: Any) -> dict[str, str | float | bool | None]:
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
        settings["calculate_l_coordinates"] = INPUT_TO_CALCULATE_L_COORDINATES[
            settings["calculate_l_coordinates"]
        ]

        inverted_settings_names = {v: k for k, v in SETTINGS_NAMES.items()}

        check_required_input(settings, REQUIRED_SETTINGS, INPUT_SHEETS["settings"], inverted_settings_names)

        return settings

    @staticmethod
    def parse_surface_lines(workbook: Any) -> dict[str, list[float]]:
        surface_lines = parse_key_row(
            sheet=workbook[INPUT_SHEETS["surface_lines"]], skip_rows=1
        )

        # Check for duplicate names
        surface_line_names = surface_lines.keys()
        if len(surface_line_names) != len(set(surface_line_names)):
            raise ValueError(f"Duplicate surface line names found: {surface_line_names}.\n"
                             "Please ensure all surface line names are unique.")

        return surface_lines

    @staticmethod
    def parse_char_points(workbook: Any) -> dict[str, dict[str, float]]:
        char_points = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["char_points"]],
            header_row=1,
            skip_rows=1,
            col_dict=CHAR_POINT_COLS,
        )
        check_list_of_dicts_for_duplicate_values(char_points, "name")

        char_points = {
            char_dict["name"]: remove_key(char_dict, "name")
            for char_dict in char_points
        }
        return char_points

    @staticmethod
    def parse_soil_params(workbook: Any) -> list[dict[str, float | str | bool | None]]:
        soil_params = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["soil_params"]],
            header_row=2,
            skip_rows=3,
            col_dict=SOIL_COLS,
        )
        check_list_of_dicts_for_duplicate_values(soil_params, "name")

        for soil_param in soil_params:
            soil_param["pattern"] = INPUT_TO_PATTERN.get(soil_param["pattern"])
            soil_param["probabilistic_strength_parameters"] = INPUT_TO_BOOL.get(
                soil_param["probabilistic_strength_parameters"])
            soil_param["probabilistic_pop"] = INPUT_TO_BOOL.get(soil_param["probabilistic_pop"])
            soil_param["correlation_c-phi"] = INPUT_TO_BOOL.get(soil_param["correlation_c-phi"])
            soil_param["correlation_s-m"] = INPUT_TO_BOOL.get(soil_param["correlation_s-m"])

            check_required_input(soil_param, REQUIRED_SOIL_COLS, INPUT_SHEETS["soil_params"], SOIL_COLS)

        return soil_params

    @staticmethod
    def parse_soil_profiles(workbook: Any) -> dict[str, list]:
        soil_profiles = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["soil_profiles"]],
            header_row=1,
            skip_rows=2,
            col_dict=SOIL_PROFILE_COLS,
        )
        for soil_profile in soil_profiles:
            soil_profile["is_aquifer"] = INPUT_TO_BOOL.get(soil_profile["is_aquifer"])

            check_required_input(soil_profile, REQUIRED_SOIL_PROFILE_COLS, INPUT_SHEETS["soil_profiles"], SOIL_PROFILE_COLS)

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
        # Check for duplicate names
        soil_profile_names = soil_profile_positions_raw.keys()
        if len(soil_profile_names) != len(set(soil_profile_names)):
            raise ValueError(f"Duplicate names found in the sheet '{INPUT_SHEETS['soil_profile_positions']}'.\n"
                             "Please ensure all names are unique.")

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
    def parse_water_levels(workbook: Any) -> dict[str, dict[str, float | None]]:
        water_levels = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["water_levels"]],
            header_row=2,
            skip_rows=2,
        )
        # Check for duplicate names
        check_list_of_dicts_for_duplicate_values(water_levels, WATER_LEVEL_LOCATION_NAME_COL)

        # Assign name as key and remove name from dict
        water_level_dict = {
            row[WATER_LEVEL_LOCATION_NAME_COL]: remove_key(row, WATER_LEVEL_LOCATION_NAME_COL)
            for row in water_levels
        }

        return water_level_dict

    @staticmethod
    def parse_water_level_configs(workbook: Any) -> dict[str, dict[str, str | None]]:
        water_level_configs = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["water_level_configs"]],
            header_row=2,
            skip_rows=2,
        )
        # check for duplicate names
        check_list_of_dicts_for_duplicate_values(water_level_configs, WATER_LEVEL_CONFIG_NAME_COL)

        # Assign name as key and remove name from dict
        water_level_configs_dict = {
            row[WATER_LEVEL_CONFIG_NAME_COL]: remove_key(row, WATER_LEVEL_CONFIG_NAME_COL)
            for row in water_level_configs
        }

        return water_level_configs_dict

    @staticmethod
    def parse_headline_offset_methods(workbook: Any) -> dict[str, list[dict[str, str | float]]]:
        # Helper dict for mapping the ref_level_type to the offset_type
        REF_LEVEL_TYPE_TO_OFFSET_TYPE = {
            RefLevelType.NAP: OffsetType.VERTICAL,
            RefLevelType.SURFACE_LEVEL: OffsetType.VERTICAL,
            RefLevelType.FIXED_LEVEL: OffsetType.VERTICAL,
            RefLevelType.RELATED_TO_OTHER_POINT: OffsetType.SLOPING,
        }

        headline_offset_methods = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["headline_offset_methods"]],
            header_row=1,
            skip_rows=2,
            col_dict=HEADLINE_OFFSET_METHODS_COLS,
        )
        for headline_offset_method in headline_offset_methods:
            headline_offset_method["char_point_type"] = INPUT_TO_CHAR_POINTS.get(
                headline_offset_method["char_point_type"])

            # If ref_level is not in the input_to_ref_level_type dict, then it is a water level (FIXED_LEVEL)
            if headline_offset_method["ref_level"] not in INPUT_TO_REF_LEVEL_TYPE:
                headline_offset_method["ref_level_type"] = RefLevelType.FIXED_LEVEL
                headline_offset_method["ref_level_name"] = headline_offset_method["ref_level"]
            else:
                headline_offset_method["ref_level_type"] = INPUT_TO_REF_LEVEL_TYPE.get(
                    headline_offset_method["ref_level"])
                headline_offset_method["ref_level_name"] = None
            headline_offset_method.pop("ref_level")

            headline_offset_method["offset_type"] = REF_LEVEL_TYPE_TO_OFFSET_TYPE.get(
                headline_offset_method["ref_level_type"])

        headline_offset_methods = group_dicts_by_key(headline_offset_methods, group_by_key="name")

        return headline_offset_methods

    @staticmethod
    def parse_head_line_configs(workbook: Any) -> dict[str, list[dict[str, str | bool | float | CharPointType | None]]]:
        head_line_configs = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["head_line_configs"]],
            header_row=2,
            skip_rows=4,
            col_dict=HEAD_LINE_CONFIG_COLS,
        )
        for head_line_config in head_line_configs:
            head_line_config["is_phreatic"] = INPUT_TO_BOOL.get(head_line_config["is_phreatic"])
            head_line_config["head_line_method_type"] = INPUT_TO_HEAD_LINE_METHOD_TYPE.get(
                head_line_config["head_line_method_type"])
            head_line_config["apply_minimal_surface_line_offset"] = INPUT_TO_BOOL.get(
                head_line_config["apply_minimal_surface_line_offset"])
            head_line_config["minimal_offset_from_point"] = INPUT_TO_CHAR_POINTS.get(
                head_line_config["minimal_offset_from_point"])
            head_line_config["minimal_offset_to_point"] = INPUT_TO_CHAR_POINTS.get(
                head_line_config["minimal_offset_to_point"])

        head_line_configs = group_dicts_by_key(head_line_configs, group_by_key="name_waternet_scenario")

        return head_line_configs

    @staticmethod
    def parse_ref_line_configs(workbook: Any) -> dict[str, list[dict[str, str | None]]]:
        ref_line_configs = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["ref_line_configs"]],
            header_row=2,
            skip_rows=4,
            col_dict=REF_LINE_CONFIG_COLS,
        )
        for ref_line_config in ref_line_configs:
            ref_line_config["ref_line_method_type"] = INPUT_TO_REF_LINE_METHOD_TYPE.get(
                ref_line_config["ref_line_method_type"])

        ref_line_configs = group_dicts_by_key(ref_line_configs, group_by_key="name_waternet_scenario")

        return ref_line_configs

    @staticmethod
    def parse_revetment_profile_blueprints(workbook: Any) -> dict[str, list[dict[str, str | float]]]:
        revetment_profile_blueprints = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["revetment_profile_blueprints"]],
            header_row=1,
            skip_rows=2,
            col_dict=REVERTMENT_PROFILE_COLS,
        )

        for revetment_profile_blueprint in revetment_profile_blueprints:
            revetment_profile_blueprint["from_char_point"] = INPUT_TO_CHAR_POINTS.get(
                revetment_profile_blueprint["from_char_point"])
            revetment_profile_blueprint["to_char_point"] = INPUT_TO_CHAR_POINTS.get(
                revetment_profile_blueprint["to_char_point"])

        revetment_profile_blueprints = group_dicts_by_key(revetment_profile_blueprints,
                                                          group_by_key="revetment_profile_name")

        return revetment_profile_blueprints

    def parse_loads(workbook: Any):
        loads = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["loads"]],
            header_row=1,
            skip_rows=2,
            col_dict=LOAD_COLS,
        )
        check_list_of_dicts_for_duplicate_values(loads, "name")

        for line_dict in loads:
            line_dict["direction"] = INPUT_TO_SIDE.get(line_dict["direction"])
            line_dict["position"] = INPUT_TO_CHAR_POINTS.get(line_dict["position"])

        return loads

    # TODO: Wellicht voor uitzonderingen?
    # @staticmethod
    # def parse_hydraulic_pressure(workbook: Any):
    #     hydraulic_pressure = parse_row_instance_remainder(
    #         sheet=workbook[INPUT_SHEETS["hydraulic_pressure"]],
    #         header_row=1,
    #         skip_rows=3,
    #         col_dict=HYDRAULIC_PRESSURE_COLS,
    #         key_remainder="values",
    #     )

    #     # Preprocess hydraulic_pressure
    #     for line_dict in hydraulic_pressure:
    #         line_dict["type"] = INPUT_TO_WATER_LINE_TYPE.get(line_dict["type"])

    #     # Create structured dict {calc_name: {scenario: {stage: {...}}}}
    #     hydraulic_pressure = list_to_nested_dict(
    #         hydraulic_pressure,
    #         keys=["calc_name", "scenario", "stage"],
    #         remove_group_key=True,
    #     )
    #     return hydraulic_pressure

    @staticmethod
    def parse_grid_settings(workbook: Any) -> dict[str, list[dict[str, str | float | None]]]:
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
                "tangent_line_position",
                "grid_1_position",
                "grid_2_position",
                "tangent_area_position",
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
        
        for grid_setting in grid_settings.values():
            check_list_of_dicts_for_duplicate_values(grid_setting, "grid_setting_name")

        return grid_settings

    @staticmethod
    def parse_model_configs(workbook: Any) -> list[dict[str, str | float | bool | None]]:
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
                # Check for duplicate stage names
                check_list_of_dicts_for_duplicate_values(scenario_rows, "stage_name")

                # Get the grid_settings_set_name and check if there is one at max.
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
    def convert(raw_input: RawUserInput) -> UserInputStructure:
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
            water_levels=WaterLevelCollection(water_levels=raw_input.water_levels),
            waternet_configs=RawInputToUserInputStructure.convert_waternet_config_collection(
                water_level_configs_dict=raw_input.water_level_configs,
                head_line_configs_dict=raw_input.head_line_configs,
                ref_line_configs_dict=raw_input.ref_line_configs,
            ),
            headline_offset_methods=RawInputToUserInputStructure.convert_headline_offset_methods(
                raw_input.headline_offset_methods),
            revetment_profile_blueprints=RawInputToUserInputStructure.convert_revetment_profile_blueprint_collection(
                raw_input.revetment_profile_blueprints),
            loads=RawInputToUserInputStructure.convert_loads(raw_input.loads),
            # waternets=RawInputToUserInputStructure.convert_waternet_collection(
            #     raw_input.hydraulic_pressure, name_phreatic_line=NAME_PHREATIC_LINE
            # ),
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
    def convert_char_points(char_points_dict: dict[str, dict[str, float | None]]) -> CharPointsProfileCollection:
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
        """Parses the dictionary into a SoilCollection

        Args:
            soil_list: list of dictionaries with the soil properties

        Returns:
            A SoilCollection instance

        Required keys in the dictionary:
          name: str
          unsaturated_weight: float
          saturated_weight: float
          strength_model_above: Literal["Shansep", "Mohr-Coulomb", "Su Table"]
          strength_model_below: Literal["Shansep", "Mohr-Coulomb", "Su Table"]
          probabilistic_strength_parameters: bool
          c_mean: float
          c_std: float
          phi_mean: float
          phi_std: float
          psi_mean: float
          psi_std: float
          shear_stress_ratio_s_mean: float
          shear_stress_ratio_s_std: float
          strength_exponent_m_mean: float
          strength_exponent_m_std: float
          probabilistic_pop: bool
          pop_mean: float
          pop_std: float
          correlation_s-m: bool
          correlation_c-phi: bool
          consolidation_traffic_load: float
          color: str
          pattern: str

        Args:
            soil_list: list of dictionaries with the soil properties
        """
        req_keys = [
            "name",
            "unsaturated_weight",
            "saturated_weight",
            "strength_model_above",
            "strength_model_below",
            "probabilistic_strength_parameters",
            "c_mean",
            "c_std",
            "phi_mean",
            "phi_std",
            "psi_mean",
            "psi_std",
            "shear_stress_ratio_s_mean",
            "shear_stress_ratio_s_std",
            "strength_exponent_m_mean",
            "strength_exponent_m_std",
            "probabilistic_pop",
            "pop_mean",
            "pop_std",
            "correlation_s-m",
            "correlation_c-phi",
            "consolidation_traffic_load",
            "color",
            "pattern",
        ]

        strength_model = {
            "Shansep": ShearStrengthModelTypePhreaticLevel.SHANSEP,
            "Mohr-Coulomb": ShearStrengthModelTypePhreaticLevel.MOHR_COULOMB,
            "Su Table": ShearStrengthModelTypePhreaticLevel.SUTABLE,
        }

        soils: list[Soil] = []

        for soil_dict in soil_list:
            # Check that all the required keys are present
            check_for_missing_keys(soil_dict, req_keys)

            gl_soil = GLSoil()
            gl_soil.is_probabilistic = soil_dict["probabilistic_strength_parameters"]
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
            gl_soil.mohr_coulomb_parameters.cohesion.mean = soil_dict["c_mean"]
            gl_soil.mohr_coulomb_parameters.cohesion.standard_deviation = soil_dict["c_std"]
            gl_soil.mohr_coulomb_parameters.cohesion.is_probabilistic = True if soil_dict["c_std"] else False
            gl_soil.mohr_coulomb_parameters.friction_angle.mean = soil_dict["phi_mean"]
            gl_soil.mohr_coulomb_parameters.friction_angle.standard_deviation = soil_dict["phi_std"]
            gl_soil.mohr_coulomb_parameters.friction_angle.is_probabilistic = True if soil_dict["phi_std"] else False
            gl_soil.mohr_coulomb_parameters.dilatancy_angle.mean = soil_dict["psi_mean"]
            gl_soil.mohr_coulomb_parameters.dilatancy_angle.standard_deviation = soil_dict["psi_std"]
            gl_soil.mohr_coulomb_parameters.dilatancy_angle.is_probabilistic = True if soil_dict["psi_std"] else False
            gl_soil.undrained_parameters.shear_strength_ratio.mean = soil_dict[
                "shear_stress_ratio_s_mean"
            ]
            gl_soil.undrained_parameters.shear_strength_ratio.standard_deviation = soil_dict["shear_stress_ratio_s_std"]
            gl_soil.undrained_parameters.shear_strength_ratio.is_probabilistic = True if soil_dict[
                "shear_stress_ratio_s_std"] else False
            gl_soil.undrained_parameters.strength_increase_exponent.mean = soil_dict[
                "strength_exponent_m_mean"
            ]
            gl_soil.undrained_parameters.strength_increase_exponent.standard_deviation = soil_dict[
                "strength_exponent_m_std"]
            gl_soil.undrained_parameters.strength_increase_exponent.is_probabilistic = True if soil_dict[
                "strength_exponent_m_std"] else False
            gl_soil.mohr_coulomb_parameters.cohesion_and_friction_angle_correlated = soil_dict["correlation_c-phi"]
            gl_soil.undrained_parameters.shear_strength_ratio_and_shear_strength_exponent_correlated = soil_dict[
                "correlation_s-m"]

            soil = Soil(
                gl_soil=gl_soil,
                pop_mean=soil_dict["pop_mean"],
                pop_std=soil_dict["pop_std"],
                probabilistic_pop=soil_dict["probabilistic_pop"] if soil_dict["probabilistic_pop"] else False,
                consolidation_traffic_load=soil_dict["consolidation_traffic_load"],
                color=soil_dict["color"],
                pattern=soil_dict["pattern"],
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
    def convert_soil_profile_positions(
            soil_profile_positions_dict: dict[str, dict[str, float | None]]
    ) -> SoilProfilePositionSetCollection:
        """Parses the dictionary into a SoilProfilePositionSetCollection

        Args:
            soil_profile_positions_dict: The dictionary to parse."""

        sets: list[SoilProfilePositionSet] = []

        for set_name, position_set_dict in soil_profile_positions_dict.items():
            positions: list[SoilProfilePosition] = []

            for soil_profile_name, l_coord in position_set_dict.items():
                positions.append(SoilProfilePosition(profile_name=soil_profile_name, l_coord=l_coord))

            sets.append(SoilProfilePositionSet(set_name=set_name, soil_profile_positions=positions))

        soil_profile_position_collection = SoilProfilePositionSetCollection(sets=sets)

        return soil_profile_position_collection

    @staticmethod
    def convert_waternet_config_collection(
            water_level_configs_dict: dict[str, dict[str, str | None]],
            head_line_configs_dict: dict[str, list[dict[str, str | bool | float | CharPointType]]],
            ref_line_configs_dict: dict[str, list[dict[str, str | None]]]
    ) -> WaternetConfigCollection:
        hlc_scenario_names = list(head_line_configs_dict.keys())
        wlc_scenario_names = list(water_level_configs_dict.keys())

        # Beide moeten nu in allebei zitten - opzich prima, maar dan kan er geen 'overtollige info' staat
        # TODO: Na implementatie van reference_line_configs, even opnieuw checken.
        if set(hlc_scenario_names) != set(wlc_scenario_names):
            union = set(hlc_scenario_names) | set(wlc_scenario_names)
            intersection = set(hlc_scenario_names) & set(wlc_scenario_names)
            difference = union - intersection

            raise ValueError("The head line scenario names and the water level scenario names do not match. "
                             f"The following scenario names are not present in all input sheets: "
                             f"{', '.join(difference)}")

        waternet_configs: list[WaternetConfig] = []

        for scenario_name in hlc_scenario_names:
            head_line_configs = [
                HeadLineConfig.model_validate(head_line_config)
                for head_line_config in head_line_configs_dict[scenario_name]
            ]
            water_level_config = WaterLevelConfig(
                name_waternet_scenario=scenario_name,
                water_levels=water_level_configs_dict[scenario_name]
            )

            ref_line_configs = [
                ReferenceLineConfig.model_validate(ref_line_config)
                for ref_line_config in ref_line_configs_dict[scenario_name]
            ]

            waternet_config = WaternetConfig(
                name_waternet_scenario=scenario_name,
                water_level_config=water_level_config,
                head_line_configs=head_line_configs,
                reference_line_configs=ref_line_configs
            )
            waternet_configs.append(waternet_config)

        return WaternetConfigCollection(waternet_configs=waternet_configs)

    # TODO: refactor - niet alleen headlines want ook reflines. Dus line_offset_methods
    @staticmethod
    def convert_headline_offset_methods(
            headline_offset_methods_dict: dict[str, list[dict[str, str | float | None]]]) -> LineOffsetMethodCollection:
        headline_offset_methods: list[LineOffsetMethod] = []

        for name, headline_offset_method_dict in headline_offset_methods_dict.items():
            headline_offset_points = [LineOffsetPoint.model_validate(op_dict) for op_dict in
                                      headline_offset_method_dict]
            headline_offset_methods.append(
                LineOffsetMethod(name_method=name, offset_points=headline_offset_points)
            )

        return LineOffsetMethodCollection(offset_methods=headline_offset_methods)

    @staticmethod
    def convert_revetment_profile_blueprint_collection(
            revetment_profile_dict: dict[str, list[dict[str, Any]]]
    ) -> RevetmentProfileBlueprintCollection:
        """Parses the dictionary into a RevetmentProfileBlueprintCollection

        Args:
            revetment_profile_dict: The dictionary to parse."""

        revetment_profile_blueprints: list[RevetmentProfileBlueprint] = []

        for name, revetment_layer_list in revetment_profile_dict.items():
            layer_blueprints: list[RevetmentLayerBlueprint] = []

            for revetment_layer in revetment_layer_list:
                layer_blueprints.append(RevetmentLayerBlueprint(
                    soil_type=revetment_layer["soil_type"],
                    thickness=revetment_layer["thickness"],
                    char_point_types=(
                        revetment_layer["from_char_point"],
                        revetment_layer["to_char_point"],
                    ),
                ))
            revetment_profile_blueprint = RevetmentProfileBlueprint(
                name=name,
                layer_blueprints=layer_blueprints,
            )
            revetment_profile_blueprints.append(revetment_profile_blueprint)

        return RevetmentProfileBlueprintCollection(profile_blueprints=revetment_profile_blueprints)

    @staticmethod
    def convert_loads(loads_dicts: list[dict[str, Any]]) -> LoadCollection:
        """Parses the dictionary into a LoadCollection

        Args:
            loads_dicts: List with load dicts to parse. The keys should match
              the Load attributes."""

        loads = [Load.model_validate(load_dict) for load_dict in loads_dicts]

        return LoadCollection(loads=loads)

    # TODO: Wordt nu niet gebruikt (was voor omzetten rechtstreekse input waternets)
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

    # TODO: Wordt nu niet gebruikt (was voor omzetten rechtstreekse input waternets)
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

    # TODO: Omschrijven naar WaternetExceptionCollection
    # @staticmethod
    # def convert_waternet_collection(
    #     waternets_dict: dict[str, dict[str, dict[str, list[dict[str, Any]]]]], 
    #     name_phreatic_line: str
    # ) -> WaternetCollection:
    #     """Parse dict to WaternetCollection

    #     Args:
    #         waternets_dict: Dictionary with structure {calc_name: {scenario: {stage: [line_dicts]}}}
    #         name_phreatic_line: The name of the phreatic line

    #     Returns:
    #         WaternetCollection: Collection of waternet objects"""

    #     waternets: list[Waternet] = []

    #     for calc_name, calc_dict in waternets_dict.items():
    #         for scenario_name, scenario_dict in calc_dict.items():
    #             for stage_name, lines in scenario_dict.items():
    #                 head_lines = RawInputToUserInputStructure.parse_head_lines(lines, name_phreatic_line)
    #                 ref_lines = RawInputToUserInputStructure.parse_ref_lines(lines)
    #                 waternets.append(
    #                     Waternet(
    #                         calc_name=calc_name,
    #                         scenario_name=scenario_name,
    #                         stage_name=stage_name,
    #                         head_lines=head_lines,
    #                         ref_lines=ref_lines,
    #                     )
    #                 )

    #     return WaternetCollection(waternets=waternets)

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

        grid_settings_sets: list[GridSettingsSet] = []

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
