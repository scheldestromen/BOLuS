from pydantic import BaseModel
from enum import StrEnum, auto
from typing import Any

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
        head_line_bottom (str): Head at bottom of reference line is based on the headline with this name"""

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

    @staticmethod
    def parse_head_lines(lines: list[dict[str, Any]], name_phreatic_line: str) -> list[HeadLine]:
        """Parse the head lines from the dictionary
        
        Args:
            lines (list[dict[str, Any]]): The lines to parse
            name_phreatic_line (str): The name of the phreatic line

        Returns:
            The parsed head lines"""
        
        head_lines: list[HeadLine] = []
        for line in lines:
            if line['type'] == WaterLineType.HEADLINE:
                head_lines.append(HeadLine(
                    name=line['line_name'],
                    is_phreatic=line['line_name'] == name_phreatic_line,
                    l=line['values'][0::2],
                    z=line['values'][1::2],
                ))

        return head_lines

    @staticmethod
    def parse_ref_lines(lines: list[dict[str, Any]]) -> list[ReferenceLine]:
        ref_lines: list[ReferenceLine] = []

        for line in lines:
            if line['type'] == WaterLineType.REFERENCE_LINE:
                if line['head_line_top'] is None:
                    raise ValueError(
                        f"Head line top is not set for reference line {line['line_name']}"
                    )

                if line['head_line_bottom'] is None:
                    line['head_line_bottom'] = line['head_line_top']

                ref_lines.append(ReferenceLine(
                    name=line['line_name'],
                    l=line['values'][0::2],
                    z=line['values'][1::2],
                    head_line_top=line['head_line_top'],
                    head_line_bottom=line['head_line_bottom'],
                ))

        return ref_lines

    @classmethod
    def from_dict(cls, waternets_dict: dict[str, Any], name_phreatic_line: str) -> "WaternetCollection":
        """Parse from dict
        
        Args:
            waternets_dict (dict[str, Any]): The dictionary to parse
            name_phreatic_line (str): The name of the phreatic line

        Returns:
            The parsed WaternetCollection"""

        waternets: list[Waternet] = []

        for calc_name, calc_dict in waternets_dict.items():
            for scenario_name, scenario_dict in calc_dict.items():
                for stage_name, lines in scenario_dict.items():
                    head_lines = cls.parse_head_lines(lines, name_phreatic_line)
                    ref_lines = cls.parse_ref_lines(lines)
                    waternets.append(Waternet(
                        calc_name=calc_name,
                        scenario_name=scenario_name,
                        stage_name=stage_name,
                        head_lines=head_lines,
                        ref_lines=ref_lines,
                    ))

        return cls(waternets=waternets)

    def get_waternet(self, calc_name: str, scenario_name: str, stage_name: str) -> Waternet:
        """Returns the waternet with the given calc_name, scenario_name and stage_name

        Args:
            calc_name: The name of the calculation
            scenario_name: The name of the scenario
            stage_name: The name of the stage

        Returns:
            The waternet with the given calc_name, scenario_name and stage_name"""

        waternet = next(
            (waternet for waternet in self.waternets
             if waternet.calc_name == calc_name
             and waternet.scenario_name == scenario_name
             and waternet.stage_name == stage_name
             ),
            None
        )
        if waternet:
            return waternet

        raise ValueError(
            f"Could not find waternet with calc_name {calc_name}, scenario_name {scenario_name} "
            f"and stage_name {stage_name}"
        )
