from shapely import LineString, Point, Polygon, MultiPoint, MultiPolygon, GeometryCollection, MultiLineString


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


#TODO testen
def geometry_to_points(geometry):
    """
    Reduces any geometry or collection of geometries into a
    flat list of Shapely Points.
    """
    points = []
    queue = [geometry]  # Use a queue to process geometries

    while queue:
        current = queue.pop(0)  # Get the first item in the queue

        if isinstance(current, Point):
            points.append(current)

        elif isinstance(current, LineString):
            # Extract points from LineString
            points.extend(Point(coord) for coord in current.coords)

        elif isinstance(current, Polygon):
            # Extract points from the exterior of the Polygon
            points.extend(Point(coord) for coord in current.exterior.coords)

            # Add interiors of the Polygon (holes) to the queue as LineStrings
            queue.extend([LineString(interior.coords) for interior in current.interiors])

        elif isinstance(current, (GeometryCollection, MultiPoint, MultiLineString, MultiPolygon)):
            # Add all geometries in the collection to the queue
            queue.extend(current.geoms)

        else:
            raise ValueError(f"Unsupported geometry type: {type(current)}")

    return points


def add_points_on_line(points: list[Point], line: LineString) -> LineString:
    """Adds """
    pass


def add_shared_points_to_polygon(polygon: Polygon, polygons: list[Polygon]) -> Polygon:
    intersects = [polygon.intersection(poly) for poly in polygons]

    if intersects:
        adjacent_points = []

        for intersect in intersects:
            adjacent_points.extend(geometry_to_points(intersect))

        # Poly exploderen naar lijnen
        # Per lijnstuk punt toevoegen (wat als meerdere punten, pythagoras?)
        # Polygon bouwen
        # En door.
        pass

    return polygon

# TODO: Kan vervallen?

poly1 = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
poly2 = Polygon([(1, 2), (3, 2), (3, 3), (1, 3)])

mpoly = MultiPolygon([poly1, poly2])

print(geometry_to_points(mpoly))
