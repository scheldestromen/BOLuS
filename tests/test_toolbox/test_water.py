from unittest import TestCase

from bolus.excel_tool import RawInputToUserInputStructure
from bolus.toolbox.waternet import (HeadLine, ReferenceLine, WaterLineType,
                                    Waternet)


class TestHeadLine(TestCase):
    def test_create_headline(self):
        """Test creating a basic headline with all required attributes"""
        HeadLine(
            name="test_headline", is_phreatic=True, l=[0.0, 1.0, 2.0], z=[0.0, 1.0, 2.0]
        )


class TestReferenceLine(TestCase):
    def test_create_reference_line(self):
        """Test creating a basic reference line with all required attributes"""
        ReferenceLine(
            name="test_ref_line",
            l=[0.0, 1.0, 2.0],
            z=[0.0, 1.0, 2.0],
            head_line_top="top_headline",
            head_line_bottom="bottom_headline",
        )


class TestWaternet(TestCase):
    def test_create_waternet(self):
        """Test creating a waternet with headlines and reflines"""
        head_lines = [
            HeadLine(
                name="headline1", is_phreatic=True, l=[0.0, 1.0, 2.0], z=[0.0, 1.0, 2.0]
            ),
            HeadLine(
                name="headline2",
                is_phreatic=False,
                l=[0.0, 1.0, 2.0],
                z=[1.0, 2.0, 3.0],
            ),
        ]
        ref_lines = [
            ReferenceLine(
                name="refline1",
                l=[0.0, 1.0, 2.0],
                z=[0.5, 1.5, 2.5],
                head_line_top="headline1",
                head_line_bottom="headline2",
            )
        ]
        self.waternet = Waternet(
            calc_name="test_calc",
            scenario_name="test_scenario",
            stage_name="test_stage",
            head_lines=head_lines,
            ref_lines=ref_lines,
        )


class TestWaternetCollection(TestCase):
    def setUp(self):
        """Set up test data for waternet collection tests"""
        self.waternets_dict = {
            "calc1": {
                "scenario1": {
                    "stage1": [
                        {
                            "type": WaterLineType.HEADLINE,
                            "line_name": "headline1",
                            "values": [0.0, 0.0, 1.0, 1.0, 2.0, 2.0],
                        },
                        {
                            "type": WaterLineType.HEADLINE,
                            "line_name": "headline2",
                            "values": [0.0, 1.0, 1.0, 2.0, 2.0, 3.0],
                        },
                        {
                            "type": WaterLineType.REFERENCE_LINE,
                            "line_name": "refline1",
                            "values": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5],
                            "head_line_top": "headline1",
                            "head_line_bottom": "headline2",
                        },
                    ]
                }
            }
        }
        self.collection = RawInputToUserInputStructure.convert_waternet_collection(
            self.waternets_dict, name_phreatic_line="headline1"
        )

    def test_create_waternet_collection(self):
        """Test creating a waternet collection from a dictionary"""

        waternet = self.collection.waternets[0]
        self.assertEqual(waternet.calc_name, "calc1")
        self.assertEqual(waternet.scenario_name, "scenario1")
        self.assertEqual(waternet.stage_name, "stage1")
        self.assertEqual(len(waternet.head_lines), 2)
        self.assertEqual(len(waternet.ref_lines), 1)

    def test_get_waternet(self):
        """Test retrieving a waternet by calc, scenario and stage names"""

        waternet = self.collection.get_waternet(
            calc_name="calc1", scenario_name="scenario1", stage_name="stage1"
        )
        self.assertEqual(waternet.calc_name, "calc1")
        self.assertEqual(waternet.scenario_name, "scenario1")
        self.assertEqual(waternet.stage_name, "stage1")

    def test_get_waternet_not_found(self):
        """Test that getting a non-existent waternet raises an error"""
        with self.assertRaises(ValueError):
            self.collection.get_waternet(
                calc_name="nonexistent", scenario_name="scenario1", stage_name="stage1"
            )
