# -*- coding: utf-8 -*-
import unittest
import sys, os
import json
import codecs

sys.path.insert(0, '../')

from data_import.generate_mydig_config import ConfigGenerator
from data_import.generate_mydig_config import FieldProperties


class TestETKConfigKGEnhancement(unittest.TestCase):
    def setUp(self):
        self.mapping_file = os.path.join(os.path.dirname(__file__), "./test_data/test_mapping.json")

    def test_kge(self):
        spec = json.load(codecs.open(self.mapping_file, 'r'))
        gen = ConfigGenerator(spec, spec["prefix"], FieldProperties(spec))
        etk_configs = gen.generate_config_files("test_config.json", list())
        for etk_config in etk_configs:
            if etk_config['filename'] == 'test_config.json':
                ec = etk_config['etk_config']
                self.assertTrue('kg_enhancement' in ec)
                a = ec['kg_enhancement']['fields']['test_type']
                ex_a = {
                    "priority": 1,
                    "extractors": {
                        "add_constant_kg": {
                            "config": {
                                "constants": "Type A"
                            }
                        }
                    },
                    "guard": {
                        "field": "dataset_identifier",
                        "value": "privacyrights"
                    }
                }
                self.assertEqual(a, ex_a)
                b = ec['kg_enhancement']['fields']['collection']
                ex_b = {
                    "priority": 0,
                    "extractors": {
                        "add_constant_kg": {
                            "config": {
                                "constants": [
                                    "Hybrid",
                                    "Electric"
                                ]
                            }
                        }
                    },
                    "guard": {
                        "field": "dataset_identifier",
                        "value": "privacyrights"
                    }
                }
                self.assertEqual(b, ex_b)

            elif etk_config['filename'] == 'test_config_provenance.json':
                ec = etk_config['etk_config']
                self.assertTrue('kg_enhancement' in ec)
                a = ec['kg_enhancement']['fields']['test_type']
                ex_a = {
                    "priority": 0,
                    "extractors": {
                        "add_constant_kg": {
                            "config": {
                                "constants": "Nested"
                            }
                        }
                    },
                    "guard": {
                        "field": "dataset_identifier",
                        "value": "privacyrights"
                    }
                }
                self.assertEqual(a, ex_a)
            else:
                ec = etk_config['etk_config']
                self.assertTrue('kg_enhancement' not in ec)


if __name__ == '__main__':
    unittest.main()
