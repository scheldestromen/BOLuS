import unittest
from shapely import Point, Polygon, LineString, GeometryCollection, MultiPolygon, MultiPoint, MultiLineString, LinearRing
from utils.geometry_utils import (
    geometry_to_polygons,
    geometry_to_points,
    determine_point_in_polygon,
    get_polygon_top_or_bottom,
    offset_line
)


class TestGeometryUtils(unittest.TestCase):
    def test_geometry_to_polygons(self):
        point = Point(0, 0)
        line = LineString([(1, 1), (2, 2), (3, 3), (4, 4)])
        polygon = Polygon([(5, 5), (6, 6), (7, 7), (8, 8)])
        linear_ring = LinearRing([(9, 9), (10, 10), (11, 11), (12, 12)])
        multi_point = MultiPoint([Point(13, 13), Point(14, 14), Point(15, 15), Point(16, 16)])
        multi_line_string = MultiLineString([LineString([(17, 17), (18, 18), (19, 19), (20, 20)]), LineString([(21, 21), (22, 22), (23, 23), (24, 24)])])
        mpoly_1 = Polygon([(25, 25), (26, 26), (27, 27), (28, 28)])
        mpoly_2 = Polygon([(29, 29), (30, 30), (31, 31), (32, 32)])
        multi_polygon = MultiPolygon([mpoly_1, mpoly_2])
        geometry_collection = GeometryCollection([point, line, polygon, linear_ring, multi_point, multi_line_string, multi_polygon])

        result = geometry_to_polygons(geometry_collection)
        self.assertEqual(len(result), 3)
        self.assertTrue(all(isinstance(p, Polygon) for p in result))
        self.assertTrue(all(p in result for p in [polygon, mpoly_1, mpoly_2]))

    def test_geometry_to_points(self):
        point = Point(0, 0)
        line = LineString([(1, 1), (2, 2), (3, 3), (4, 4)])
        polygon = Polygon([(5, 5), (6, 6), (7, 7), (8, 8)])
        linear_ring = LinearRing([(9, 9), (10, 10), (11, 11), (12, 12)])
        multi_point = MultiPoint([Point(13, 13), Point(14, 14), Point(15, 15), Point(16, 16)])
        multi_line_string = MultiLineString([LineString([(17, 17), (18, 18), (19, 19), (20, 20)]), LineString([(21, 21), (22, 22), (23, 23), (24, 24)])])
        mpoly_1 = Polygon([(25, 25), (26, 26), (27, 27), (28, 28)])
        mpoly_2 = Polygon([(29, 29), (30, 30), (31, 31), (32, 32)])
        multi_polygon = MultiPolygon([mpoly_1, mpoly_2])
        geometry_collection = GeometryCollection([point, line, polygon, linear_ring, multi_point, multi_line_string, multi_polygon])


        result = geometry_to_points(geometry_collection)
        self.assertEqual(len(result), 33)
        expected_points = [Point(i, i) for i in range(33)]
        self.assertTrue(all(point in result for point in expected_points))

    def test_offset_line_above(self):
        line = LineString([(0, 0), (1, 0)])
        offset = 1.0
        result = offset_line(line, offset, "above")

        self.assertEqual(result, LineString([(0, 1), (1, 1)]))

    def test_offset_line_below(self):
        line = LineString([(0, 0), (1, 0)])
        offset = 1.0
        result = offset_line(line, offset, "below")

        self.assertEqual(result, LineString([(0, -1), (1, -1)]))
