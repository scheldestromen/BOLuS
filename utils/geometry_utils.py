from shapely import LineString, Point, Polygon, MultiPoint, MultiPolygon, GeometryCollection, MultiLineString


def geometry_to_polygons(geometry):
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


def determine_point_in_polygon(polygon: Polygon, shift: float = 0.01) -> tuple[float, float]:
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
        A tuple of (x, y) coordinates of the point lying inside the polygon
    """
    centroid = polygon.centroid

    # Check if centroid is within the polygon
    if polygon.contains(centroid):
        return centroid.coords[0]

    # If not: get the nearest point on the polygon boundary
    distance = polygon.exterior.project(centroid)  # Distance along the line to the nearest point
    nearest_point = polygon.exterior.interpolate(distance)  # Get the nearest point geometry

    # Determine unity vector to the nearest point
    dx = nearest_point.x - centroid.x
    dy = nearest_point.y - centroid.y
    length = (dx ** 2 + dy ** 2) ** 0.5
    unit_vector = (dx / length, dy / length)

    new_point_coord = (nearest_point.x + unit_vector[0] * shift, nearest_point.y + unit_vector[1] * shift)
    new_point = Point(new_point_coord)

    if polygon.contains(new_point):
        return new_point_coord

    raise ValueError('Could not determine point in polygon')


def polygon_to_lines(polygon: Polygon) -> list[LineString]:
    """
    Converts a Shapely Polygon to a list of Shapely LineStrings
    with only two points. Only exterior lines are returned. Voids in
    polygons are ignored.
    """
    return [LineString([p1, p2]) for p1, p2 in zip(polygon.exterior.coords, polygon.exterior.coords[1:])]


def lines_to_polygon(lines: list[LineString]) -> Polygon:
    """
    Converts a list of Shapely LineStrings to a Shapely Polygon.
    The lines must form a closed polygon.
    """
    pass
    # return Polygon([line.coords for line in lines]) -> AI, controleren. Volgens mij eerst met union een linearring


# Vervallen?
# def geometry_to_points(geometry):
#     """
#     Reduces any geometry or collection of geometries into a
#     flat list of Shapely Points.
#     """
#     points = []
#     queue = [geometry]  # Use a queue to process geometries
#
#     while queue:
#         current = queue.pop(0)  # Get the first item in the queue
#
#         if isinstance(current, Point):
#             points.append(current)
#
#         elif isinstance(current, LineString):
#             # Extract points from LineString
#             points.extend(Point(coord) for coord in current.coords)
#
#         elif isinstance(current, Polygon):
#             # Extract points from the exterior of the Polygon
#             points.extend(Point(coord) for coord in current.exterior.coords)
#
#             # Add interiors of the Polygon (holes) to the queue as LineStrings
#             queue.extend([LineString(interior.coords) for interior in current.interiors])
#
#         elif isinstance(current, (GeometryCollection, MultiPoint, MultiLineString, MultiPolygon)):
#             # Add all geometries in the collection to the queue
#             queue.extend(current.geoms)
#
#         else:
#             raise ValueError(f"Unsupported geometry type: {type(current)}")
#
#     return points


# def add_points_on_line(points: list[Point], line: LineString) -> LineString:
#     """Adds """
#     pass


# def add_shared_points_to_polygon(polygon: Polygon, polygons: list[Polygon]) -> Polygon:
#     intersects = [polygon.intersection(poly) for poly in polygons]
#
#     if intersects:
#         adjacent_points = []
#
#         for intersect in intersects:
#             adjacent_points.extend(geometry_to_points(intersect))
#
#         # Poly exploderen naar lijnen
#         # Per lijnstuk punt toevoegen (wat als meerdere punten, pythagoras?)
#         # Polygon bouwen
#         # En door.
#         pass
#
#     return polygon

# TODO: Kan vervallen?

# poly1 = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
# poly2 = Polygon([(1, 2), (3, 2), (3, 3), (1, 3)])
#
# mpoly = MultiPolygon([poly1, poly2])
#
# print(geometry_to_points(mpoly))
