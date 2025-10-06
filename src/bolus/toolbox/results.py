"""
Reading and exporting DStablityModel results
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import openpyxl
from geolib.models.dstability.dstability_model import DStabilityModel
from geolib.models.dstability.internal import (
    BishopBruteForceReliabilityResult, BishopBruteForceResult,
    BishopReliabilityResult, BishopResult,
    SpencerGeneticAlgorithmReliabilityResult, SpencerGeneticAlgorithmResult,
    SpencerReliabilityResult, SpencerResult,
    UpliftVanParticleSwarmReliabilityResult, UpliftVanParticleSwarmResult,
    UpliftVanReliabilityResult, UpliftVanResult)
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import BaseModel

from bolus.toolbox.modifier import parse_d_stability_models
from bolus.utils.file_utils import get_files_by_extension
from bolus.utils.list_utils import get_list_item_indices

RESULT_SHEETS = {"Resultaten": "all_results", "Maatgevend": "critical_result"}

ALL_RESULT_COLS = {
    "name": "Naam",
    "scenario": "Scenario",
    "calculation": "Berekening",
    "analysis_type": "Type",
    "sf": "SF",
    "failure_probability": "Faalkans",
    "reliability_index": "Betrouwbaarheidsindex",
    "convergence": "Convergentie",
    "distance_to_convergence": "Afstand tot convergentie",
    "l_coord_1": "L-coord 1",
    "z_coord_1": "Z-coord 1",
    "radius_1": "Radius 1",
    "l_coord_2": "L-coord 2",
    "z_coord_2": "Z-coord 2",
    "radius_2": "Radius 2",
}


# Grouping the result types for convenience
BishopResultType = (
    BishopBruteForceResult
    | BishopReliabilityResult
    | BishopBruteForceReliabilityResult
    | BishopResult
)

UpliftVanResultType = (
    UpliftVanResult
    | UpliftVanParticleSwarmResult
    | UpliftVanReliabilityResult
    | UpliftVanParticleSwarmReliabilityResult
)

SpencerResultType = (
    SpencerGeneticAlgorithmResult
    | SpencerReliabilityResult
    | SpencerGeneticAlgorithmReliabilityResult
    | SpencerResult
)

DStabilityResult = BishopResultType | SpencerResultType | UpliftVanResultType


class ResultSummary(BaseModel):
    """Represents the most important information of a slope
    stability calculation"""

    analysis_type: str
    sf: Optional[float | str] = None
    failure_probability: Optional[float | str] = None
    reliability_index: Optional[float | str] = None
    convergence: Optional[bool] = None
    distance_to_convergence: Optional[float | str] = None
    l_coord_1: Optional[float] = None
    z_coord_1: Optional[float] = None
    radius_1: Optional[float] = None
    l_coord_2: Optional[float] = None
    z_coord_2: Optional[float] = None
    radius_2: Optional[float] = None

    @classmethod
    def _nan_to_none(cls, v: Any) -> Optional[Any]:
        """Convert "NaN" to None for any value"""
        if isinstance(v, str) and v.lower() == "nan":
            return None
        return v

    @classmethod
    def from_result(cls, result: DStabilityResult):
        result_type_methods = {
            BishopResultType: cls._from_bishop_result_type,
            UpliftVanResultType: cls._from_uplift_van_result_type,
            SpencerResultType: cls._from_spencer_result_type,
        }

        for result_type, method in result_type_methods.items():
            if isinstance(result, result_type):
                return method(result)

        raise ValueError(f"Unsupported result type {type(result)}")

    @classmethod
    def _from_bishop_result_type(cls, result: BishopResultType) -> "ResultSummary":
        """Internal method for converting a BishopResultType object to a ResultSummary object"""

        try:
            # If there is no calculation result, a value error is raised
            circle = result.get_slipcircle_output()
            l_coord = circle.x
            z_coord = circle.z
            radius = circle.radius

        except ValueError:
            l_coord = None
            z_coord = None
            radius = None

        return cls(
            analysis_type=type(result).__name__[
                :-6
            ],  # Use the class name and remove the "Result" suffix
            sf=cls._nan_to_none(getattr(result, "FactorOfSafety", None)),
            failure_probability=cls._nan_to_none(
                getattr(result, "FailureProbability", None)
            ),
            reliability_index=cls._nan_to_none(
                getattr(result, "ReliabilityIndex", None)
            ),
            convergence=getattr(result, "Converged", None),
            distance_to_convergence=cls._nan_to_none(
                getattr(result, "DistanceToConvergence", None)
            ),
            l_coord_1=l_coord,
            z_coord_1=z_coord,
            radius_1=radius,
        )

    @classmethod
    def _from_uplift_van_result_type(
        cls, result: UpliftVanResultType
    ) -> "ResultSummary":
        """Internal method for converting a UpliftVanResultType object to a ResultSummary object"""

        try:
            # If there is no calculation result, a value error is raised
            circle = result.get_slipcircle_output()
            l_coord_1 = circle.x_left
            z_coord_1 = circle.z_left
            l_coord_2 = circle.x_right
            z_coord_2 = circle.z_right
            tangent = circle.z_tangent
            radius_1 = z_coord_1 - tangent
            radius_2 = z_coord_2 - tangent

        except ValueError:
            l_coord_1 = None
            z_coord_1 = None
            l_coord_2 = None
            z_coord_2 = None
            radius_1 = None
            radius_2 = None

        return cls(
            analysis_type=type(result).__name__[
                :-6
            ],  # Use the class name and remove the "Result" suffix
            sf=cls._nan_to_none(getattr(result, "FactorOfSafety", None)),
            failure_probability=cls._nan_to_none(
                getattr(result, "FailureProbability", None)
            ),
            reliability_index=cls._nan_to_none(
                getattr(result, "ReliabilityIndex", None)
            ),
            convergence=getattr(result, "Converged", None),
            distance_to_convergence=cls._nan_to_none(
                getattr(result, "DistanceToConvergence", None)
            ),
            l_coord_1=l_coord_1,
            z_coord_1=z_coord_1,
            radius_1=radius_1,
            l_coord_2=l_coord_2,
            z_coord_2=z_coord_2,
            radius_2=radius_2,
        )

    @classmethod
    def _from_spencer_result_type(cls, result: SpencerResultType) -> "ResultSummary":
        """Internal method for converting a SpencerResultType object to a ResultSummary object"""
        return cls(
            analysis_type=type(result).__name__[
                :-6
            ],  # Use the class name and remove the "Result" suffix
            sf=cls._nan_to_none(getattr(result, "FactorOfSafety", None)),
            failure_probability=cls._nan_to_none(
                getattr(result, "FailureProbability", None)
            ),
            reliability_index=cls._nan_to_none(
                getattr(result, "ReliabilityIndex", None)
            ),
            convergence=getattr(result, "Converged", None),
            distance_to_convergence=cls._nan_to_none(
                getattr(result, "DistanceToConvergence", None)
            ),
        )


@dataclass
class DStabilityResultExporter:
    """Exports DStabilityModel results to an Excel file using a template

    Attributes:
        dm_list: List of DStabilityModel objects containing calculation results
        template_path: Path to Excel template file
        result_sheet_name: Name of the worksheet in the template where results should be written. Defaults to "Resultaten"
        header_row: Row number (1-based) containing the column headers in the template. Defaults to 2
        result_cols: Optional dictionary mapping internal result column names to template header names. If None, uses ALL_RESULT_COLS

    Private Attributes:
        _workbook: Internal openpyxl Workbook object for template handling
        _worksheet: Internal openpyxl Worksheet object for the active sheet
        _header_indices: Internal mapping of result column names to column indices"""

    dm_list: list[DStabilityModel]
    result_sheet_name: str = "Resultaten"
    template_path: Path = Path(
        os.path.join(os.path.dirname(__file__), "templates", "export_template.xlsx")
    )
    header_row: int = 2
    result_cols: Optional[dict[str, str]] = None
    _workbook: Optional[Workbook] = None
    _worksheet: Optional[Worksheet] = None
    _header_indices: Optional[dict[str, int]] = None

    def read_template(self):
        """Reads the template Excel file"""
        if self.result_cols is None:
            self.result_cols = ALL_RESULT_COLS

        self._workbook = openpyxl.load_workbook(self.template_path)
        self._worksheet = self._workbook[self.result_sheet_name]

        header_list = [cell.value for cell in self._worksheet[self.header_row]]
        header_indices = get_list_item_indices(header_list, self.result_cols)

        # Adding 1 to the indices because openpyxl counts columns from 1
        self._header_indices = {key: value + 1 for key, value in header_indices.items()}

    def write_results(self):
        """Writes the results to the Excel file"""
        # A Calculation instance contains the ResultId and CalculationSetingsId

        for dm in self.dm_list:
            if dm.filename is None:
                raise ValueError(
                    "DStabilityModel has no filename. Has it been serialized?"
                )

            dm_name = Path(dm.filename).name

            for scenario_index, scenario in enumerate(dm.scenarios):
                scenario_name = scenario.Label

                for calculation_index, calculation in enumerate(scenario.Calculations):
                    calculation_name = calculation.Label

                    if dm.has_result(
                        scenario_index=scenario_index,
                        calculation_index=calculation_index,
                    ):
                        result = dm.get_result(
                            scenario_index=scenario_index,
                            calculation_index=calculation_index,
                        )

                        result_summary = ResultSummary.from_result(result=result)
                        result_dict = result_summary.model_dump()
                        result_dict = self.round_result_dict(result_dict=result_dict)

                        result_dict.update(
                            {
                                "name": dm_name,
                                "scenario": scenario_name,
                                "calculation": calculation_name,
                            }
                        )
                        result_row = {
                            self._header_indices[key]: value
                            for key, value in result_dict.items()
                        }
                        self._worksheet.append(result_row)

    @staticmethod
    def round_result_dict(result_dict: dict[str, Any]) -> dict[str, Any]:
        """Rounds the result dictionary"""

        for key, value in result_dict.items():
            if value is None:
                continue

            if key == "sf":
                result_dict[key] = round(value, 3)
            elif key == "reliability_index":
                result_dict[key] = round(value, 4)
            elif key == "failure_probability":
                result_dict[key] = round(value, 6)
            elif any(coord_key in key for coord_key in ["coord", "radius"]):
                result_dict[key] = round(value, 2)
            elif key == "distance_to_convergence":
                result_dict[key] = round(value, 3)

        return result_dict

    def export_results(self, output_path: Path | str):
        """Exports the results to the Excel file

        Args:
            output_path: Path to the output Excel file"""

        self.read_template()
        self.write_results()
        self._workbook.close()
        self._workbook.save(output_path)


def results_from_dir(directory: str, output_path: str):
    """Exports the results from a directory of .stix files to an Excel file

    Args:
        directory: The directory containing the .stix files. All other files are ignored.
        output_path: The path to the output Excel file.

    Returns:
        A DStabilityResultExporter object."""

    stix_files = get_files_by_extension(directory=directory, file_ext=".stix")
    stix_paths = [stx["path"] for stx in stix_files]
    dm_list = parse_d_stability_models(path_list=stix_paths)

    exporter = DStabilityResultExporter(
        dm_list=dm_list,
    )
    exporter.export_results(output_path=output_path)
