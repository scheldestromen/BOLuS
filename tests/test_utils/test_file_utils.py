from unittest import TestCase
from pathlib import Path
import tempfile
import shutil
from utils.file_utils import get_files_by_extension


class TestGetFilesByExtension(TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_file1 = self.temp_dir / 'test1.txt'
        self.test_file1.touch()
        self.test_file2 = self.temp_dir / 'test2.txt'
        self.test_file2.touch()
        self.test_subdir = self.temp_dir / 'subdir'
        self.test_subdir.mkdir()
        self.test_file3 = self.test_subdir / 'test3.txt'
        self.test_file3.touch()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_get_files_by_extension(self):
        files = get_files_by_extension(str(self.temp_dir), 'txt')
        self.assertEqual(len(files), 2)
        self.assertIn({"name": self.test_file1.name, "path": str(self.test_file1)}, files)
        self.assertIn({"name": self.test_file2.name, "path": str(self.test_file2)}, files)

    def test_get_files_by_extension_with_subdir(self):
        files = get_files_by_extension(str(self.temp_dir), 'txt', search_sub_dir=True)
        self.assertEqual(len(files), 3)
        self.assertIn({"name": self.test_file1.name, "path": str(self.test_file1)}, files)
        self.assertIn({"name": self.test_file2.name, "path": str(self.test_file2)}, files)
        self.assertIn({"name": self.test_file3.name, "path": str(self.test_file3)}, files)

    def test_get_files_by_extension_invalid_dir(self):
        with self.assertRaises(ValueError):
            get_files_by_extension('invalid_dir', 'txt')

    def test_get_files_by_extension_empty_extension(self):
        with self.assertRaises(ValueError):
            get_files_by_extension(str(self.temp_dir), '')
