import numpy as np
from shapely import GeometryCollection, MultiPolygon, Point, Polygon, LineString, MultiLineString, MultiPoint, \
    LinearRing
from shapely.ops import orient
from shapely import offset_curve
from typing import Literal, Union

# Type alias for all possible Shapely geometry types
GeometryType = Union[
    Point, LineString, LinearRing, Polygon, MultiPoint, MultiLineString, MultiPolygon, GeometryCollection]


def geometry_to_polygons(geometry: GeometryType) -> list[Polygon]:
    """
    Reduces any geometry or collection of geometries into a
    flat list of Shapely Polygons.
    """
    polygons: list[Polygon] = []
    queue: list[GeometryType] = [geometry]  # Use a queue to process geometries

    while queue:
        current = queue.pop(0)  # Get the first item in the queue

        if isinstance(current, Polygon):
            # Extract points from the exterior of the Polygon
            polygons.append(current)

        elif isinstance(current, (GeometryCollection, MultiPolygon)):
            # Add all geometries in the collection to the queue
            queue.extend(current.geoms)

        else:
            continue

    return polygons


def geometry_to_points(geometry: GeometryType) -> list[Point]:
    """
    Reduces any Shapely geometry or Shapely collection of geometries into a
    flat list of Shapely Points.
    """
    points: list[Point] = []
    queue: list[GeometryType] = [geometry]

    while queue:
        current = queue.pop(0)

        # If the current geometry is a Point, add it to the list
        if isinstance(current, Point):
            points.append(current)

        elif isinstance(current, LinearRing):
            points.extend([Point(x, y) for x, y in current.coords[:-1]])  # The last point is repeated

        # If the current geometry is a line, add its points to the list
        elif isinstance(current, LineString):
            points.extend([Point(x, y) for x, y in current.coords])

        # If the current geometry is a Polygon, add its exterior and interior rings to the queue
        elif isinstance(current, Polygon):
            queue.extend([current.exterior, *current.interiors])

        # If the current geometry is a collection of geometries, add its geometries to the queue
        elif isinstance(current, (GeometryCollection, MultiPolygon, MultiLineString, MultiPoint)):
            queue.extend(current.geoms)

        else:
            raise ValueError(f"Unexpected geometry type: {type(current)}")

    return points


def determine_point_in_polygon(
        polygon: Polygon, shift: float = 0.01
) -> tuple[float, float]:
    """Determines a point in a polygon.

    By default the polygon centroid is used. If the centroid is not
    within the polygon then an alternative point is used. The point
    on the polygon boundary that is closest to the centroid is
    determined. This point is then shifted in the direction of the
    polygon so that the point lies within the polygon.

    Args:
        polygon: A Shapely Polygon
        shift: The amount to shift the point in the direction of the
            polygon in case the centroid cannot be used.

    Returns:
        A tuple of (x, y) coordinates of the point lying inside the polygon"""

    centroid = polygon.centroid

    # Check if centroid is within the polygon
    if polygon.contains(centroid):
        return centroid.coords[0]

    # If not: get the nearest point on the polygon boundary
    distance = polygon.exterior.project(
        centroid
    )  # Distance along the line to the nearest point
    nearest_point = polygon.exterior.interpolate(
        distance
    )  # Get the nearest point geometry

    # Determine unity vector to the nearest point
    dx = nearest_point.x - centroid.x
    dy = nearest_point.y - centroid.y
    length = (dx ** 2 + dy ** 2) ** 0.5
    unit_vector = (dx / length, dy / length)

    new_point_coord = (
        nearest_point.x + unit_vector[0] * shift,
        nearest_point.y + unit_vector[1] * shift,
    )
    new_point = Point(new_point_coord)

    if polygon.contains(new_point):
        return new_point_coord

    raise ValueError("Could not determine point in polygon")


def get_polygon_top_or_bottom(polygon: Polygon, top_or_bottom: Literal["top", "bottom"]) -> LineString:
    """
    Returns the top or bottom side of a polygon as a LineString.

    The top or bottom side of a polygon is defined as the line part that 
    starts with the lowest or highest x coordinate and ends with the highest or lowest x coordinate.

    Args:
        polygon: A Shapely Polygon
        top_or_bottom: Whether to get the top or bottom side of the polygon

    Returns:
        A Shapely LineString"""

    # Orient the polygon so that the points are in clockwise order
    orient_polygon = orient(polygon, sign=-1)

    # Get the points of the polygon from the exterior - skip the last point (same as first point)
    poly_points = [(p[0], p[1]) for p in list(orient_polygon.exterior.coords)][:-1]

    # Determine the outer x-coordinates
    x_min = min([p[0] for p in poly_points])
    x_max = max([p[0] for p in poly_points])

    # Get the points on the x_min line and sort them by y-coordinate
    x_min_points = sorted([p for p in poly_points if p[0] == x_min], key=lambda p: p[1])
    x_max_points = sorted([p for p in poly_points if p[0] == x_max], key=lambda p: p[1])

    # Get the highest point on x_min and x_max
    if top_or_bottom == "top":
        start = x_min_points[-1]
        end = x_max_points[-1]

    # Get the lowest point on x_min and x_max
    # Start is now the lowest point on x_max, because the direction is clockwise
    else:
        start = x_max_points[0]
        end = x_min_points[0]

    # Get the index of the start of the top or bottom side
    i_start = poly_points.index(start)

    # Sort the points so that the start is the first in the list
    poly_points = poly_points[i_start:] + poly_points[:i_start]

    # Get the index of the end of the top or bottom side
    i_end = poly_points.index(end)

    # Now get the points from the start to the end
    side_points = poly_points[: i_end + 1]

    # Create the top or bottom side
    side = LineString(side_points)

    return side


def offset_line(line: LineString, offset: float, above_or_below: Literal["above", "below"]) -> LineString:
    """Offsets a line by a given distance. The offset is applied perpendicular
    to the given LineString. If the ends of the LineString are non-horizontal
    then the resulting LineString will have bounds not equal to the given LineString.

    Args:
        line: A Shapely LineString
        offset: The distance to offset the line
        above_or_below: Whether to offset the line above or below the line. This
          is determined by looking at the maximum y-coordinate (vertical axis) of the line.

    Returns: 
        A Shapely LineString"""

    offset_line_strings = [
        offset_curve(line, distance=offset)
        for offset in [offset, -offset]
    ]
    offset_lines_coords = [
        [(p[0], p[1]) for p in line.coords]
        for line in offset_line_strings
    ]

    # Select the higher or lower line - depending on the above_or_below argument
    if above_or_below == "above":
        offset_line_coords = max(offset_lines_coords, key=lambda lst: max(t[1] for t in lst))
    else:
        offset_line_coords = min(offset_lines_coords, key=lambda lst: min(t[1] for t in lst))

    # Make a LineString from the coordinates
    offset_line = LineString(offset_line_coords)

    return offset_line


def point_is_redundant(
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float],
        tolerance: float
) -> bool:
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3

    # Avoid division by zero (vertical line)
    if x3 == x1:
        return abs(x2 - x1) < tolerance

    # Interpolate p2's expected coordinates between p1 and p3
    t = (x2 - x1) / (x3 - x1)
    expected_y = y1 + t * (y3 - y1)

    # Compare actual vs expected
    return abs(y2 - expected_y) < tolerance


def simplify_line(
        x: list[float],
        y: list[float],
        tolerance: float
) -> tuple[list[float], list[float]]:
    """Simplifies a line by reducing the number of points.

    Per set of three points it is checked if the middle point is 
    necessary. This is checked by comparing the actual y-coordinate 
    of the middle point with a calculated y-coordinate of a linear 
    interpolation between the first and last point at the x-coordinate
    of the middle point. If the difference is smaller than the tolerance,
    the middle point is removed.

    Args:
        x: The x-coordinates of the line
        y: The y-coordinates of the line
        tolerance: The tolerance to simplify the line

    Returns:

        A tuple of (x, y) coordinates of the simplified line"""
    if len(x) <= 2:
        return x, y  # Nothing to simplify

    simplified_x = [x[0]]
    simplified_y = [y[0]]

    for i in range(1, len(x) - 1):
        prev_point = (simplified_x[-1], simplified_y[-1])
        curr_point = (x[i], y[i])
        next_point = (x[i + 1], y[i + 1])

        if not point_is_redundant(p1=prev_point, p2=curr_point, p3=next_point, tolerance=tolerance):
            simplified_x.append(x[i])
            simplified_y.append(y[i])

    simplified_x.append(x[-1])
    simplified_y.append(y[-1])

    return simplified_x, simplified_y


def linear_interpolation(
        x: float,
        xp: list[float],
        fp: list[float]
) -> float:
    """Performs linear interpolation on a list of x and y coordinates.
    The x-coordinates must be monotonically increasing or decreasing.
    Equal values are NOT allowed.

    Args:
        x: The x-coordinate to interpolate the y-coordinate for
        xp: The x-coordinates of the line
        fp: The y-coordinates of the line

    Returns:
        The y-coordinate of the interpolated point"""

    # Check if x is within the range of xp
    if x < min(xp) or x > max(xp):
        raise ValueError(
            f"x-coordinate {x} is outside the range of x-coordinates [{min(xp)}, {max(xp)}]"
        )

    # Check if xp is monotonically increasing or decreasing
    if not np.all(np.diff(xp) > 0) and not np.all(np.diff(xp) < 0):
        raise ValueError(
            f"The x-coordinates of the line are not monotonically increasing or decreasing"
            "(equal values are allowed).\n"
            f"The x-coordinates are: {xp}\n"
            f"The y-coordinates are: {fp}"
        )

    # Sort the x and y coordinates
    xp, fp = zip(*sorted(zip(xp, fp), key=lambda p: p[0]))

    # Perform linear interpolation
    return np.interp(x, xp, fp)


def is_valid_polygon(polygon: Polygon, decimals: int = 3) -> bool:
    """Check if a polygon is valid if rounding is applied. This is done by
    checking the area after rounding all points to the given number of
    decimals. Also checks if the polygon is not empty and if it is valid
    with the shapely implementation.

    Args:
        polygon: The polygon to check
        decimals: The number of decimals to round to

    Returns:
        bool: True if the polygon is valid, False otherwise"""

    points = [(round(x, decimals), round(y, decimals)) for x, y in polygon.exterior.coords]
    rounded_polygon = Polygon(points)
    is_valid = rounded_polygon.is_valid and rounded_polygon.area != 0 and not rounded_polygon.is_empty

    return is_valid
