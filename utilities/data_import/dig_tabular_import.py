import StringIO
import json
import os
import re
from collections import defaultdict
import pytablereader as ptr
import pytablewriter as ptw
from optparse import OptionParser


class TabularImport(object):
    """
        type (string): add a "type" attribute to the resulting JSON
        title_template (string): a template used to create a "title" attribute. The template
         is of the form "xxx {column-name-1} yyy {column-name-2} zzz" and the strings in
         {} will get substituted as appropriate
    """

    def __init__(self, filename, mapping_spec):
        """
        Convert a CSV file to a simple JSON that we can use for further processing.
        Creates an attribute for every column, and handles parsing of CSV, quoting, etc.

        The conversion of the CSV lines to JSON objects is stored in self.object_list

        Args:
            filename (string): the name of the CSV file
            mapping_spec(dict): parsed mapping spec object

        """
        self.website = mapping_spec.get("website")
        self.file_url = mapping_spec.get("file_url")
        self.id_path = mapping_spec.get("id_path")
        self.prefix = mapping_spec["prefix"]
        self.remove_leading_trailing_whitespace = mapping_spec.get("remove_leading_trailing_whitespace")
        if self.remove_leading_trailing_whitespace is None:
            self.remove_leading_trailing_whitespace = True
        self.remove_blank_fields = mapping_spec.get("remove_blank_fields")
        if self.remove_blank_fields is None:
            self.remove_blank_fields = True
        self.nested_configs = mapping_spec.get("nested_configs")
        self.object_list = list()
        self.config = mapping_spec.get("config")
        loader = ptr.CsvTableFileLoader(filename)
        for table_data in loader.load():
            # print "headers", table_data.header_list
            # print "matrix", table_data.value_matrix
            writer = ptw.JsonTableWriter()
            output = StringIO.StringIO()
            writer.stream = output
            writer.header_list = table_data.header_list
            writer.value_matrix = table_data.value_matrix
            writer.write_table()
            self.object_list = json.loads(output.getvalue())

            title_template = self.config.get("title")

            # preprocess all rules in the config and create a dict for faster processing
            rules = self.config['rules']

            if self.nested_configs:
                for nested_config in self.nested_configs:
                    if 'config' in nested_config and 'rules' in nested_config['config']:
                        rules.extend(nested_config['config']['rules'])

            delete_dict = dict()
            decoding_dict = dict()
            for rule in rules:
                if 'delete' in rule:
                    delete_dict[rule['path']] = rule['delete'] if isinstance(rule['delete'], list) else [rule['delete']]

                if 'decoding_dict' in rule:
                    decoding_dict[rule['path']] = dict()
                    decoding_dict[rule['path']]['decoding_dict'] = rule['decoding_dict']['keys']
                    # default action can be `preserve` or `delete`, default = `preserve`
                    decoding_dict[rule['path']]['default_action'] = rule['decoding_dict'][
                        'default_action'] if 'default_action' in rule['decoding_dict'] else 'preserve'

            for ob in self.object_list:
                ob["raw_content"] = "<html><pre>" + json.dumps(ob, sort_keys=True, indent=2) + "</pre></html>"

                # go through the csv and delete all values marked to be deleted
                for k in delete_dict.keys():
                    if k in ob:
                        if ob[k] in delete_dict[k]:
                            ob.pop(k)

                # decode the values if there is anything to decode
                for k in decoding_dict.keys():
                    # {'B 1': {'default_action': 'preserve', 'decoding_dict': {'is': 'are'}}}
                    if k in ob:
                        if ob[k] in decoding_dict[k]['decoding_dict']:
                            ob[k] = decoding_dict[k]['decoding_dict'][ob[k]]
                        else:
                            # no decoding dict defined for this value, do the default_action
                            if decoding_dict[k]['default_action'] == 'delete':
                                ob.pop(k)

                # apply templates to combine fields
                for rule in rules:
                    if "template" in rule:
                        ob[rule["path"]] = self.apply_format_template(rule["template"], ob)

                kg_type = self.config.get("type")
                if kg_type:
                    ob["type"] = self.listify(kg_type)
                if title_template:
                    ob["title"] = self.apply_format_template(title_template, ob)

                # remove all fields with a blank value
                if self.remove_blank_fields:
                    for k in ob.keys():
                        val = ob[k]
                        if val:
                            if isinstance(val, basestring) and val.strip() == '':
                                ob.pop(k)
                        else:
                            ob.pop(k)


    def listify(self, value):
        """
        Make into a list if not already a list
        Args:
            value (object): any Python object

        Returns: a list

        """
        if isinstance(value, list):
            return value
        else:
            return [value]

    def apply_format_template(self, template, one_object):
        """
        Apply a template of the form "xxx {column-name-1} yyy {column-name-2} zzz",
        substituting the {} with values from the given object.
        Args:
            template (string): the template
            one_object (dict): contains the key/values used for substitution

        Returns: the template string with the values substituted.

        """
        result = template
        for m in re.finditer(r'\{([\w ]+)\}', template):
            key = m.group(1)
            value = one_object.get(key)
            if value:
                if not isinstance(value, basestring):
                    value = str(value)
            else:
                value = ''
            result = result.replace("{" + key + "}", value)
        return result.strip()

    def object_id(self, ob):
        """
        When self.id_path is present, it represents a path to get an identifier for an object.
        Args:
            ob (dict): an object parsed from a file

        Returns: the identifier for an object, or None
        """
        if self.id_path:
            return ob.get(self.id_path)
        else:
            return None

    def nest_generated_json(self):
        """
        Puts the generated JSON for a CSV inside an object, nested one level down from
        the top level object. The name of the new attribute is `prefix`. We do this to avoid
        ambiguity in the DIG config. The need for doing this will go away when ETK adds support
        for filtering based on TLD, url, etc.

        Also can add a "tld" attribute to the parent object

        """
        result = list()
        counter = 1
        for ob in self.object_list:
            new_ob = dict()
            new_ob[self.prefix] = ob

            ob_id = self.object_id(ob) or str(counter)
            if self.website:
                new_ob["tld"] = self.website
                # website is not working: DIG ignores it
            if self.file_url:
                new_ob["url"] = self.file_url + "#" + ob_id
            else:
                new_ob["url"] = self.website + "#" + ob_id

            new_ob["raw_content"] = ob["raw_content"]
            ob.pop("raw_content")
            result.append(new_ob)

            counter += 1

        self.object_list = result

    def apply_nested_configs(self, one_object):
        """
        When a config specifies nested_configs, process them to create nested object.
        Args:
            one_object (dict): one object from the list of objects in a file
        """
        if not self.nested_configs:
            return one_object

        all_keys = set(one_object.keys())
        result = defaultdict()
        for item in self.nested_configs:
            k = item["path"]
            d = defaultdict()

            # Create the nested objects and add the grouping attributes
            rules = item["config"].get("rules")
            if rules:
                for rule in rules:
                    # this is a simplification as we are assuming that "path" is an attribute
                    # generalize to allow json paths
                    entry = rule["path"]
                    value = one_object.get(entry)
                    if self.remove_leading_trailing_whitespace and value and isinstance(value, basestring):
                        value = value.strip()
                    if value or not self.remove_blank_fields:
                        d[entry] = value
                    all_keys.discard(entry)

                # Add raw_content
                d["raw_content"] = "<html><pre>" + json.dumps(d, sort_keys=True, indent=2) + "</pre></html>"

                # Add a type attribute to the nested objects
                kg_type = item["config"].get("type")
                if kg_type:
                    d["type"] = self.listify(kg_type)

                # add a title
                title_template = item["config"].get("title")
                if title_template:
                    d["title"] = self.apply_format_template(title_template, one_object)

                # add the object ot the parent, we nest it inside an object with
                # the prefix so that when it becomes a top level object, it has
                # the same structure as the original object
                result[k] = {
                    self.prefix: d
                }

        # Add the attributes that didn't go into the nested objects
        all_keys.add("title")
        all_keys.add("type")
        for k in all_keys:
            value = one_object.get(k)
            if value and isinstance(value, basestring):
                value = value.strip()
            if value or not self.remove_blank_fields:
                result[k] = value
        return result

    def apply_nested_configs_to_all_objects(self):
        """
        For each of the objects in dict_list, apply the grouping spec.
        """
        result = list()
        for d in self.object_list:
            new = self.apply_nested_configs(d)
            result.append(new)
        self.object_list = result


def create_jl_file_from_csv(csv_file, mapping_spec=None, mapping_file=None, output_filename=""):
    """
    Create a json-lines file ready for ingestion in myDIG.
    Must provide a mapping, either as an object in mapping_spec or a mapping_file.

    Args:
        csv_file (string): name of the CSV file
        mapping_spec (dict): the JSON mapping
        mapping_file (string): a mapping file
        output_filename (string): name of the output json-lines file, if not provided the file will be written in the
          same folder where the csv_file is stored.
    """
    if not mapping_spec and not mapping_file:
        print "Error: must provide either 'mapping_spec' or 'mapping_file'."
        exit()

    if mapping_spec and mapping_file:
        print "Error: both 'mapping_spec' and 'mapping_file' provided, only one should be provided."
        exit()

    if mapping_file:
        with open(mapping_file, 'r') as open_file:
            mapping_spec = json.loads(open_file.read())
            open_file.close()

    ti = TabularImport(csv_file, mapping_spec)
    ti.apply_nested_configs_to_all_objects()
    ti.nest_generated_json()

    new_file = output_filename
    if not output_filename or output_filename == "":
        new_file = os.path.splitext(filename)[0] + ".jl"

    with open(new_file, 'w') as outfile:
        write_newline = False
        for item in ti.object_list:
            if write_newline:
                outfile.write("\n")
            write_newline = True
            outfile.write(json.dumps(item))
        outfile.close()
    print "Wrote jsonlines file:", new_file


def create_default_mapping_for_csv_file(csv_file, dataset_key, website="", file_url="", output_filename=""):
    """
    Create a default mapping file for a CSV file to build a KG using every column of the file.
    There is no attempt to interpret any of the columns in the CSV file. The output is meant
    to give a starting point to create a custom mapping file.

    The code reads the CSV file and uses the first line as the headers.

    Args:
        csv_file (string): a CSV file
        dataset_key (string): a string used to distinguish this file from other files. It should use only lowercase
          and underscore.
        website (string): optional, the website from where the file came, e.g., 'isi.edu'.
        file_url (string): optional, the URL of the file as best as you can provide it, e.g., 'http://isi.edu/abc/123'.
        output_filename (string): a path to write the mapping file, if not provided the file will be written in the
          same folder where the csv_file is stored.
    """
    mapping = {
        "prefix": dataset_key,
        "website": website,
        "file_url": file_url,
        "config": {
            "title": "dummy title",
            "type": [],
            "rules": []
        },
        "nested_configs": []
    }
    ti = TabularImport(csv_file, mapping)
    rules = mapping["config"]["rules"]
    for k in ti.object_list[0]:
        r = {
            "path": k,
            "field": re.sub(r'\W+', '_', k).lower()
        }
        rules.append(r)

    new_file = output_filename
    if not output_filename or output_filename == "":
        new_file = os.path.dirname(filename) + "/" + dataset_key + "-mapping.json"

    with open(new_file, 'w') as outfile:
        outfile.write(json.dumps(mapping, indent=2, sort_keys=True))
        outfile.write("\n")
        outfile.close()
        print "Wrote default mapping file:", new_file

# home_dir = "/Users/pszekely/github/sage/"
# prefix_dir = "sage-research-tool/datasets/"
# files = [
#     {
#         "csv": "reigncoups/example/couplist_raw.csv",
#         "mapping": "reigncoups/reigncoups_mapping.json",
#         "jl": "reigncoups/example/couplist_diginput.jl"
#     }
#     # ,
#     # {
#     #     "csv": "privacyrights/example/Privacy_Rights_Clearinghouse-Data-Breaches-Export_raw.csv",
#     #     "mapping": "privacyrights/privacyrights_mapping.json",
#     #     "jl": "privacyrights/example/Privacy_Rights_Clearinghouse-Data-Breaches-Export_diginput.jl"
#     # }
# ]
#
# # filename = "./examples/Privacy_Rights_Clearinghouse-Data-Breaches-Export_100.csv"
# # filename = "/Users/pszekely/Downloads/couplist.csv"
# # mapping_file = "./examples/privacyrights-mapping.json"
# # mapping_file = "/Users/pszekely/Downloads/reigncoups-mapping.json"
#
# # 1. generate default mappings
# # create_default_mapping_for_csv_file(filename, "output/default-mapping")
#
# # 2. create jl file
# # create_jl_file_from_csv(filename, mapping_file=mapping_file,
# #                         output_filename="/Users/pszekely/Downloads/couplist.jl")
# # create_jl_file_from_csv(filename, mapping_file=mapping_file,
# #                         output_filename="./examples/privacyrights_diginput.jl")
#
# for item in files:
#     create_jl_file_from_csv(
#         home_dir + prefix_dir + item["csv"],
#         mapping_file=home_dir + prefix_dir + item["mapping"],
#         output_filename=home_dir + prefix_dir + item["jl"])
