"""
Reading and exporting DStablityModel results
"""
from pathlib import Path
from typing import Optional, Union

from geolib.models.dstability.internal import UpliftVanResult, UpliftVanParticleSwarmResult, UpliftVanReliabilityResult, \
    UpliftVanParticleSwarmReliabilityResult, SpencerGeneticAlgorithmResult, SpencerReliabilityResult, \
    SpencerGeneticAlgorithmReliabilityResult, SpencerResult, BishopBruteForceResult, BishopReliabilityResult, \
    BishopBruteForceReliabilityResult, BishopResult
from pydantic import BaseModel
from geolib.models import DStabilityModel
from geolib.models.dstability.dstability_model import AnalysisType

from dstability_toolbox import dm_getter
from dstability_toolbox.dm_getter import get_by_id
from dstability_toolbox.modifier import parse_d_stability_models
from utils.file_utils import get_files_by_extension

RESULT_SHEETS = {
    "Resultaten": "all_results",
    "Maatgevend": "critical_result"
}


ALL_RESULT_COLS = {
    "name": "Naam",
    "scenario": "Scenario",
    "calculation": "Berekening",
    "type": "Type",
    "sf": "SF",
    "sf_critical": "SF maatgevend",
    "failure_probability": "Faalkans",
    "reliability_index": "Betrouwbaarheidsindex",
    "convergence": "Convergentie",
    "distance_to_convergence": "Afstand tot convergentie",
    "failure_probability_critical": "Faalkans maatgevend",
    "l_coord_1": "L-coord 1",
    "z_coord_1": "Z-coord 1",
    "radius_1": "Radius 1",
    "l_coord_2": "L-coord 2",
    "z_coord_2": "Z-coord 2",
    "radius_2": "Radius 2",
}

# RESULT_TYPE_TO_OUTPUT = {
#     UpliftVanResult: "Uplift-Van - Single",
#     UpliftVanParticleSwarmResult: "Uplift-Van Particle Swarm",
#     UpliftVanReliabilityResult: "UpliftVanReliabilityResult",
#     UpliftVanParticleSwarmReliabilityResult: "UpliftVanParticleSwarmReliabilityResult",
#     SpencerGeneticAlgorithmResult: "SpencerGeneticAlgorithmResult",
#     SpencerReliabilityResult: "SpencerReliabilityResult",
#     SpencerGeneticAlgorithmReliabilityResult: "SpencerGeneticAlgorithmReliabilityResult",
#     SpencerResult: "SpencerResult",
#     BishopBruteForceResult: "BishopBruteForceResult",
#     BishopReliabilityResult: "BishopReliabilityResult",
#     BishopBruteForceReliabilityResult: "BishopBruteForceReliabilityResult",
#     BishopResult: "BishopResult",
# }

# Grouping the result types for convenience
BishopResultType = (
    BishopBruteForceResult |
    BishopReliabilityResult |
    BishopBruteForceReliabilityResult |
    BishopResult
)

UpliftVanResultType = (
    UpliftVanResult |
    UpliftVanParticleSwarmResult |
    UpliftVanReliabilityResult |
    UpliftVanParticleSwarmReliabilityResult
)

SpencerResultType = (
    SpencerGeneticAlgorithmResult |
    SpencerReliabilityResult |
    SpencerGeneticAlgorithmReliabilityResult |
    SpencerResult
)


DStabilityResult = (BishopResultType | SpencerResultType | UpliftVanResultType)


class ResultSummary(BaseModel):
    """Represents the most important information for a slope
    stability calculation"""

    analysis_type: str
    sf: Optional[float] = None
    # sf_critical: Optional[bool] = None
    failure_probability: Optional[float] = None
    reliability_index: Optional[float] = None
    convergence: Optional[bool] = None
    distance_to_convergence: Optional[float] = None
    # failure_probability_critical: Optional[float] = None
    l_coord_1: Optional[float] = None
    z_coord_1: Optional[float] = None
    radius_1: Optional[float] = None
    l_coord_2: Optional[float] = None
    z_coord_2: Optional[float] = None
    radius_2: Optional[float] = None

    @classmethod
    def from_result(cls, result: DStabilityResult):
        result_type_methods = {
            BishopResultType: cls._from_bishop_result_type,
            UpliftVanResultType: cls._from_uplift_van_result_type,
            SpencerResultType: cls._from_spencer_result_type
        }

        for result_type, method in result_type_methods.items():
            if isinstance(result, result_type):
                return method(result)

        raise ValueError("Unsupported result type")

    @classmethod
    def _from_bishop_result_type(cls, result: BishopResultType) -> "ResultSummary":
        try:
            circle = result.get_slipcircle_output()
            l_coord = circle.x
            z_coord = circle.z
            radius = circle.radius

        except ValueError():
            l_coord = None
            z_coord = None
            radius = None

        return cls(
            analysis_type=type(result).__name__,
            sf=result.FactorOfSafety,
            # sf_critical=,
            failure_probability=getattr(result, 'FailureProbability', None),
            reliability_index=getattr(result, 'ReliabilityIndex', None),
            convergence=getattr(result, 'Converged', None),
            distance_to_convergence=getattr(result, 'DistanceToConvergence', None),
            # failure_probability_critical=result.failure_probability_critical,
            l_coord_1=l_coord,
            z_coord_1=z_coord,
            radius_1=radius,
        )

    @classmethod
    def _from_uplift_van_result_type(cls, result: UpliftVanResultType) -> "ResultSummary":
        try:
            circle = result.get_slipcircle_output()
            l_coord_1 = circle.x_left
            z_coord_1 = circle.z_left
            l_coord_2 = circle.x_right
            z_coord_2 = circle.z_right
            tangent = circle.z_tangent
            radius_1 = z_coord_1 - tangent
            radius_2 = z_coord_2 - tangent

        except ValueError():
            l_coord_1 = None
            z_coord_1 = None
            l_coord_2 = None
            z_coord_2 = None
            radius_1 = None
            radius_2 = None

        return cls(
            analysis_type=type(result).__name__,
            sf=result.FactorOfSafety,
            # sf_critical=,
            failure_probability=getattr(result, 'FailureProbability', None),
            reliability_index=getattr(result, 'ReliabilityIndex', None),
            convergence=getattr(result, 'Converged', None),
            distance_to_convergence=getattr(result, 'DistanceToConvergence', None),
            # failure_probability_critical=
            l_coord_1=l_coord_1,
            z_coord_1=z_coord_1,
            radius_1=radius_1,
            l_coord_2=l_coord_2,
            z_coord_2=z_coord_2,
            radius_2=radius_2,
        )
    
    @classmethod
    def _from_spencer_result_type(cls, result: SpencerResultType) -> "ResultSummary":
        return {}


def export_results(directory: str):
    # A Calculation instance contains the ResultId and CalculationSetingsId
    stix_files = get_files_by_extension(directory=directory, file_ext='.stix')
    stix_paths = [stx['path'] for stx in stix_files]
    dm_list = parse_d_stability_models(path_list=stix_paths)

    rows = []

    for dm in dm_list:
        dm_name = Path(dm.filename).name

        for scenario_index, scenario in enumerate(dm.scenarios):
            scenario_name = scenario.Label

            for calculation_index, calculation in enumerate(scenario.Calculations):
                calculation_name = calculation.Label

                if dm.has_result(scenario_index=scenario_index,
                                 calculation_index=calculation_index):
                    result = dm.get_result(scenario_index=scenario_index,
                                           calculation_index=calculation_index)

                    result_summary = ResultSummary.from_result(result=result)
                    result_dict = result_summary.model_dump()

                    result_dict.update({
                        "name": dm_name,
                        "scenario": scenario_name,
                        "calculation": calculation_name,
                    })
                    print(result_dict)
                    rows.append(result_dict)

# TODO: Wegschirjven naar bestand, opschonen, en tests schrijven voor alle toevoegingen
if __name__ == "__main__":

    directory = r"C:\Users\danie\Documents\Rekenmap"
    dm_files = get_files_by_extension(directory=directory, file_ext='.stix')
    #
    # dm = DStabilityModel()
    # dm.parse(Path(dm_files[0]['path']))
    #
    # # dm.get_slipcircle_result()  # Bishop & Uplift
    # # dm.get_slipplane_result()  # Spencer
    # print(dm.has_result(0, 0))
    # result = dm.get_result(0, 0)
    # print(getattr(result, 'Circle', None))
    # print(result.Points)
    # print(type(result).__name__)
    # print(result.FactorOfSafety)
    # print(result.SlipPlaneResults[0])
    export_results(directory)

