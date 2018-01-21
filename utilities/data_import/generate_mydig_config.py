import json
import re
import os
from optparse import OptionParser
import codecs


class Rule(object):
    """

    """

    def __init__(self, rule_spec, prefix, field_properties, path_to_nested_object=None, field_of_nested_object=None):
        """

        Args:
            rule_spec ():
            prefix(string): the prefix used to nest object in the json-lines file

        Returns: a Rule object

        """
        self.path = rule_spec["path"]
        self.field = rule_spec["field"]
        self.prefix = prefix
        self.field_properties = field_properties
        self.path_to_nested_object = path_to_nested_object
        self.field_of_nested_object = field_of_nested_object

    @staticmethod
    def make_alphanumeric_underscore(a_str):
        """
        Args:
            a_str (string): any string

        Returns: a string with all non alphanumeric chars subsituted with underscore.
        """
        return re.sub(r'\W+', '_', a_str)

    def segment_name(self):
        """
        Build the segment name for a <path> in a rule.

        Currently, all data extractors except kg_construction must get their data from segments.

        For top level objects:
        - <prefix>__<underscore_path>

        For nested objects:
        - <attribute>__<prefix>__<underscore_path>

        Returns: the segment name as a string
        """
        underscore_path = Rule.make_alphanumeric_underscore(self.path)
        if self.path_to_nested_object:
            return self.path_to_nested_object + "__" + self.prefix + "__" + underscore_path
        else:
            return self.prefix + "__" + underscore_path

    def path_to_raw_json(self):
        """
        The jsonpath to <path> in the raw json, assuming it starts at the top level object.

        For top level objects:
        - used in data_extraction to access nested json to construct the nested KG objects
          - <prefix>.<path>

        For nested objects:
        - used in content_extraction to define segments to access the data
        - this is weird, but done this way because KG construction puts the raw data
          inside content_extraction, sigh!
          - content_extraction.<attribute>.<prefix>.<path>

        Returns: a json path relative to the top level object.
        """
        if self.field_of_nested_object:
            return "content_extraction." + self.field_of_nested_object + "." + self.prefix + ".\"" + self.path + "\""
        else:
            return self.prefix + "." + self.path

    def path_to_content_extraction(self):
        """
        There are two cases to consider:
        1) If the path is being used to access raw JSON data for nested objects, then we don't need [*]
        2) If the path is used to access data to extractors, we need the [*].
        It is sad that this is so complicated, ETK needs a cleaner way to access data.

        Returns: the jsonpath to access the data corresponding to a <path>
        """

        if self.field_properties.stores_kg_nodes(self.path):
            return "content_extraction." + self.segment_name()
        else:
            return "content_extraction." + self.segment_name() + "[*]"

    def needs_content_extraction(self):
        """
        Returns: True if the rule must access its data via content extraction.
          Currently, this is true for all paths except those used in construction of nested objects
        """
        return not self.field_properties.stores_kg_nodes(self.field)

    def content_extraction(self):
        """
        Build the content extraction section for this rule.

        Returns: a dict, if the rule needs a content extraction section, or None
        """
        if self.needs_content_extraction():
            ob = {
                "input_path": self.path_to_raw_json(),
                "segment_name": self.segment_name()
            }
            return ob
        else:
            return None

    # to-do: move default extractors to an external file
    default_extractors = {
        "country": {
            "extract_using_dictionary": {
                "config": {
                    "ngrams": 3,
                    "dictionary": "countries",
                    "case_sensitive": False
                }
            }
        },
        "state": {
            "extract_using_dictionary": {
                "config": {
                    "ngrams": 3,
                    "dictionary": "states_usa_canada",
                    "case_sensitive": False
                }
            }
        },
        "states_usa_codes": {
            "extract_using_dictionary": {
                "config": {
                    "ngrams": 1,
                    "dictionary": "states_usa_codes",
                    "case_sensitive": False
                }
            }
        },
        "city_name": {
            "extract_using_dictionary": {
                "config": {
                    "ngrams": 3,
                    "dictionary": "cities",
                    "case_sensitive": False
                }
            }
        },
        "phone": {
            "extract_using_custom_spacy": {
                "config": {
                    "spacy_field_rules": "phone"
                }
            }
        },
        "email": {
            "extract_email": {
                "config": {}
            }
        },
        "stock_ticker": {
            "extract_using_custom_spacy": {
                "config": {
                    "spacy_field_rules": "stock_ticker"
                }
            }
        }
    }

    def field_specific_extractor(self):
        """
        The config generator understands the names of common fields such as city_name,
        and automatically creates a reference to the appropriate extractor if the
        field is one of the standard fields.

        To-do: an an option to not use a default extractor ignore_default_extractor: True,
        for those cases where special configuration is needed.

        Returns: a default extractor, or None
        """
        return self.default_extractors.get(self.field)

    def data_extraction(self):
        """
        Build the data extraction section for this rule.

        There are two cases to consider as they must be handled differently:

        1) For constructing nested KG nodes, the data is expected to be raw JSON.
        2) All other data extractors must get their data from content extraction.

        In addition, there are extractor-specific tricks
        Returns: a dict with the data extraction section
        """
        if self.field_properties.stores_kg_nodes(self.field):
            input_path = self.path_to_raw_json()
            extractor = {
                "create_kg_node_extractor": {
                    "config": {
                        "segment_name": self.field
                    }
                }
            }
        else:
            # the rest of the extractors go to content_extraction
            input_path = self.path_to_content_extraction()
            extractor = self.field_specific_extractor()

            # if there is no field-specific extractor, then copy the value from the content to the field
            if not extractor:
                extractor = {
                    "extract_as_is": {}
                }

        # for dates, make sure that they parse as a date
        if self.field_properties.is_date_field(self.field):
            # for now use a specific function
            # To-do: invent a way to add post-filters to any extractor, which would be more general
            self.add_parse_date_post_filter(extractor)

        fields = {
            self.field: {
                "extractors": extractor
            }
        }
        return {
            "input_path": input_path,
            "fields": fields
        }

    def add_parse_date_post_filter(self, extractor):
        """
        Add the parse_date post_filter to the extractor
        Args:
            extractor (dict): an extractor

        Returns: nothing, modifies the passed in extractor
        """
        if "extract_as_is" in extractor:
            extractor["extract_as_is"]["config"] = {
                "post_filter": "parse_date",
                "ignore_past_years": 100
            }


class ConfigGenerator(object):
    """
    A class to generate the supplemental config for each of the config sections in a mapping spec.

    The class generates several files for a single mapping spec:
    1) A file for the top level object.
       The file name is <mapping-file>-config.json
    2) One file for each of the nested objects.
       The file name is <mapping-file>-config_<attribute>.json
    """

    def __init__(self, full_config, prefix, field_properties, path_to_nested_object=None, field_of_nested_object=None):
        self.prefix = prefix
        self.config = full_config["config"]
        self.nested_configs = full_config.get("nested_configs")
        self.title = self.config.get("title")
        self.rules = list()
        self.field_properties = field_properties
        self.path_to_nested_object = path_to_nested_object
        self.field_of_nested_object = field_of_nested_object

        # To-do: add an "ignore": True, option to rule objects so that users can test
        # specific rules without having to remove them from their JSON file.
        for rule in self.config["rules"]:
            self.rules.append(
                Rule(rule,
                     self.prefix,
                     self.field_properties,
                     path_to_nested_object=self.path_to_nested_object,
                     field_of_nested_object=self.field_of_nested_object))

    def content_extraction(self):
        """
        Generate the content extraction section for a configuration.
        This method does not worry about possible nested configurations.

        Returns: the dict to insert in the etk supplemental config
        """
        entries = list()
        signatures = set()  # to prevent duplicates
        for rule in self.rules:
            ce = rule.content_extraction()
            if ce:
                signature = ce["input_path"] + "//" + ce["segment_name"]
                if signature not in signatures:
                    entries.append(ce)
                    signatures.add(signature)

        if not self.path_to_nested_object:
            self.content_extraction_for_join_fields()

        return {
            "json_content": entries
        }

    def data_extraction(self):
        """
        Generate the data extraction section for a configuration.
        This method does not worry about possible nested configurations.

        Returns: the dict to insert in the etk supplemental config
        """
        entries = list()
        for rule in self.rules:
            de = rule.data_extraction()
            if de:
                entries.append(de)
        return entries

    def kg_enhancement(self):
        priority = 0
        kge = None
        constants = self.config.get("constants")
        if constants:
            kge = {
                "fields": {},
                "input_path": "knowledge_graph.`parent`"
            }
            for constant in constants:
                if 'priority' in constant:
                    user_priority = constant["priority"]
                else:
                    user_priority = None
                kge["fields"][constant["field"]] = {
                    "priority": user_priority if user_priority else priority,
                    "extractors": {
                        "add_constant_kg": {
                            "config": {
                                "constants": constant["value"]
                            }
                        }
                    }

                }
                guard = dict()
                guard['field'] = "dataset_identifier"
                guard['value'] = self.prefix
                kge["fields"][constant["field"]]['guard'] = guard
                if not user_priority:
                    priority += 1

        return kge

    def segment_name_for_joins(self, config, rule):
        """
        Join fields are fields that store at the top level values in nested objects.
        To construct them, the values are first stored in segments of the form <prefix>__<path1>__<path2>
        Args:
            config (dict):
            rule ():

        Returns:

        """
        return self.prefix + "__" + Rule.make_alphanumeric_underscore(config["path"]) \
               + "__" + Rule.make_alphanumeric_underscore(rule["path"])

    def content_extraction_for_join_fields(self):
        content_extraction_for_joins = list()
        if self.nested_configs:
            for config in self.nested_configs:
                input_path_prefix = self.prefix + ".\"" + config["path"] + "\"." + self.prefix + ".\""
                for rule in config["config"].get("rules") or []:
                    if rule.get("join_indexing"):
                        input_path = input_path_prefix + rule["path"] + "\"[*]"
                        segment_name = self.segment_name_for_joins(config, rule)
                        ce = {
                            "input_path": input_path,
                            "segment_name": segment_name
                        }
                        content_extraction_for_joins.append(ce)
        return content_extraction_for_joins

    def data_extraction_for_joins(self):
        data_extraction_for_joins = list()
        if self.nested_configs:
            for config in self.nested_configs:
                for rule in config["config"].get("rules") or []:
                    if rule.get("join_indexing"):
                        field_name = config["field"] + "__" + rule["field"]
                        de = {
                            "fields": {
                                field_name: {
                                    "extractors": {
                                        "extract_as_is": {}
                                    }
                                }
                            },
                            "input_path": "content_extraction." + self.segment_name_for_joins(config, rule) + "[*]"
                        }
                        data_extraction_for_joins.append(de)
        return data_extraction_for_joins

    def generate_config_files(self, filename, etk_configs):
        """
        Generates all the supplemental config files for a mapping file.

        Args:
            filename (string): the name of the file for the top level config file.

        Returns: nothing
        """
        ce = self.content_extraction()
        ce["json_content"].extend(self.content_extraction_for_join_fields())
        de = self.data_extraction()
        de.extend(self.data_extraction_for_joins())
        kge = self.kg_enhancement()
        supl_config = {
            "content_extraction": ce,
            "data_extraction": de
        }

        if kge:
            supl_config['kg_enhancement'] = kge

        etk_configs.append({'etk_config': supl_config, 'filename': filename})

        # with open(filename, 'w') as outfile:
        #     ce = self.content_extraction()
        #     ce["json_content"].extend(self.content_extraction_for_join_fields())
        #     de = self.data_extraction()
        #     de.extend(self.data_extraction_for_joins())
        #     kge = self.kg_enhancement()
        #     supl_config = {
        #         "content_extraction": ce,
        #         "data_extraction": de
        #     }
        #
        #     if kge['fields'].keys() > 0:
        #         supl_config['kg_enhancement'] = kge
        #     outfile.write(json.dumps(supl_config, indent=2, sort_keys=True))
        #     outfile.write("\n")
        #     outfile.close()
        #     print "Wrote ", filename

        if self.nested_configs:
            for config in self.nested_configs:
                gen = ConfigGenerator(config,
                                      self.prefix,
                                      self.field_properties,
                                      path_to_nested_object=config["path"],
                                      field_of_nested_object=config["field"])
                nested_filename = os.path.splitext(filename)[0] \
                                  + "_" + Rule.make_alphanumeric_underscore(config["path"]) + ".json"
                gen.generate_config_files(nested_filename, etk_configs)

        return etk_configs


class FieldProperties(object):
    """
    This class answers questions about the fields.

    It is a hack right now, it should either wrap the master_config.json file or use
    the API to ask questions about fields.
    """

    def __init__(self, config):
        self.kg_properties = set()
        for x in config["nested_configs"]:
            self.kg_properties.add(x["field"])

    def stores_kg_nodes(self, path):
        """
        Determine whether a path leads to KG nodes (as opposed to literals)
        Args:
            path (string): the name of a field

        Returns: True if path is expected to store KN nodes
        """
        return path in self.kg_properties

    def is_date_field(self, fieldname):
        """
        Determine if this field stores a date.
        The current implementation is a heuristic
        Args:
            fieldname (string): name of a field in the master_config

        Returns: True if the field stores a date

        """
        return fieldname.startswith("date_") \
               or fieldname.endswith("_date") \
               or fieldname.find("_date_") != -1


# test1 = Rule(spec["config"]["rules"][0], spec["prefix"])
# print "content_extraction: ", test1.content_extraction()
# print "data_extraction: ", test1.data_extraction()

# home_dir = "/Users/pszekely/github/sage/"
# prefix_dir = "sage-research-tool/datasets/"
# output_dir = "/Users/pszekely/Documents/mydig-projects/sage_kg/working_dir/additional_etk_config/"
# mapping_files = [
#     "privacyrights/privacyrights",
#     "reigncoups/reigncoups"
#     ]

# sage-research-tool/other-additional-etk-configs/measurement
# home_dir = "/Users/pszekely/github/sage/"
# prefix_dir = "sage-research-tool/other-additional-etk-configs/"
# output_dir = "/Users/pszekely/Documents/mydig-projects/sage_kg/working_dir/additional_etk_config/"
# mapping_files = [
#     "measurement/measurement",
#     "measure/measure"
# ]
#
# for item in mapping_files:
#     mapping_file = home_dir + prefix_dir + item + "_mapping.json"
#     with open(mapping_file, 'r') as open_file:
#         spec_nested = json.loads(open_file.read())
#         # print spec_nested
#         gen = ConfigGenerator(spec_nested, spec_nested["prefix"], FieldProperties(spec_nested))
#         # print "content_extraction: ", test2.content_extraction()
#         # print "data_extraction: ", test2.data_extraction()
#         etk_configs = gen.generate_config_files(output_dir + item.split("/")[0] + "_config.json", list())
#
#         # supl_config = {
#         #     "content_extraction": test2.content_extraction(),
#         #     "data_extraction": test2.data_extraction()
#         # }
#         # print json.dumps(supl_config, indent=2, sort_keys=True)


if __name__ == '__main__':
    compression = "org.apache.hadoop.io.compress.GzipCodec"

    parser = OptionParser()

    (c_options, args) = parser.parse_args()
    mapping_file = args[0]
    spec_nested = json.load(codecs.open(mapping_file, mode='r'))
    gen = ConfigGenerator(spec_nested, spec_nested["prefix"], FieldProperties(spec_nested))

    ori_filename = os.path.basename(mapping_file)
    filename, ext = os.path.splitext(ori_filename)
    filename = filename.replace('_mapping', '')
    etk_configs = gen.generate_config_files(filename + "_config.json", list())

    for etk_config in etk_configs:
        o = codecs.open('/tmp/{}'.format(etk_config['filename']), 'w')
        o.write(json.dumps(etk_config['etk_config'], indent=2, sort_keys=True))
        o.close()