from unittest import TestCase

from utils.list_utils import get_list_item_indices


class TestGetListItemIndices(TestCase):

    def test_basic_case(self):
        li = ["derde", "tweede", "eerste"]
        di = {"first": "eerste", "second": "tweede", "third": "derde"}
        result = get_list_item_indices(li, di)
        expected = {"first": 2, "second": 1, "third": 0}

        self.assertEqual(result, expected)

    def test_empty_list(self):
        li: list[str] = []
        di = {"first": "eerste", "second": "tweede", "third": "derde"}

        with self.assertRaises(ValueError):
            get_list_item_indices(li, di)


