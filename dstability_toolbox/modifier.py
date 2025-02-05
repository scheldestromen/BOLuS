from shapely import Point

from geolib import DStabilityModel
from geolib.geometry.one import Point as GLPoint
from geolib.models.dstability.internal import SoilCollection as GLSoilCollection
from geolib.models.dstability.states import DStabilityStatePoint, DStabilityStress
from geolib.models.dstability.loads import UniformLoad, Consolidation

from dstability_toolbox.dm_getter import get_stage_by_indices, get_waternet_by_id
from dstability_toolbox.loads import Load
from dstability_toolbox.model import Model
from dstability_toolbox.geometry import Geometry, CharPointsProfile, CharPointType, Side
from dstability_toolbox.soils import SoilCollection
from dstability_toolbox.state import StatePoint
from dstability_toolbox.subsoil import Subsoil
from dstability_toolbox.water import Waternet


def get_scenario_and_stage_index_by_label(dm: DStabilityModel, scenario: str, stage: str):
    pass


def set_geometry(geometry: Geometry, dm: DStabilityModel, scenario_index: int, stage_index: int):
    # Eerste instantie: check op bestaande geometrie, dan foutmeldingen
    # Later omgang met bestaande som: bv. door opvulmateriaal boven de gedefinieerde bodemopbouw
    pass


def add_soil_collection(soil_collection: SoilCollection, dm: DStabilityModel) -> DStabilityModel:
    """Adds the soils in the soil_collection to the DStabilityModel.
    Soils already present are kept.

    Args:
        soil_collection: The soil_collection to add to the DStabilityModel
        dm: The DStabilityModel to add the soils to

    Returns:
        The modified DStabilityModel
    """

    for soil in soil_collection.soils:
        dm.add_soil(soil.gl_soil)

    return dm


def set_subsoil(subsoil: Subsoil, dm: DStabilityModel, scenario_index: int, stage_index: int) -> DStabilityModel:
    """Adds the Subsoil to the DStabilityModel. If the geometry already has
    layers, an error is raised.

    Args:
        subsoil: The Subsoil object to add to the DStabilityModel
        dm: The DStabilityModel to add the subsoil to
        scenario_index: The index of the scenario to add the subsoil to
        stage_index: The index of the stage to add the subsoil to

    Returns:
        The modified DStabilityModel
    """
    geometry = dm._get_geometry(scenario_index=scenario_index, stage_index=stage_index)

    if geometry.Layers:
        raise ValueError(f'Geometry of scenario {scenario_index} and stage {stage_index} '
                         f'already has layers')

    for soil_polygon in subsoil.soil_polygons:
        points = soil_polygon.to_geolib_points()
        dm.add_layer(
            points=points,
            soil_code=soil_polygon.soil_type,
            scenario_index=scenario_index,
            stage_index=stage_index
        )

    return dm


def add_state_points(
        state_points: list[StatePoint],
        dm: DStabilityModel,
        scenario_index: int,
        stage_index: int
) -> DStabilityModel:
    """Adds state points to the DStabilityModel

    Args:
        state_points: The state points to add to the DStabilityModel
        dm: The DStabilityModel to add the state points to
        scenario_index: The index of the scenario to add the state points to
        stage_index: The index of the stage to add the state points to

    Returns:
        The modified DStabilityModel
    """
    subsoil = Subsoil.from_geolib(dm=dm, scenario_index=scenario_index, stage_index=stage_index)

    for state_point in state_points:
        point = Point((state_point.x, state_point.z))

        for soil_polygon in subsoil.soil_polygons:
            polygon = soil_polygon.to_shapely()

            if polygon.contains(point):
                dm.add_state_point(
                    state_point=DStabilityStatePoint(
                        layer_id=soil_polygon.dm_layer_id,
                        point=GLPoint(x=state_point.x, z=state_point.z),
                        stress=DStabilityStress(pop=state_point.pop)
                    ),
                    scenario_index=scenario_index,
                    stage_index=stage_index
                )

    return dm


def add_uniform_load(
        load: Load,
        soil_collection: SoilCollection,
        char_point_profile: CharPointsProfile,
        dm: DStabilityModel,
        scenario_index: int,
        stage_index: int
):
    """Adds a uniform load to the DStabilityModel based on the input.

    The consolidation percentages of the load are based on the soil_collection

    Args:
        load: The load to add to the DStabilityModel
        soil_collection: The soil_collection to use, containing the consolidation percentages
        char_point_profile: The CharPointsProfile to base the load position on
        dm: The DStabilityModel to add the load to
        scenario_index: The index of the scenario to add the load to
        stage_index: The index of the stage to add the load to

    Returns:
        The modified DStabilityModel
    """
    l_inward = char_point_profile.get_point_by_type(CharPointType.SURFACE_LEVEL_LAND_SIDE).l
    l_outward = char_point_profile.get_point_by_type(CharPointType.SURFACE_LEVEL_WATER_SIDE).l
    load_edge_1 = char_point_profile.get_point_by_type(load.position).l
    inward_positive = l_inward > l_outward  # Determine the direction of the l-axis

    # Determine the start and end of the load
    if (load.direction == Side.LAND_SIDE and inward_positive
            or load.direction == Side.WATER_SIDE and not inward_positive):
        load_edge_2 = load_edge_1 + load.width
    else:
        load_edge_2 = load_edge_1 - load.width

    # Depending on the profile orientation, the land side can be left or right
    # Hence the start and end are determined using min/max to ensure they are in the right order
    uniform_load = UniformLoad(
        label=load.name,
        magnitude=load.magnitude,
        angle_of_distribution=load.angle,
        start=min(load_edge_1, load_edge_2),
        end=max(load_edge_1, load_edge_2)
    )

    # Add consolidation percentages. When added, each layer must have a consolidation percentage
    subsoil = Subsoil.from_geolib(dm=dm, scenario_index=scenario_index, stage_index=stage_index)
    consolidations = []

    for soil_polygon in subsoil.soil_polygons:
        soil = soil_collection.get_by_name(soil_polygon.soil_type)
        consolidation = Consolidation(
            degree=soil.consolidation_traffic_load or 100,
            layer_id=soil_polygon.dm_layer_id
        )
        consolidations.append(consolidation)

    dm.add_load(
        load=uniform_load,
        consolidations=consolidations,
        scenario_index=scenario_index,
        stage_index=stage_index
    )


def set_waternet(waternet: Waternet, dm: DStabilityModel, scenario_index: int, stage_index: int):
    """Adds the waternet to the DStabilityModel

    If a waternet is already defined, an error is raised.

    Args:
        waternet: The waternet to add to the DStabilityModel
        dm: The DStabilityModel to add the waternet to
        scenario_index: The index of the scenario to add the waternet to
        stage_index: The index of the stage to add the waternet to

    Returns:
        The modified DStabilityModel"""

    gl_stage = get_stage_by_indices(dm=dm, scenario_index=scenario_index, stage_index=stage_index)
    gl_waternet = get_waternet_by_id(waternet_id=gl_stage.WaternetId, dm=dm)

    if gl_waternet.HeadLines or gl_waternet.ReferenceLines:
        raise ValueError(f'Waternet of scenario {scenario_index} and stage {stage_index} '
                         f'already has head lines and/or reference lines')

    # Dict to store the id's in - for adding the ref. lines later
    head_line_id_dict = {}

    # Add the headlines
    for head_line in waternet.head_lines:
        head_line_id = dm.add_head_line(
            label=head_line.name,
            points=[GLPoint(x=l, z=z) for l, z in zip(head_line.l, head_line.z)],
            is_phreatic_line=head_line.is_phreatic,
            scenario_index=scenario_index,
            stage_index=stage_index
        )
        # Store the id
        head_line_id_dict[head_line.name] = head_line_id

    # Add the reference lines
    for ref_line in waternet.ref_lines:
        dm.add_reference_line(
            label=ref_line.name,
            points=[GLPoint(x=l, z=z) for l, z in zip(ref_line.l, ref_line.z)],
            scenario_index=scenario_index,
            stage_index=stage_index,
            top_head_line_id=head_line_id_dict[ref_line.head_line_top],
            bottom_headline_id=head_line_id_dict[ref_line.head_line_bottom]
        )

    return dm


def create_d_stability_model(model: Model):
    """Creates new calculations with the given models"""
    dm = DStabilityModel()

    # Remove standard input
    dm.datastructure.soils = GLSoilCollection(Soils=[])

    # Add the soil types
    dm = add_soil_collection(model.soil_collection, dm)

    # Add the scenarios
    for i, scenario in enumerate(model.scenarios):
        # By default, a first stage is created by GEOLib
        if i == 0:
            dm.scenarios[0].Label = scenario.name
            dm.scenarios[0].Notes = scenario.notes

        else:
            dm.add_scenario(label=scenario.name, notes=scenario.notes, set_current=True)

        for j, stage in enumerate(scenario.stages):
            if j == 0:
                dm.scenarios[dm.current_scenario].Stages[0].Label = stage.name
                dm.scenarios[dm.current_scenario].Stages[0].Notes = stage.notes
            else:
                dm.add_stage(label=stage.name, notes=stage.notes, set_current=True)

            # Add subsoil
            dm = set_subsoil(
                subsoil=stage.subsoil,
                dm=dm,
                scenario_index=dm.current_scenario,
                stage_index=dm.current_stage)

            # Add state points
            if stage.state_points is not None:
                add_state_points(state_points=stage.state_points, dm=dm, scenario_index=dm.current_scenario,
                                 stage_index=dm.current_stage)

            if stage.load is not None:
                add_uniform_load(
                    load=stage.load,
                    soil_collection=model.soil_collection,
                    char_point_profile=stage.geometry.char_point_profile,
                    dm=dm,
                    scenario_index=dm.current_scenario,
                    stage_index=dm.current_stage
                )

            set_waternet(
                waternet=stage.waternet,
                dm=dm,
                scenario_index=dm.current_scenario,
                stage_index=dm.current_stage
            )

    return dm
