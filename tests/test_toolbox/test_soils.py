from unittest import TestCase

from geolib.soils.soil import ShearStrengthModelTypePhreaticLevel
from geolib.soils.soil import Soil as GLSoil

from toolbox.soils import Soil, SoilCollection


class TestSoil(TestCase):
    def setUp(self):
        """Set up a basic GEOLib soil for testing"""
        self.gl_soil = GLSoil()
        self.gl_soil.name = "test_soil"
        self.gl_soil.code = "test_soil"
        self.gl_soil.soil_weight_parameters.unsaturated_weight = 16.0
        self.gl_soil.soil_weight_parameters.saturated_weight = 18.0
        self.gl_soil.shear_strength_model_above_phreatic_level = (
            ShearStrengthModelTypePhreaticLevel.MOHR_COULOMB
        )
        self.gl_soil.shear_strength_model_below_phreatic_level = (
            ShearStrengthModelTypePhreaticLevel.MOHR_COULOMB
        )
        self.gl_soil.mohr_coulomb_parameters.cohesion.mean = 5.0
        self.gl_soil.mohr_coulomb_parameters.friction_angle.mean = 30.0
        self.gl_soil.mohr_coulomb_parameters.dilatancy_angle.mean = 0.
        self.gl_soil.undrained_parameters.shear_strength_ratio.mean = 0.25
        self.gl_soil.undrained_parameters.strength_increase_exponent.mean = 0.8

    def test_init(self):
        """Test creating a basic soil with all required attributes"""
        soil = Soil(
            gl_soil=GLSoil(name="test_soil", code="test_soil"),
            pop_mean=10.0,
            consolidation_traffic_load=50,
        )

        self.assertEqual(soil.gl_soil.name, "test_soil")
        self.assertEqual(soil.pop_mean, 10.0)
        self.assertEqual(soil.consolidation_traffic_load, 50)


class TestSoilCollection(TestCase):
    def setUp(self):
        """Set up test data for soil collection tests"""
        # Create first soil
        gl_soil1 = GLSoil()
        gl_soil1.name = "soil1"
        gl_soil1.code = "soil1"

        # Create second soil
        gl_soil2 = GLSoil()
        gl_soil2.name = "soil2"
        gl_soil2.code = "soil2"

        self.soils = [
            Soil(gl_soil=gl_soil1, pop_mean=10.0, consolidation_traffic_load=50),
            Soil(gl_soil=gl_soil2, pop_mean=15.0, consolidation_traffic_load=75),
        ]
        self.collection = SoilCollection(name="test_collection", soils=self.soils)

    def test_init(self):
        """Test creating a soil collection with multiple soils"""
        self.assertEqual(self.collection.name, "test_collection")
        self.assertEqual(len(self.collection.soils), 2)
        self.assertEqual(self.collection.soils[0].gl_soil.name, "soil1")
        self.assertEqual(self.collection.soils[1].gl_soil.name, "soil2")

    def test_get_by_name(self):
        """Test retrieving a soil by name"""
        soil = self.collection.get_by_name("soil1")
        self.assertEqual(soil.gl_soil.name, "soil1")
        self.assertEqual(soil.pop_mean, 10.0)

    def test_get_by_name_not_found(self):
        """Test that getting a non-existent soil raises an error"""
        with self.assertRaises(NameError):
            self.collection.get_by_name("nonexistent_soil")
