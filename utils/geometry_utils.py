from shapely import GeometryCollection, MultiPolygon, Point, Polygon, LineString, MultiLineString, MultiPoint, LinearRing
from shapely.ops import orient
from shapely import offset_curve
from typing import Literal

import matplotlib.pyplot as plt


def geometry_to_polygons(geometry) -> list[Polygon]:
    """
    Reduces any geometry or collection of geometries into a
    flat list of Shapely Polygons.
    """
    polygons = []
    queue = [geometry]  # Use a queue to process geometries

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


def geometry_to_points(geometry) -> list[Point]:
    """
    Reduces any Shapely geometry or Shapely collection of geometries into a
    flat list of Shapely Points.
    """
    points = []
    queue = [geometry]

    while queue:
        current = queue.pop(0)

        # If the current geometry is a Point, add it to the list
        if isinstance(current, Point):
            points.append(current)

        elif isinstance(current, LinearRing):
            print([Point(x, y) for x, y in current.coords[:-1]])
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
    length = (dx**2 + dy**2) ** 0.5
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
    """Offsets a line by a given distance.

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

    # Select the higer or lower line - depending on the above_or_below argument
    if above_or_below == "above":
        offset_line_coords = max(offset_lines_coords, key=lambda lst: max(t[1] for t in lst))
    else:
        offset_line_coords = min(offset_lines_coords, key=lambda lst: min(t[1] for t in lst))

    # Make a LineString from the coordinates
    offset_line = LineString(offset_line_coords)

    return offset_line
