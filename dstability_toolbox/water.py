from typing import Optional

from pydantic import BaseModel
from enum import StrEnum, auto


class WaterLineType(StrEnum):
    HEADLINE = auto()
    REFERENCE_LINE = auto()


class HeadLine(BaseModel):
    name: str
    is_phreatic: bool
    l: list[float]
    z: list[float]


class ReferenceLine(BaseModel):
    name: str
    l: list[float]
    z: list[float]
    head_line_top: str
    head_line_bottom: str


class Waternet(BaseModel):
    calc_name: str
    scenario_name: str
    stage_name: str
    head_lines: list[HeadLine]
    ref_lines: list[ReferenceLine]


class WaternetCollection(BaseModel):
    waternets: list[Waternet]

    @classmethod
    def from_dict(cls, waternets_dict: dict, name_phreatic_line: str):
        """Parse from dict."""
        def parse_head_lines(lines: list[dict], name_phreatic_line: str):
            head_lines = []

            for line in lines:
                if line['type'] == WaterLineType.HEADLINE:
                    head_lines.append(HeadLine(
                        name=line['line_name'],
                        is_phreatic=line['line_name'] == name_phreatic_line,
                        l=line['values'][0::2],
                        z=line['values'][1::2],
                    ))

            return head_lines

        def parse_ref_lines(lines):
            ref_lines = []

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

        waternets = []

        for calc_name, calc_dict in waternets_dict.items():
            for scenario_name, scenario_dict in calc_dict.items():
                for stage_name, lines in scenario_dict.items():
                    head_lines = parse_head_lines(lines, name_phreatic_line)
                    ref_lines = parse_ref_lines(lines)
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


# TODO: Hier moeten de methode/algoritme/sequences aan toegevoegd worden. Of apart, kan ook.
#  - Basis offset method raamwerk maken en daarom verder bouwen
