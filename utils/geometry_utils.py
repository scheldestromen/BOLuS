from shapely import Point, Polygon, MultiPolygon, GeometryCollection


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
