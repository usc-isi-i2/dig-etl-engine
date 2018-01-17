# -*- coding: utf-8 -*-
import unittest
import sys, os

sys.path.append('../../')
import json
import codecs


class TestDeleteCellValues(unittest.TestCase):
    def setUp(self):
        file_path = os.path.join(os.path.dirname(__file__), "test_data/delete_cell_input.jl")
        self.doc = json.load(codecs.open(file_path, 'r'))

    def test_delete_cell(self):




if __name__ == '__main__':
    unittest.main()
