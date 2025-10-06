from unittest import TestCase

from bolus.toolbox.waternet import HeadLine, ReferenceLine, Waternet


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
            head_lines=head_lines,
            ref_lines=ref_lines,
        )
