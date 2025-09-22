from typing import Optional, Self

from geolib import DStabilityModel
from geolib.geometry.one import Point as GLPoint
from geolib.models.dstability.internal import PersistableLayer
from pydantic import BaseModel, model_validator
from shapely.geometry import Polygon, LineString, GeometryCollection, MultiPolygon
from shapely.ops import split

from toolbox.geolib_utils import get_by_id
from toolbox.geometry import SurfaceLine, CharPointType, CharPointsProfile
from utils.geometry_utils import geometry_to_polygons, is_valid_polygon


# TODO: Zou mooi zijn om een baseclass voor collections te maken. Dan
#  moeten de collections allen de attribute items hebben, en de items de attribute name.
#  - Eénmaal implementeren van get_by_name (indien a)
#  - Eénmaal implementeren van check op dubbele namen

# TODO: "Blueprint" is eigenlijk wat elders "Config" heet.

class SoilLayer(BaseModel):
    """Representation of a 1D soil layer"""

    soil_type: str
    top: float
    is_aquifer: Optional[bool] = None


# Nice-to-have: onderkant van grondprofiel toevoegen
class SoilProfile(BaseModel):
    """Representation of a 1D soil profile"""

    name: str
    layers: list[SoilLayer]

    @model_validator(mode="after")
    def check_descending_tops(self) -> Self:
        tops = [layer.top for layer in self.layers]

        if tops != sorted(tops, reverse=True):
            raise ValueError(
                f"The soil layers in the soil profile {self.name} are not in descending order. "
                f"Make sure each top is lower than the previous one."
            )

        return self


class SoilProfilePosition(BaseModel):
    """Represents the position of a soil profile in the subsoil in
    a 2D cross-section. The l-coordinate is the horizontal coordinate

    Attributes:
        profile_name (str): The name of the soil profile
        l_coord (float): The l-coordinate of the soil profile"""

    profile_name: str
    l_coord: float | None


class SoilProfilePositionSet(BaseModel):
    """Represents the SoilProfilePosition instances belonging to
    one subsoil schematization of (multiple) SoilProfile instances.

    Attributes:
        set_name (str): name of the set
        soil_profile_positions (list[SoilProfilePosition]): SoilProfilePositions belonging
          to the set."""

    set_name: str
    soil_profile_positions: list[SoilProfilePosition]

    def get_by_name(self, name: str) -> SoilProfilePosition:
        """Returns the SoilProfilePosition with the given name"""

        position = next((pos for pos in self.soil_profile_positions if pos.profile_name == name), None)

        if position:
            return position
        else:
            raise ValueError(f"Could not find soil profile position with name '{name}'")


class SoilProfilePositionSetCollection(BaseModel):
    """Collection of soil profile positions

    Attributes:
        sets (list[SoilProfilePositionSet]): List of SoilProfilePosition instances"""

    sets: list[SoilProfilePositionSet]

    def get_by_name(self, name: str) -> SoilProfilePositionSet:
        """Returns the SoilProfilePositionSet with the given name"""

        position_set = next((set for set in self.sets if set.set_name == name), None)

        if position_set:
            return position_set
        else:
            raise ValueError(f"Could not find soil profile position set with name '{name}'")


class SoilProfileCollection(BaseModel):
    """Collection of 1D soil profiles of type SoilProfile"""

    profiles: list[SoilProfile]

    def get_by_name(self, name: str) -> SoilProfile:
        """Returns the SoilProfile with the given name"""

        profile = next((prof for prof in self.profiles if prof.name == name), None)

        if profile:
            return profile
        else:
            raise ValueError(f"Could not find soil profile with name '{name}'")


class SoilPolygon(BaseModel):
    """Representation of a 2D soil layer

    Attributes:
        soil_type (str): Type of the soil
        points (list): List of tuples each representing 2D-coordinates
        dm_layer_id (str): Optional. The id of the layer in de DStabilityModel it belongs to.
          It is needed for adding state points and consolidations percentages related 
          to uniform loads.
        is_aquifer (bool): Optional. Whether the soil polygon is an aquifer. This is 
          required when generating the waternets (pore water pressures) using the subsoil.
          This attribute is ignored when using the methods from_geolib_layer, from_shapely 
          or from_shapely since this attribute is not present in the input or output of these methods.
    """

    soil_type: str
    points: list[tuple[float, float]]
    dm_layer_id: Optional[str] = None
    is_aquifer: Optional[bool] = None

    @classmethod
    def from_geolib_layer(cls, gl_layer: PersistableLayer, soil_type: str) -> Self:
        """Creates a SoilPolygon from a GEOLib PersistableLayer"""

        points = [(point.X, point.Z) for point in gl_layer.Points]
        return cls(soil_type=soil_type, points=points, dm_layer_id=gl_layer.Id)

    def to_geolib_points(self) -> list[GLPoint]:
        """Returns a list of GEOLib points"""
        gl_points = [GLPoint(x=x, z=z) for x, z in self.points]
        return gl_points

    @classmethod
    def from_shapely(cls, soil_type: str, polygon: Polygon) -> Self:
        """Creates a SoilPolygon from a Shapely Polygon"""

        if not isinstance(polygon, Polygon):
            raise ValueError(
                f"Input must be a Shapely Polygon but is of type {type(polygon)}"
            )

        points = list(polygon.exterior.coords)[:-1]  # Remove the repeated first point
        return cls(soil_type=soil_type, points=points)

    def to_shapely(self) -> Polygon:
        """Creates a Shapely Polygon from the SoilPolygon"""
        return Polygon(self.points)


class Subsoil(BaseModel):
    """Representation of a 2D subsoil schematization. This is a collection of (multiple)
    SoilPolygon's belonging to the same cross-sectional schematization.

    There is no check on whether soil polygons are overlapping.
    This should be implemented.

    Attributes:
        soil_polygons (list): List of SoilPolygon instances"""

    soil_polygons: list[SoilPolygon]
    name: str = ""

    @classmethod
    def from_geolib(
        cls, dm: DStabilityModel, scenario_index: int, stage_index: int
    ) -> Self:
        soil_layers = dm._get_soil_layers(
            scenario_index=scenario_index, stage_index=stage_index
        )
        geometry = dm._get_geometry(
            scenario_index=scenario_index, stage_index=stage_index
        )

        soil_polygons: list[SoilPolygon] = []

        for soil_layer in soil_layers.SoilLayers:
            soil = get_by_id(collection=dm.soils.Soils, item_id=soil_layer.SoilId)
            layer = geometry.get_layer(id=soil_layer.LayerId)

            soil_polygon = SoilPolygon.from_geolib_layer(
                soil_type=soil.Code, gl_layer=layer
            )
            soil_polygons.append(soil_polygon)

        return cls(soil_polygons=soil_polygons)

    def remove_soil_polygons(self, remove_polygons: list[SoilPolygon]) -> None:
        """Substracts a polygon from the subsoil. This is done by 'clipping' the subsoil
        polygon with the polygon to substract. This is needed for adding soil layers 
        to the subsoil that overlap with the subsoil, like a revetment layer.

        This method modifies the subsoil in place.

        Args:
            remove_polygons (list[SoilPolygon]): The polygons to remove"""

        # Create a new list to store the modified polygons
        new_soil_polygons: list[SoilPolygon] = []

        for soil_polygon in self.soil_polygons:
            soil_polygon_shapely = soil_polygon.to_shapely()

            should_keep = True
            for polygon in remove_polygons:
                polygon_shapely = polygon.to_shapely()

                if soil_polygon_shapely.intersects(polygon_shapely):
                    should_keep = False
                    clipped_polygon = soil_polygon_shapely.difference(polygon_shapely)

                    # Handle different geometry types
                    if isinstance(clipped_polygon, (GeometryCollection, MultiPolygon)):
                        for geom in clipped_polygon.geoms:
                            if isinstance(geom, Polygon) and is_valid_polygon(geom):
                                new_soil_polygon = SoilPolygon.from_shapely(
                                    soil_type=soil_polygon.soil_type, polygon=geom
                                )
                                new_soil_polygons.append(new_soil_polygon)

                    elif isinstance(clipped_polygon, Polygon) and is_valid_polygon(clipped_polygon):
                        new_soil_polygon = SoilPolygon.from_shapely(
                            soil_type=soil_polygon.soil_type, polygon=clipped_polygon
                        )
                        new_soil_polygons.append(new_soil_polygon)
                    break  # No need to check other layers once we've clipped this polygon

            # If the polygon wasn't clipped, keep it
            if should_keep:
                new_soil_polygons.append(soil_polygon)

        # Replace the old list with the new one
        self.soil_polygons = new_soil_polygons

    def get_bottom(self) -> float:
        """Returns the minimim z-coordinate of the subsoil"""

        return min(point[1] for polygon in self.soil_polygons for point in polygon.points)


class SubsoilCollection(BaseModel):
    """Collection of subsoils"""

    subsoils: list[Subsoil]

    def from_dms(
        self,
        dm_list: list[DStabilityModel],
        scenario_index: int,
        stage_index: int
    ) -> Self:
        """Creates a SubsoilCollection from a list of DStabilityModels"""

        for dm in dm_list:
            subsoil = Subsoil.from_geolib(dm=dm, scenario_index=scenario_index, stage_index=stage_index)
            self.subsoils.append(subsoil)

        return self

    def get_by_name(self, name: str) -> Subsoil:
        """Returns the Subsoil with the given name"""

        subsoil = next((subsoil for subsoil in self.subsoils if subsoil.name == name), None)

        if subsoil:
            return subsoil
        else:
            raise ValueError(f"Could not find subsoil with name '{name}'")


class RevetmentLayer(BaseModel):
    """Representation of a revetment layer. This is a layer at the surface level,
    parallel to the surface line, with a certain thickness. This can represent 
    the clay revetment or a road construction.
    
    Attributes:
        soil_type (str): The type of soil (soil_code in D-Stability) of the revetment layer
        thickness (float): The thickness of the revetment layer
        l_coords (tuple[float, float]): The l-coordinates of the revetment layer (start and end).
          These do not have to be in order."""

    soil_type: str
    thickness: float
    l_coords: tuple[float, float]

    def to_soil_polygon(self, surface_line: SurfaceLine) -> SoilPolygon:
        """Returns a SoilPolygon instance representing the revetment layer
        
        Args:
            surface_line (SurfaceLine): The surface line of the subsoil. The surface
              should contain the l-coordinates of the points.

        Returns:
            SoilPolygon: The SoilPolygon instance representing the revetment layer
        """

        shapely_surface_line = LineString([(p.l, p.z) for p in surface_line.points])

        # Buffer the surface line by the thickness of the revetment layer
        buffer = shapely_surface_line.buffer(distance=self.thickness, cap_style='square')

        # Create a helper polygon to clip the buffered to the defined l-coordinates
        helper_top = max(p.z for p in surface_line.points) + 1
        helper_bottom = min(p.z for p in surface_line.points) - 100
        helper_left = min(self.l_coords)
        helper_right = max(self.l_coords)
        helper_polygon = Polygon(
            [
                (helper_left, helper_top),
                (helper_right, helper_top),
                (helper_right, helper_bottom),
                (helper_left, helper_bottom)
            ]
        )

        # Clip the buffered surface line to the helper polygon
        clipped_buffer = buffer.intersection(helper_polygon)  # , grid_size=1e-3

        # Split the clipped buffer by the surface line
        split_buffer = split(clipped_buffer, shapely_surface_line)

        if len(split_buffer.geoms) != 2:
            raise ValueError("Something went wrong creating a revetment layer")

        # Get the lower polygon (under the surface line). This is the revetment layer
        min_y_coord = min(p.bounds[1] for p in split_buffer.geoms)
        revetment_layer = next(p for p in split_buffer.geoms if p.bounds[1] == min_y_coord)

        if not isinstance(revetment_layer, Polygon):
            raise ValueError("Something went wrong creating a revetment layer")

        return SoilPolygon.from_shapely(soil_type=self.soil_type, polygon=revetment_layer)


class RevetmentProfile(BaseModel):
    """Representation of all the revetment layers in a subsoil.
    
    Attributes:
        name (str): The name of the revetment profile
        layers (list[RevetmentLayer]): The revetment layers in the profile"""

    layers: list[RevetmentLayer]

    def to_soil_polygons(self, surface_line: SurfaceLine) -> list[SoilPolygon]:
        """Returns a list of SoilPolygon instances representing the revetment layers
        within the subsoil."""

        soil_polygons: list[SoilPolygon] = []

        for layer in self.layers:
            soil_polygon = layer.to_soil_polygon(surface_line=surface_line)
            soil_polygons.append(soil_polygon)

        return soil_polygons


class RevetmentLayerBlueprint(BaseModel):
    """Blueprint for creating revetment layers. This acts as a factory for RevetmentLayer instances.
    
    Attributes:
        soil_type (str): The type of soil (soil_code in D-Stability) of the revetment layer
        thickness (float): The thickness of the revetment layer
        char_point_types (tuple[CharPointType, CharPointType]): The characteristic point types to use.
    """

    soil_type: str
    thickness: float
    char_point_types: tuple[CharPointType, CharPointType]

    def create_revetment_layer(self, char_point_profile: CharPointsProfile) -> RevetmentLayer:
        """Creates a concrete RevetmentLayer instance using a char_point_profile.
        
        Args:
            char_point_profile (CharPointsProfile): The profile of the characteristic points.
            
        Returns:
            RevetmentLayer: A concrete revetment layer with l_coords derived from char_points.
        """
        char_points = [char_point_profile.get_point_by_type(char_point_type)
                      for char_point_type in self.char_point_types]

        # Ensure both l coordinates are not None
        if char_points[0].l is None or char_points[1].l is None:
            raise ValueError("Characteristic points must have l-coordinates")

        l_coords = (float(char_points[0].l), float(char_points[1].l))

        return RevetmentLayer(
            soil_type=self.soil_type,
            thickness=self.thickness,
            l_coords=l_coords
        )


class RevetmentProfileBlueprint(BaseModel):
    """Blueprint for creating a revetment profile. This acts as a factory for RevetmentProfile instances.
    
    A RevetmentProfileBlueprint can be used to create many RevetmentProfile instances, while
    a RevetmentProfile has a one-to-one relationship with a subsoil.
    
    Attributes:
        name (str): The name of the revetment profile
        layer_blueprints (list[RevetmentLayerBlueprint]): The revetment layer blueprints (optional)
        layers (list[RevetmentLayer]): The concrete revetment layers (optional)"""

    name: str
    layer_blueprints: Optional[list[RevetmentLayerBlueprint]] = None

    def create_revetment_profile(self, char_point_profile: CharPointsProfile) -> RevetmentProfile:
        """Creates a revetment profile from the blueprints.
        
        Args:
            char_point_profile (CharPointsProfile): The char points profile
            
        Returns:
            RevetmentProfile: The revetment profile instance
        """
        if not self.layer_blueprints:
            raise ValueError("No layer blueprints available")

        revetment_layers = [
            blueprint.create_revetment_layer(char_point_profile)
            for blueprint in self.layer_blueprints
            ]

        return RevetmentProfile(layers=revetment_layers)


class RevetmentProfileBlueprintCollection(BaseModel):
    """Collection of revetment profile blueprints
    
    Attributes:
        profile_blueprints (list[RevetmentProfileBlueprint]): The revetment profile blueprints in the collection"""

    profile_blueprints: list[RevetmentProfileBlueprint]

    def get_by_name(self, name: str) -> RevetmentProfileBlueprint:
        """Returns the RevetmentProfileBlueprint with the given name"""

        profile_blueprint = next(
            (profile_blueprint for profile_blueprint in self.profile_blueprints if profile_blueprint.name == name),
            None
            )
        if profile_blueprint:
            return profile_blueprint
        else:
            raise ValueError(f"Could not find revetment profile blueprint with name '{name}'")


def subsoil_from_soil_profiles(
    surface_line: SurfaceLine,
    soil_profiles: list[SoilProfile],
    transitions: Optional[list[float]] = None,
    thickness_bottom_layer: float = 1,
    min_soil_profile_depth: Optional[float] = None,
) -> Subsoil:
    """Creates an instance of Subsoil from one or more SoilProfile objects.

    Args:
        surface_line: SurfaceLine object
        soil_profiles: One or more SoilProfile objects
        transitions: List of transition l-coordinates. Optional in case of single profile.
          Must be in ascending order and of length len(soil_profiles) - 1
        thickness_bottom_layer: The layer thickness of the bottom layer. Defaults to 1 m.
          The layer bottoms are determined by the layer underneath, but the bottom layer
          of a SoilProfile does not have that.
        min_soil_profile_depth: (Optional) The minimum depth of a SoilProfile. If the SoilProfile
          is shallower than this value, the SoilProfile is extended to this depth.

    """
    if transitions is None:
        transitions = []

    # Perform checks
    if len(soil_profiles) == 0:
        raise ValueError("At least one soil profile must be provided")

    if len(transitions) != len(soil_profiles) - 1:
        raise ValueError(
            "The number of soil profiles does not match the number of transitions"
        )

    if transitions != sorted(transitions):
        raise ValueError(
            "The transitions of the soil profiles are not in ascending order"
        )

    surface_line.check_l_coordinates_present()
    l_coords: list[float] = [p.l for p in surface_line.points]  # type: ignore

    # Determine the bounds of the soil profiles, which are the given transitions
    # and the minimum and maximum l-coordinates
    l_min = min(l_coords)
    l_max = max(l_coords)
    bounds = [l_min] + transitions + [l_max]

    if bounds != sorted(bounds):
        raise ValueError(
            "One or more soil profile transitions lie beyond the surface line geometry."
            f"The bounds are {l_min, l_max} and the transitions are {transitions}"
        )

    geometry_points = (
        [(surface_line.points[0].l, -100)]
        + [(p.l, p.z) for p in surface_line.points]
        + [(surface_line.points[-1].l, -100)]
    )
    geometry_polygon = Polygon(geometry_points)
    soil_polygons: list[SoilPolygon] = []

    for i, soil_profile in enumerate(soil_profiles):
        left = bounds[i]
        right = bounds[i + 1]

        for j, layer in enumerate(soil_profile.layers):
            top = layer.top

            # If layer is the bottom layer then use thickness_bottom_layer and min_soil_profile_depth
            if j + 1 == len(soil_profile.layers):
                if min_soil_profile_depth is not None:
                    bottom = min(top - thickness_bottom_layer, min_soil_profile_depth)
                else:
                    bottom = top - thickness_bottom_layer
            else:
                bottom = soil_profile.layers[j + 1].top

            polygon = Polygon(
                [(left, top), (right, top), (right, bottom), (left, bottom)]
            )

            # Adjust for the surface level
            geometry = polygon.intersection(geometry_polygon)
            polygons = geometry_to_polygons(geometry)

            for polygon in polygons:
                # Check if polygon is not empty
                if not polygon.is_empty:
                    soil_polygon = SoilPolygon.from_shapely(
                        soil_type=layer.soil_type, polygon=polygon
                    )
                    soil_polygon.is_aquifer = layer.is_aquifer
                    soil_polygons.append(soil_polygon)

    subsoil = Subsoil(soil_polygons=soil_polygons)

    return subsoil


def add_revetment_profile_to_subsoil(
    subsoil: Subsoil,
    revetment_profile: RevetmentProfile,
    surface_line: SurfaceLine,
) -> Subsoil:
    """Adds a revetment profile to the subsoil.
    
    Args:
        subsoil: The subsoil to add the revetment profile to
        revetment_profile: The revetment profile to add
        surface_line: The surface line of the subsoil
    """

    # Check if l-coordinates are present in the surface line
    surface_line.check_l_coordinates_present()

    # Create soil polygons from the revetment profile and add them to the subsoil
    revetment_polygons = revetment_profile.to_soil_polygons(surface_line=surface_line)

    # Subtract the revetment polygons from the subsoil (so they don't overlap)
    subsoil.remove_soil_polygons(revetment_polygons)

    # Add the revetment polygons to the subsoil
    subsoil.soil_polygons.extend(revetment_polygons)

    return subsoil
