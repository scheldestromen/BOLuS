from shapely import LineString, Point, Polygon, MultiPoint, MultiPolygon, GeometryCollection


def polygon_to_lines(polygon: Polygon) -> list[LineString]:
    # TODO: toelichting, alleen de buitenkant. aanname is geen gaten.
    return [LineString([p1, p2]) for p1, p2 in zip(polygon.exterior.coords, polygon.exterior.coords[1:])]


#TODO testen
def reduce_to_points(geometry):
    """
    Recursively reduces any geometry or collection of geometries into a flat list of points.
    Ensures no points are lost, even for deeply nested collections.
    """
    points = []
    queue = [geometry]  # Use a queue to process geometries

    while queue:
        current = queue.pop(0)  # Get the first item in the queue

        if isinstance(current, Point):
            points.append(current)
        elif isinstance(current, (LineString, Polygon)):
            # Extract points from LineString or Polygon
            coords = current.exterior.coords if isinstance(current, Polygon) else current.coords
            points.extend(Point(coord) for coord in coords)

            # Add interiors of a Polygon (holes) to the queue
            if isinstance(current, Polygon):
                queue.extend([LineString(interior.coords) for interior in current.interiors])
        elif isinstance(current, (GeometryCollection, MultiPoint, MultiPolygon)):
            # Add all geometries in the collection to the queue
            queue.extend(current.geoms)
        else:
            raise ValueError(f"Unsupported geometry type: {type(current)}")

    return points


poly1 = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
poly2 = Polygon([(1, 2), (3, 2), (3, 3), (1, 3)])

mpoly = MultiPolygon([poly1, poly2])

print(reduce_to_points(mpoly))
