"""
Parses the input file
"""
from pydantic import BaseModel

from pathlib import Path
from typing import List, Any
import openpyxl

from dstability_tool.excel_utils import parse_row_instance, parse_key_row
from dstability_toolbox.geometry import CharPointType, SurfaceLineCollection, CharPointsProfileCollection
from dstability_toolbox.soils import SoilCollection
from dstability_toolbox.subsoil import SoilProfileCollection

INPUT_SHEETS = {
    "surface_lines": "Dwarsprofielen",
    "char_points": "Kar. punten",
    "soil_params": "Sterkteparameters",
    "soil_profiles": "Bodemopbouw",
}

CHAR_POINT_COLS = {
    'name': 'Naam',
    'x_surface_level_water_side': 'X_Maaiveld buitenwaarts',
    'y_surface_level_water_side': 'Y_Maaiveld buitenwaarts',
    'z_surface_level_water_side': 'Z_Maaiveld buitenwaarts',
    'x_toe_canal': 'X_Teen geul', 'y_toe_canal': 'Y_Teen geul',
    'z_toe_canal': 'Z_Teen geul', 'x_start_canal': 'X_Insteek geul',
    'y_start_canal': 'Y_Insteek geul', 'z_start_canal': 'Z_Insteek geul',
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
    "color": "Kleur (hex, zonder #)",
}

SOIL_PROFILE_COLS = {
    "name": "Naam grondprofiel",
    "soil_type": "Grondsoort",
    "top": "Bovenkant",
}


def remove_key(d: dict, key: Any):
    d.pop(key)
    return d


class RawUserInput(BaseModel):
    """Represents the Input Excel file"""
    surface_lines: dict
    char_points: dict[str, dict]
    soil_params: List[dict]
    soil_profiles: List[dict]

    @classmethod
    def read_from_file(cls, file_path: str | Path):
        """Creates an instance from an input file"""
        workbook = openpyxl.load_workbook(
            file_path, data_only=True, read_only=True
        )
        surface_lines = parse_key_row(sheet=workbook[INPUT_SHEETS["surface_lines"]], skip_rows=1)
        char_points = parse_row_instance(
            sheet=workbook[INPUT_SHEETS["char_points"]],
            header_row=1,
            skip_rows=1,
            col_dict=CHAR_POINT_COLS
        )
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

        return cls(
            surface_lines=surface_lines,
            char_points=char_points,
            soil_params=soil_params,
            soil_profiles=soil_profiles
        )


class UserInputStructure(BaseModel):
    surface_lines: SurfaceLineCollection
    char_points: CharPointsProfileCollection
    # soil_params: SoilCollection
    # soil_profiles: SoilProfileCollection

    @classmethod
    def from_raw_input(cls, raw_input: RawUserInput):
        surface_lines = SurfaceLineCollection.from_dict(raw_input.surface_lines)
        char_points = CharPointsProfileCollection.from_dict(raw_input.char_points)

        return cls(surface_lines=surface_lines, char_points=char_points)


# REMINDER: Houdt de invoerstructuur zo algemeen mogelijk. list met dicts is algemeen als tabel handig
# Behalve dingen die obvious een invoerbestand zijn (zoals surfacelines en charpoints)

