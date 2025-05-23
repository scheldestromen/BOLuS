from enum import StrEnum, auto
from typing import Optional, Self

from pydantic import BaseModel, model_validator

from toolbox.geometry import CharPointType


class WaterLevelCollection(BaseModel):
    """
    The water levels are defined by a name and a value. The water levels are location dependent.
    For example, the water level at location 1 is different from the water level at location 2.

    Attributes:
        water_levels (dict[str, dict[str, float]]): The first key is the location name, the second key is the water level name
          and the value is the water level value.

          For example:
            {
                'location 1': {
                    'polder level': 1.0,
                    'mean water level': 2.0,
                    'extreme water level': 5.0,
                },
                'location 2': {
                    'polder level': 1.5,
                    'mean water level': 2.5,
                    'extreme water level': 5.5,
                }
            }"""

    water_levels: dict[str, dict[str, float | None]]

    def get_by_name(self, name: str) -> dict[str, float | None]:
        water_level_dict = self.water_levels.get(name)

        if water_level_dict is None:
            raise ValueError(f"Water level with name '{name}' not found")

        return water_level_dict


class WaterLevelConfig(BaseModel):
    """
    A WaterLevelConfig is the connection between the generalized water level variables
    used in the head_line_configs and the names of the actual water levels that should
    be used, as they are defined in the WaterLevelCollection.

    For example:
        Two generalized water level variables could be defined:
        - 'outer water level'
        - 'inner water level'

        The waternet scenario 'daily conditions' could use two water levels:
        - 'mean water level'
        - 'polder level'

        The WaterLevelConfig could be defined as follows:

            WaterLevelConfig(
                name_waternet_scenario='daily conditions',
                water_levels={
                    'outer water level': 'mean water level',
                    'inner water level': 'polder level'
                }
            )"""

    name_waternet_scenario: str
    water_levels: dict[str, str | None]


class HeadLineMethodType(StrEnum):
    """
    Enum defining the type of head line method."""

    OFFSETS = auto()
    INTERPOLATE_FROM_WATERNET = auto()


class RefLineMethodType(StrEnum):
    """
    Enum defining the type of ref line method."""

    OFFSETS = auto()
    INTRUSION = auto()
    AQUIFER = auto()
    INTERMEDIATE_AQUIFER = auto()


# TODO: Zou gesplitst kunnen worden per methode (net als bij ref. line zou moeten)
class HeadLineConfig(BaseModel):
    name_head_line: str
    is_phreatic: bool
    head_line_method_type: HeadLineMethodType
    offset_method_name: Optional[str] = None
    interpolate_from_waternet_name: Optional[str] = None
    apply_minimal_surface_line_offset: Optional[bool] = None
    minimal_surface_line_offset: Optional[float] = None
    minimal_offset_from_point: Optional[CharPointType] = None
    minimal_offset_to_point: Optional[CharPointType] = None

    @model_validator(mode='after')
    def validate_head_line_method(self) -> Self:
        if self.head_line_method_type == HeadLineMethodType.OFFSETS and self.offset_method_name is None:
            raise ValueError(
                f"An offset method needs to be specified when the headline method is {HeadLineMethodType.OFFSETS}")

        return self

    @model_validator(mode='after')
    def validate_interpolate_from_waternet_name(self) -> Self:
        if self.head_line_method_type == HeadLineMethodType.INTERPOLATE_FROM_WATERNET:
            if self.interpolate_from_waternet_name is None:
                raise ValueError(
                    f"A waternet name needs to be specified when the headline method is {HeadLineMethodType.INTERPOLATE_FROM_WATERNET}"
                    f"This is not the case for the headline '{self.name_head_line}'"
                    )

        return self

    @model_validator(mode='after')
    def validate_minimal_surface_line_offset(self) -> Self:
        if self.apply_minimal_surface_line_offset and not self.is_phreatic:
            raise ValueError("A minimal surface line offset can only be applied to a phreatic line")

        if self.apply_minimal_surface_line_offset:
            if self.minimal_surface_line_offset is None:
                raise ValueError("A value for the minimal surface line offset needs to "
                                 "be specified when the apply_minimal_surface_line_offset is True")

            if self.minimal_offset_from_point is None or self.minimal_offset_to_point is None:
                raise ValueError("Two characteristic points need to be specified when "
                                 "applying a minimal offset of the phreatic line from the surface line")

        return self


# TODO: Eigenlijk zou dit een baseclass moeten zijn, en zou deze subclasses moeten maken, dan kunnen de validaties gedeeltelijk vervallen
#       (nice-to-have)
class ReferenceLineConfig(BaseModel):
    name_ref_line: str
    name_head_line_top: Optional[str] = None
    name_head_line_bottom: Optional[str] = None
    ref_line_method_type: RefLineMethodType
    offset_method_name: Optional[str] = None
    intrusion_from_ref_line: Optional[str] = None
    intrusion_length: Optional[float] = None

    @model_validator(mode='after')
    def validate_ref_line_method(self) -> Self:
        if self.ref_line_method_type == RefLineMethodType.OFFSETS and self.offset_method_name is None:
            raise ValueError(
                f"An offset method needs to be specified when the ref line method is {RefLineMethodType.OFFSETS}")

        if self.ref_line_method_type == RefLineMethodType.INTRUSION:
            if self.intrusion_length is None:
                raise ValueError(f"An intrusion length needs to be specified when the reference line "
                                 f"placement method is {RefLineMethodType.INTRUSION}. This is not the case "
                                 f"for the reference line '{self.name_ref_line}'")

            if self.intrusion_length == 0:
                raise ValueError(f"The intrusion length cannot be 0 when the reference line "
                                 f"placement method is {RefLineMethodType.INTRUSION}. This is the case "
                                 f"for the reference line '{self.name_ref_line}'")

            if  self.intrusion_from_ref_line is None:
                raise ValueError(f"A reference line needs to be specified when the reference line "
                                 f"placement method is {RefLineMethodType.INTRUSION}. This is not the case "
                                 f"for the reference line '{self.name_ref_line}'")

        return self

    @model_validator(mode='after')
    def validate_min_one_head_line_name(self) -> Self:
        if self.name_head_line_top is None and self.name_head_line_bottom is None:
            raise ValueError(f"At least one head line needs to be assigned to the reference line "
                             f"'{self.name_ref_line}'")

        return self


class WaternetConfig(BaseModel):
    """A WaternetConfig is the blueprint for creating a waternet. At least a 
    phreatic line is required.

    Attributes:
        name (str): The name of the waternet configuration
        water_level_config (WaterLevelConfig): The water level configuration.
          This is the connection between the water levels used in the waternet and
          the generalized water level variables used in the head_line_configs.
        head_line_configs (list[HeadLineConfig]): The head line configurations.
          These are the methods for creating the head lines.
        reference_line_configs (list[ReferenceLineConfig]): The reference line configurations.
          These are the methods for creating the reference lines. This is optional
          if there is only a phreatic line.
    """

    name_waternet_scenario: str
    water_level_config: WaterLevelConfig
    head_line_configs: list[HeadLineConfig]
    reference_line_configs: Optional[list[ReferenceLineConfig]] = None  # Optional - if there is only a phreatic line

    @model_validator(mode='after')
    def validate_unique_names(self) -> Self:
        names = [config.name_head_line for config in self.head_line_configs]
        duplicates = [name for name in names if names.count(name) > 1]
        duplicates = list(set(duplicates))

        if len(duplicates):
            raise ValueError("There can only be one head line per scenario with the same name. This is not the case for the waternet scenario "
                             f"'{self.name_waternet_scenario}'. Duplicates names: {', '.join(duplicates)}")

        if self.reference_line_configs is not None:
            names = [config.name_ref_line for config in self.reference_line_configs]
            duplicates = [name for name in names if names.count(name) > 1]
            duplicates = list(set(duplicates))

            if len(duplicates):
                raise ValueError("There can only be one reference line per scenario with the same name. This is not the case for the waternet scenario "
                                 f"'{self.name_waternet_scenario}'. Duplicates names: {', '.join(duplicates)}")

        return self

    @model_validator(mode='after')
    def validate_head_line_assignment(self) -> Self:
        head_lines_configs = [hlc.name_head_line for hlc in self.head_line_configs if not hlc.is_phreatic]

        if self.reference_line_configs is not None:
            assigned_head_line_names = [config.name_head_line_top for config in self.reference_line_configs]
            assigned_head_line_names.extend([config.name_head_line_bottom for config in self.reference_line_configs])
        else:
            assigned_head_line_names = []

        non_assigned_head_line_names = set(head_lines_configs) - set(assigned_head_line_names)

        if len(non_assigned_head_line_names) > 0:
            raise ValueError("There are head lines that are not assigned to a reference line. "
                             f"This is the case for the head lines '{', '.join(non_assigned_head_line_names)}' "
                             f"in the waternet scenario '{self.name_waternet_scenario}'")

        return self

    @model_validator(mode='after')
    def validate_intrusion_from_ref_line_excists(self) -> Self:
        if self.reference_line_configs is not None:
            ref_line_names_referenced = [
                config.intrusion_from_ref_line for config in self.reference_line_configs
                if config.ref_line_method_type == RefLineMethodType.INTRUSION
                ]
            ref_line_names = [config.name_ref_line for config in self.reference_line_configs]

            for ref_line_name in ref_line_names_referenced:
                if ref_line_name not in ref_line_names:
                    raise ValueError(
                        f"The ref. line '{ref_line_name}' is referenced by an intrusion method, "
                        f"but is not defined in the reference line configs")

        return self

    @model_validator(mode='after')
    def validate_amount_of_phreatic_lines(self) -> Self:
        phreatic_lines = [config for config in self.head_line_configs if config.is_phreatic]

        if len(phreatic_lines) == 0:
            raise ValueError("There must be at least a phreatic line. This is not the case for the waternet scenario "
                             f"'{self.name_waternet_scenario}'")

        if len(phreatic_lines) > 1:
            raise ValueError("There can only be one phreatic line. This is not the case for the waternet scenario "
                             f"'{self.name_waternet_scenario}'")

        return self

    @model_validator(mode='after')
    def validate_single_intrusion_ref_line_per_ref_line(self) -> Self:
        """Checks if there is only one intrusion reference line per reference line
        based on the name of the ReferenceLineConfig.

        An exception is however when the related reference line is modelled using the
        aquifer method. In that case two reference lines are made using one
        ReferenceLineConfig. In that case two intrusion reference lines are allowed,
        one below the aquifer and one above the aquifer (one for every aquifer ref. line).
        """

        if self.reference_line_configs is None:
            return self

        intrusion_from_ref_line_names = [config.intrusion_from_ref_line for config in self.reference_line_configs
                                         if config.ref_line_method_type == RefLineMethodType.INTRUSION]

        # Get duplicate names
        duplicate_names = set([name for name in intrusion_from_ref_line_names
                               if intrusion_from_ref_line_names.count(name) > 1])

        for dup_name in duplicate_names:
            configs = [config for config in self.reference_line_configs
                       if config.intrusion_from_ref_line == dup_name]

            if len(configs) == 2:
                from_ref_line_config = next(
                    conf for conf in self.reference_line_configs
                    if conf.name_ref_line == configs[0].intrusion_from_ref_line
                    )
                from_ref_line_is_aquifer = (from_ref_line_config.ref_line_method_type == RefLineMethodType.AQUIFER
                                            or from_ref_line_config.ref_line_method_type == RefLineMethodType.INTERMEDIATE_AQUIFER)
                intrusion_opposite_direction = configs[0].intrusion_length * configs[1].intrusion_length < 0

                if from_ref_line_is_aquifer and intrusion_opposite_direction:
                    continue

            raise ValueError(
                "There can only be one intrusion ref. line per ref. line, or two in case "
                "of an aquifer method."
                f"This is not the case for the waternet scenario '{self.name_waternet_scenario}' "
                f"and the reference line '{configs[0].intrusion_from_ref_line}', "
                f"which is used more than allowed")

        return self

    @model_validator(mode='after')
    def validate_aquifer_types(self) -> Self:
        ref_line_aquifer = [config for config in self.reference_line_configs
                            if config.ref_line_method_type == RefLineMethodType.AQUIFER]
        ref_line_intermediate_aquifer = [config for config in self.reference_line_configs
                                        if config.ref_line_method_type == RefLineMethodType.INTERMEDIATE_AQUIFER]

        if len(ref_line_aquifer) > 1:
            raise ValueError("There can only be one aquifer ref. line. This is not the case for the waternet scenario "
                             f"'{self.name_waternet_scenario}'")

        if len(ref_line_intermediate_aquifer) > 1:
            raise ValueError("There can only be one intermediate aquifer ref. line. This is not the case for the waternet scenario "
                             f"'{self.name_waternet_scenario}'")

        if len(ref_line_intermediate_aquifer) == 1 and len(ref_line_aquifer) == 0:
            raise ValueError("There must be an aquifer ref. line when there is an intermediate aquifer ref. line. "
                             f"This is not the case for the waternet scenario '{self.name_waternet_scenario}'")

        return self


class WaternetConfigCollection(BaseModel):
    waternet_configs: list[WaternetConfig]

    def get_by_name(self, name: str) -> WaternetConfig:
        waternet_config = next((config for config in self.waternet_configs if config.name_waternet_scenario == name),
                               None)

        if waternet_config is None:
            raise ValueError(f"Waternet config with name '{name}' not found")

        return waternet_config
