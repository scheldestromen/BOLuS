from enum import StrEnum, auto

from pydantic import BaseModel


class WaterLineType(StrEnum):
    HEADLINE = auto()
    REFERENCE_LINE = auto()


class HeadLine(BaseModel):
    """Represents a headline

    Attributes:
        name (str): Name (label) of the headline
        is_phreatic (bool): Indicates if the headline is the phreatic line
        l (list): list of floats for the l-coordinates
        z (list): list of floats for the z-coordinates"""

    name: str
    is_phreatic: bool
    l: list[float]
    z: list[float]


class ReferenceLine(BaseModel):
    """Represents a reference line. Headline can be assigned to it.

    Attributes:
        name (str): Name (label) of the reference line
        l (list): list of floats for the l-coordinates
        z (list): list of floats for the z-coordinates
        head_line_top (str): Head at top of reference line is based on the headline with this name
        head_line_bottom (str): Head at bottom of reference line is based on the headline with this name
    """

    name: str
    l: list[float]
    z: list[float]
    head_line_top: str
    head_line_bottom: str


class Waternet(BaseModel):
    """Represents the waternet for a stage in a D-Stability calculation

    Attributes:
        calc_name (str): Name of the calculation it belongs to
        scenario_name (str): Name of the scenario it belongs to
        stage_name (str): Name of the stage it belongs to
        head_lines (list[HeadLine]): List of HeadLine
        ref_lines (list[ReferenceLine]): List of ReferenceLine
    """

    calc_name: str
    scenario_name: str
    stage_name: str
    head_lines: list[HeadLine]
    ref_lines: list[ReferenceLine]


class WaternetCollection(BaseModel):
    waternets: list[Waternet]

    def get_waternet(
        self, calc_name: str, scenario_name: str, stage_name: str
    ) -> Waternet:
        """Returns the waternet with the given calc_name, scenario_name and stage_name

        Args:
            calc_name: The name of the calculation
            scenario_name: The name of the scenario
            stage_name: The name of the stage

        Returns:
            The waternet with the given calc_name, scenario_name and stage_name"""

        waternet = next(
            (
                waternet
                for waternet in self.waternets
                if waternet.calc_name == calc_name
                and waternet.scenario_name == scenario_name
                and waternet.stage_name == stage_name
            ),
            None,
        )
        if waternet:
            return waternet

        raise ValueError(
            f"Could not find waternet with calc_name {calc_name}, scenario_name {scenario_name} "
            f"and stage_name {stage_name}"
        )
