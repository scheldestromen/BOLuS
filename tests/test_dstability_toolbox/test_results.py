import os
from pathlib import Path
from unittest import TestCase
from dstability_toolbox.results import ResultSummary, DStabilityResultExporter, results_from_dir
from geolib.models.dstability.internal import UpliftVanParticleSwarmResult, UpliftVanReliabilityResult, \
    SpencerGeneticAlgorithmResult, SpencerReliabilityResult, BishopBruteForceResult, BishopReliabilityResult
from geolib.models import DStabilityModel


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURE_DIR = os.path.join(os.path.dirname(TEST_DIR), 'fixtures')
DSTABILITY_DIR = os.path.join(FIXTURE_DIR, 'dstability')


class TestResultSummary(TestCase):
    def setUp(self):
        self.dm = DStabilityModel()
        self.dm.parse(Path(os.path.join(DSTABILITY_DIR, 'test_2.stix')))

    def test_from_result_bishop(self):
        result = self.dm.get_result(0, 0)  # 0, 0 is BishopBruteForceResult
        result_summary = ResultSummary.from_result(result=result)
        self.assertEqual(result_summary.analysis_type, 'BishopBruteForce')

    def test_from_result_bishop_reliability(self):
        result = self.dm.get_result(0, 3)  # 0, 3 is BishopReliabilityResult
        result_summary = ResultSummary.from_result(result=result)
        self.assertEqual(result_summary.analysis_type, 'BishopReliability')

    def test_from_result_bishop_no_result_brute_force(self):
        result = BishopBruteForceResult()

        result_summary = ResultSummary.from_result(result=result)
        self.assertEqual(result_summary.analysis_type, 'BishopBruteForce')
        self.assertIsNone(result_summary.sf)
        self.assertIsNone(result_summary.l_coord_1)
        self.assertIsNone(result_summary.radius_1)

    def test_from_result_bishop_no_result_reliability(self):
        result = BishopReliabilityResult()

        result_summary = ResultSummary.from_result(result=result)
        self.assertEqual(result_summary.analysis_type, 'BishopReliability')
        self.assertIsNone(result_summary.reliability_index)


    def test_from_result_uplift_van(self):
        result = self.dm.get_result(0, 1)  # 0, 1 is UpliftVanResult
        result_summary = ResultSummary.from_result(result=result)
        self.assertEqual(result_summary.analysis_type, 'UpliftVanParticleSwarm')

    def test_from_result_uplift_van_no_result_particle_swarm(self):
        result = UpliftVanParticleSwarmResult()

        result_summary = ResultSummary.from_result(result=result)
        self.assertEqual(result_summary.analysis_type, 'UpliftVanParticleSwarm')
        self.assertIsNone(result_summary.sf)
        self.assertIsNone(result_summary.l_coord_1)
        self.assertIsNone(result_summary.radius_1)

    def test_from_result_uplift_van_no_result_reliability(self):
        result = UpliftVanReliabilityResult()

        result_summary = ResultSummary.from_result(result=result)
        self.assertEqual(result_summary.analysis_type, 'UpliftVanReliability')
        self.assertIsNone(result_summary.sf)
        self.assertIsNone(result_summary.reliability_index)


    def test_from_result_spencer(self):
        result = self.dm.get_result(0, 2)  # 0, 2 is SpencerResult
        result_summary = ResultSummary.from_result(result=result)
        self.assertEqual(result_summary.analysis_type, 'SpencerGeneticAlgorithm')

    def test_from_result_spencer_no_result_genetic_algorithm(self):
        result = SpencerGeneticAlgorithmResult()

        result_summary = ResultSummary.from_result(result=result)
        self.assertEqual(result_summary.analysis_type, 'SpencerGeneticAlgorithm')
        self.assertIsNone(result_summary.sf)

    def test_from_result_spencer_no_result_reliability(self):
        result = SpencerReliabilityResult()

        result_summary = ResultSummary.from_result(result=result)
        self.assertEqual(result_summary.analysis_type, 'SpencerReliability')
        self.assertIsNone(result_summary.sf)
        self.assertIsNone(result_summary.reliability_index)
    
    def test_from_result_unknown_result(self):
        result = object()

        with self.assertRaises(ValueError):
            ResultSummary.from_result(result=result)


class TestDStabilityResultExporter(TestCase):
    """Tests the DStabilityResultExporter class
    
    Has a couple of simple integrated tests"""

    def setUp(self):
        self.dm = DStabilityModel()
        self.dm.parse(Path(os.path.join(DSTABILITY_DIR, 'test_2.stix')))

        # Temporary file
        self.temp_file = Path(os.path.join(DSTABILITY_DIR, 'test_2_results.xlsx'))
    
    def tearDown(self):
        if self.temp_file.exists():
            self.temp_file.unlink()

    def test_read_template(self):
        exporter = DStabilityResultExporter(dm_list=[self.dm])
        exporter.read_template()

    def test_write_results(self):
        exporter = DStabilityResultExporter(dm_list=[self.dm])
        exporter.read_template()
        exporter.write_results()

    def test_write_results_dm_not_serialized(self):
        exporter = DStabilityResultExporter(dm_list=[DStabilityModel()])
        exporter.read_template()

        with self.assertRaises(ValueError):
            exporter.write_results()

    def test_export_results(self):
        exporter = DStabilityResultExporter(dm_list=[self.dm])
        exporter.read_template()
        exporter.write_results()
        exporter.export_results(self.temp_file)

        self.assertTrue(self.temp_file.exists())

        # Check if the file is not empty
        self.assertGreater(self.temp_file.stat().st_size, 0)


class TestResultsFromDir(TestCase):
    """Tests the results_from_dir function"""

    def setUp(self):
        self.temp_file = Path(os.path.join(DSTABILITY_DIR, 'temp_results.xlsx'))

    def tearDown(self):
        if self.temp_file.exists():
            self.temp_file.unlink()

    def test_results_from_dir(self):
        results_from_dir(directory=DSTABILITY_DIR, output_path=self.temp_file)

        self.assertTrue(self.temp_file.exists())

        # Check if the file is not empty
        self.assertGreater(self.temp_file.stat().st_size, 0)

