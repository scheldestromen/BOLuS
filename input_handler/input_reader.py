"""
Parses the input file
"""
from geolib.models.dstability.internal import OptionsType
from pydantic import BaseModel

from pathlib import Path
import openpyxl

from dstability_toolbox.calculation_settings import SlipPlaneModel, GridSettingsSetCollection
from dstability_toolbox.loads import LoadCollection
from dstability_toolbox.soils import SoilCollection
from dstability_toolbox.subsoil import SoilProfileCollection
from input_handler.excel_utils import (parse_row_instance, parse_key_row, parse_row_instance_remainder,
                                       parse_key_value_cols)
from dstability_toolbox.geometry import CharPointType, Side, SurfaceLineCollection, CharPointsProfileCollection
from dstability_toolbox.water import WaterLineType, WaternetCollection
from input_handler.user_input import UserInputStructure, model_configs_from_list
from utils.dict_utils import remove_key, group_dicts_by_key, list_to_nested_dict
from utils.list_utils import check_list_of_dicts_for_duplicate_values, unique_in_order

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
    "model_configs": "Berekeningen"
}

SETTINGS_COLS = {
    "setting": "Instelling",
    "value": "Waarde"
}

SETTINGS_NAMES = {
    "Minimale diepte ondergrond": "min_soil_profile_depth",
}

CHAR_POINT_COLS = {
    'name': 'LOCATIONID',
    'x_surface_level_water_side': 'X_Maaiveld buitenwaarts',
    'y_surface_level_water_side': 'Y_Maaiveld buitenwaarts',
    'z_surface_level_water_side': 'Z_Maaiveld buitenwaarts',
    'x_toe_canal': 'X_Teen geul',
    'y_toe_canal': 'Y_Teen geul',
    'z_toe_canal': 'Z_Teen geul',
    'x_start_canal': 'X_Insteek geul',
    'y_start_canal': 'Y_Insteek geul',
    'z_start_canal': 'Z_Insteek geul',
    'x_dike_toe_water_side': 'X_Teen dijk buitenwaarts',
    'y_dike_toe_water_side': 'Y_Teen dijk buitenwaarts',
    'z_dike_toe_water_side': 'Z_Teen dijk buitenwaarts',
    'x_berm_crest_water_side': 'X_Kruin buitenberm',
    'y_berm_crest_water_side': 'Y_Kruin buitenberm',
    'z_berm_crest_water_side': 'Z_Kruin buitenberm',
    'x_berm_start_water_side': 'X_Insteek buitenberm',
    'y_berm_start_water_side': 'Y_Insteek buitenberm',
    'z_berm_start_water_side': 'Z_Insteek buitenberm',
    'x_dike_crest_water_side': 'X_Kruin buitentalud',
    'y_dike_crest_water_side': 'Y_Kruin buitentalud',
    'z_dike_crest_water_side': 'Z_Kruin buitentalud',
    'x_traffic_load_water_side': 'X_Verkeersbelasting kant buitenwaarts',
    'y_traffic_load_water_side': 'Y_Verkeersbelasting kant buitenwaarts',
    'z_traffic_load_water_side': 'Z_Verkeersbelasting kant buitenwaarts',
    'x_traffic_load_land_side': 'X_Verkeersbelasting kant binnenwaarts',
    'y_traffic_load_land_side': 'Y_Verkeersbelasting kant binnenwaarts',
    'z_traffic_load_land_side': 'Z_Verkeersbelasting kant binnenwaarts',
    'x_dike_crest_land_side': 'X_Kruin binnentalud',
    'y_dike_crest_land_side': 'Y_Kruin binnentalud',
    'z_dike_crest_land_side': 'Z_Kruin binnentalud',
    'x_berm_start_land_side': 'X_Insteek binnenberm',
    'y_berm_start_land_side': 'Y_Insteek binnenberm',
    'z_berm_start_land_side': 'Z_Insteek binnenberm',
    'x_berm_crest_land_side': 'X_Kruin binnenberm',
    'y_berm_crest_land_side': 'Y_Kruin binnenberm',
    'z_berm_crest_land_side': 'Z_Kruin binnenberm',
    'x_dike_toe_land_side': 'X_Teen dijk binnenwaarts',
    'y_dike_toe_land_side': 'Y_Teen dijk binnenwaarts',
    'z_dike_toe_land_side': 'Z_Teen dijk binnenwaarts',
    'x_ditch_start_water_side': 'X_Insteek sloot dijkzijde',
    'y_ditch_start_water_side': 'Y_Insteek sloot dijkzijde',
    'z_ditch_start_water_side': 'Z_Insteek sloot dijkzijde',
    'x_ditch_bottom_water_side': 'X_Slootbodem dijkzijde',
    'y_ditch_bottom_water_side': 'Y_Slootbodem dijkzijde',
    'z_ditch_bottom_water_side': 'Z_Slootbodem dijkzijde',
    'x_ditch_bottom_land_side': 'X_Slootbodem polderzijde',
    'y_ditch_bottom_land_side': 'Y_Slootbodem polderzijde',
    'z_ditch_bottom_land_side': 'Z_Slootbodem polderzijde',
    'x_ditch_start_land_side': 'X_Insteek sloot polderzijde',
    'y_ditch_start_land_side': 'Y_Insteek sloot polderzijde',
    'z_ditch_start_land_side': 'Z_Insteek sloot polderzijde',
    'x_surface_level_land_side': 'X_Maaiveld binnenwaarts',
    'y_surface_level_land_side': 'Y_Maaiveld binnenwaarts',
    'z_surface_level_land_side': 'Z_Maaiveld binnenwaarts'
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
    'width': 'Breedte',
    'position': 'Positie',
    'direction': 'Richting',
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
    "evaluate": "Berekenen"
}

INPUT_TO_BOOL = {
    "Ja": True,
    "Nee": False,
    None: None
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
    None: None
}

INPUT_TO_SIDE = {
    "Binnenwaarts": Side.LAND_SIDE,
    "Buitenwaarts": Side.WATER_SIDE,
    None: None
}

INPUT_TO_WATER_LINE_TYPE = {
    "Stijghoogtelijn": WaterLineType.HEADLINE,
    "Referentielijn": WaterLineType.REFERENCE_LINE
}

INPUT_TO_SLIP_PLANE_MODEL = {
    "Uplift Van": SlipPlaneModel.UPLIFT_VAN_PARTICLE_SWARM,
    "Bishop": SlipPlaneModel.BISHOP_BRUTE_FORCE
}

INPUT_TO_SEARCH_MODE = {
    "Normal": OptionsType.DEFAULT,
    "Thorough": OptionsType.THOROUGH,
    None: None
}

NAME_PHREATIC_LINE = "Freatisch"


class RawUserInput(BaseModel):
    """Represents the Input Excel file"""
    settings: dict[str, str | float]
    surface_lines: dict[str, list]
    char_points: dict[str, dict]
    soil_params: list[dict]
    soil_profiles: dict[str, list]
    soil_profile_positions: dict[str, dict[str, float | None]]
    loads: list[dict]
    hydraulic_pressure: dict
    grid_settings: dict[str, list]
    model_configs: list[dict]

    @classmethod
    def read_from_file(cls, file_path: str | Path):
        """Creates an instance from an input file"""
        workbook = openpyxl.load_workbook(
            file_path, data_only=True, read_only=True
        )
        settings = parse_key_value_cols(
            sheet=workbook[INPUT_SHEETS["settings"]],
            header_row=1,
            skip_rows=1,
            key_col='setting',
            value_col='value',
            col_dict=SETTINGS_COLS,
            key_dict=SETTINGS_NAMES
        )

        surface_lines = parse_key_row(sheet=workbook[INPUT_SHEETS["surface_lines"]], skip_rows=1)
        char_points = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["char_points"]],
            header_row=1,
            skip_rows=1,
            col_dict=CHAR_POINT_COLS
        )
        check_list_of_dicts_for_duplicate_values(char_points, "name")  # Check uniqueness of names
        char_points = {char_dict["name"]: remove_key(char_dict, "name") for char_dict in char_points}

        soil_params = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["soil_params"]],
            header_row=1,
            skip_rows=2,
            col_dict=SOIL_COLS
        )
        soil_profiles = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["soil_profiles"]],
            header_row=1,
            skip_rows=2,
            col_dict=SOIL_PROFILE_COLS
        )
        soil_profiles = group_dicts_by_key(soil_profiles, group_by_key="name")

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

        loads = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["loads"]],
            header_row=1,
            skip_rows=2,
            col_dict=LOAD_COLS
        )

        for line_dict in loads:
            line_dict["direction"] = INPUT_TO_SIDE[line_dict["direction"]]
            line_dict["position"] = INPUT_TO_CHAR_POINTS[line_dict["position"]]

        hydraulic_pressure = parse_row_instance_remainder(
            sheet=workbook[INPUT_SHEETS["hydraulic_pressure"]],
            header_row=1,
            skip_rows=3,
            col_dict=HYDRAULIC_PRESSURE_COLS,
            key_remainder="values"
        )

        # Preprocess hydraulic_pressure
        for line_dict in hydraulic_pressure:
            line_dict["type"] = INPUT_TO_WATER_LINE_TYPE[line_dict["type"]]

        # Create structured dict {calc_name: {scenario: {stage: {...}}}}
        hydraulic_pressure = list_to_nested_dict(
            hydraulic_pressure,
            keys=["calc_name", "scenario", "stage"],
            remove_group_key=True
        )

        # Read and preprocess the grid settings
        grid_settings = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["grid_settings"]],
            header_row=2,
            skip_rows=4,
            col_dict=GRID_SETTINGS_COLS
        )
        for line_dict in grid_settings:
            line_dict['slip_plane_model'] = INPUT_TO_SLIP_PLANE_MODEL[line_dict['slip_plane_model']]
            line_dict['search_mode'] = INPUT_TO_SEARCH_MODE[line_dict['search_mode']]

            for key in ["grid_direction", "grid_1_direction", "grid_2_direction",
                        "zone_a_direction", "zone_b_direction"]:
                line_dict[key] = INPUT_TO_SIDE[line_dict[key]]

            for key in ["grid_position", "grid_1_position", "grid_2_position",
                        "zone_a_position", "zone_b_position"]:
                line_dict[key] = INPUT_TO_CHAR_POINTS[line_dict[key]]

            for key in ["move_grid", "apply_minimum_slip_plane_dimensions", "apply_constraint_zone_a",
                        "apply_constraint_zone_b"]:
                line_dict[key] = INPUT_TO_BOOL[line_dict[key]]

        grid_settings = group_dicts_by_key(grid_settings, group_by_key="name_set")

        model_config_rows = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["model_configs"]],
            header_row=2,
            skip_rows=4,
            col_dict=CALCULATION_COLS
        )

        # Preprocess model_configs
        for model_dict in model_config_rows:
            model_dict["apply_state_points"] = INPUT_TO_BOOL[model_dict["apply_state_points"]]

        calc_names = unique_in_order([calc_row["calc_name"] for calc_row in model_config_rows])
        model_configs = []

        # Create structured list [{calc_name: "name", "scenarios": [{"scenario_name": "name", "stages": {"stage_name":..
        for calc_name in calc_names:
            # Get all row of calculation calc_name
            calc_rows = [calc_row for calc_row in model_config_rows if calc_row["calc_name"] == calc_name]
            scenario_names = unique_in_order([row["scenario_name"] for row in calc_rows])
            scenarios = []

            for scenario_name in scenario_names:
                # Get al rows belonging to the scenario
                scenario_rows = [row for row in calc_rows if row["scenario_name"] == scenario_name]
                grid_settings_set_name_list = [row["grid_settings_set_name"] for row in scenario_rows
                                          if row["grid_settings_set_name"] is not None]

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
                    "grid_settings_set_name": grid_settings_set_name
                }
                scenarios.append(scenario)

            model_configs.append({"calc_name": calc_name, "scenarios": scenarios})

        return cls(
            settings=settings,
            surface_lines=surface_lines,
            char_points=char_points,
            soil_params=soil_params,
            soil_profiles=soil_profiles,
            soil_profile_positions=soil_profile_positions,
            loads=loads,
            hydraulic_pressure=hydraulic_pressure,
            grid_settings=grid_settings,
            model_configs=model_configs
        )


def raw_input_to_user_input_structure(raw_input: RawUserInput) -> UserInputStructure:
    surface_lines = SurfaceLineCollection.from_dict(raw_input.surface_lines)
    char_points = CharPointsProfileCollection.from_dict(raw_input.char_points)
    soil_collection = SoilCollection.from_list(raw_input.soil_params)
    soil_profiles = SoilProfileCollection.from_dict(raw_input.soil_profiles)
    loads = LoadCollection.from_list(raw_input.loads)
    waternet_collection = WaternetCollection.from_dict(
        raw_input.hydraulic_pressure, name_phreatic_line=NAME_PHREATIC_LINE
    )
    grid_settings = GridSettingsSetCollection.from_dict(raw_input.grid_settings)
    model_configs = model_configs_from_list(raw_input.model_configs)

    return UserInputStructure(
        settings=raw_input.settings,
        surface_lines=surface_lines,
        char_points=char_points,
        soils=soil_collection,
        soil_profiles=soil_profiles,
        soil_profile_positions=raw_input.soil_profile_positions,
        loads=loads,
        waternets=waternet_collection,
        grid_settings=grid_settings,
        model_configs=model_configs
    )

# REMINDER: Houdt de invoerstructuur zo algemeen mogelijk. list met dicts is algemeen als tabel handig
# Behalve dingen die duidelijk een invoerbestand zijn (zoals surfacelines en charpoints)
# En als een dict logischer is, bv met soil profiles, waarbij de naam bovenliggend is en per regel een workaround is
# t.b.v. invoer in Excel

# Twijfel over beste locatie voor omzetten van invoervariabele (INPUT_TO_...). Nu bij RawInput,
