import json
import os
import re
from collections import defaultdict

import pyexcel_io
import pyexcel_xlsx
from jsonpath_rw import parse
from optparse import OptionParser


class Guard(object):
    """
    Guards are used to test values in an object
    """

    def __init__(self, guard_spec):
        self.path = guard_spec["path"]
        self.regex = re.compile(guard_spec["regex"])

    def test_guard(self, ob, tabular_import):
        """

        Args:
            ob (): an parsed JSON object

        Returns: True if the guard condition is met

        """
        match = tabular_import.dereference_json_path(ob, self.path)
        # value = ob.get(self.path)
        if match:
            value = match.value
            if not isinstance(value, basestring):
                value = str(value)
            return self.regex.match(value.strip())
        return False


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
            
        
        Specification
            heading_row (int): the row index that has the heading (default=0)
            content_start_row (int): the index of content start row (default=1)
            heading_colums (tuple or list): the range of colum indices to be taken
            content_end_row (int): the index of content end row
            blank_row_ends_content (int): the index of blank row ends content
        """

        if mapping_spec.get("heading_row") is not None:
            self.heading_row = mapping_spec.get("heading_row") - 1
        if mapping_spec.get("heading_row") is None:
            self.heading_row = 0

        if mapping_spec.get("content_start_row") is not None:
            self.content_start_row = mapping_spec.get("content_start_row") - 1
        if mapping_spec.get("content_start_row") is None:
            self.content_start_row = 1

        self.heading_colums = mapping_spec.get("heading_colums")
        if self.heading_colums is not None:
            self.heading_colums[0] = self.heading_colums[0] - 1
            self.heading_colums[1] = self.heading_colums[1] + 1
        self.content_end_row = mapping_spec.get("content_end_row")
        if self.content_end_row is not None:
            self.content_end_row = self.content_end_row + 1
        self.blank_row_ends_content = mapping_spec.get("blank_row_ends_content")
        if self.blank_row_ends_content is not None:
            self.blank_row_ends_content = mapping_spec.get("blank_row_ends_content") + 1

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

        self.guards = list()

        guards = self.config.get("guards")
        if guards is not None:
            for guard in guards:
                self.guards.append(Guard(guard))

        fn, extention = os.path.splitext(filename)
        if extention == ".csv":
            get_data = pyexcel_io.get_data
        elif extention == ".xls":
            get_data = pyexcel_xlsx.get_data
        elif extention == ".xlsx":
            get_data = pyexcel_xlsx.get_data
        else:
            print "file extension can not read"
        # data = get_data(filename, auto_detect_datetime=False)
        print filename
        try:
            data = get_data(filename, auto_detect_datetime=False, encoding="utf-8")
        except:
            try:
                data = get_data(filename, auto_detect_datetime=False, encoding="latin_1")
            except:
                data = get_data(filename, auto_detect_datetime=False, encoding="utf-8-sig")
        data = data.values().pop(0)

        # find a heading part
        if self.heading_colums is None:
            keys = data[self.heading_row]

        elif self.heading_colums is not None:
            # deal with the erro case
            start = self.heading_colums[0]
            end = self.heading_colums[1]
            keys = [str(name) for name in range(start + 1, end)]

        # keys = [k.replace(u'\ufeff', '') for k in keys]

        # if both content_end_row and blank_row_ends_content are provided, take former
        if self.content_end_row is not None:
            data = data[self.content_start_row:self.content_end_row + 1]

        # if self.blank_row_ends_content is not None, it will read the data untill blank row
        if (self.content_end_row is None) and (self.blank_row_ends_content is not None):
            data = data[self.content_start_row:self.blank_row_ends_content]

        elif (self.content_end_row is None) and (self.blank_row_ends_content is None):
            data = data[self.content_start_row:]

        self.content_row_identification = {}
        self.content_row_identification["non_empty_colums"] = keys

        if self.heading_colums is None:
            for value in data:
                self.object_list.append(dict(zip(keys, value + [u''] * (len(keys) - len(value)))))

        # specify the colums to take by slicing data
        elif self.heading_colums is not None:
            start = self.heading_colums[0]
            end = self.heading_colums[1]
            for value in data:
                self.object_list.append(dict(zip(keys, value[start:end + 1] + [u''] * (len(keys) - len(value)))))

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
                #
                # This is wrong as the path is a JSON path and needs to be translated
                # into an attribute name, decoding won't work for quoted paths.
                #
                decoding_dict[rule['path']] = dict()
                decoding_dict[rule['path']]['decoding_dict'] = rule['decoding_dict']['keys']
                # default action can be `preserve` or `delete`, default = `preserve`
                decoding_dict[rule['path']]['default_action'] = rule['decoding_dict'][
                    'default_action'] if 'default_action' in rule['decoding_dict'] else 'preserve'

        for ob in self.object_list:
            ob['dataset_identifier'] = self.prefix
            ob["raw_content"] = "<html><pre>" + json.dumps(ob, sort_keys=True, indent=2) + "</pre></html>"

            # go through the csv and delete all values marked to be deleted
            for k in delete_dict.keys():
                if k in ob:
                    if ob[k] in delete_dict[k]:
                        ob.pop(k)

            self.decode_cell_values(decoding_dict, ob)

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

    def decode_cell_values(self, decoding_dict, ob):
        # decode the values if there is anything to decode
        for k in decoding_dict.keys():
            # {'B 1': {'default_action': 'preserve', 'decoding_dict': {'is': 'are'}}}
            parsed_k = parse(k)
            matches = parsed_k.find(ob)
            if matches:
                # should only have one "match"
                match = matches[0]
                value = match.value
                str_path = str(match.path)
                if not isinstance(value, basestring):
                    value = str(value)
                if value in decoding_dict[k]['decoding_dict']:
                    ob[str_path] = decoding_dict[k]['decoding_dict'][value]
                else:
                    # no decoding dict defined for this value, do the default_action
                    if decoding_dict[k]['default_action'] == 'delete':
                        ob.pop(str_path)

    def apply_guards(self, item, guards):
        """
        Apply the guards to an an item, an object or sub-object in the output.

        Args:
            item (): a json object
            guards (): list of guards

        Returns: True if all guards are satisfied.

        """
        for guard in guards:
            if not guard.test_guard(item, self):
                return False
        return True

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
            new_ob["dataset_identifier"] = ob["dataset_identifier"]
            ob.pop("raw_content")
            ob.pop("dataset_identifier")
            result.append(new_ob)

            counter += 1

        self.object_list = result

    parsed_json_paths = dict()

    def dereference_json_path(self, item, json_path):
        """

        Args:
            item ():
            json_path ():

        Returns:

        """
        parsed_json_path = self.parsed_json_paths.get(json_path)
        if parsed_json_path is None:
            parsed_json_path = parse(json_path)
            self.parsed_json_paths[json_path] = parsed_json_path

        match = parsed_json_path.find(item)
        return match[0] if match else None

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

            # Improve this code by saving the Guard object in the config at initialization
            # so that we don't compile the regex every time we test, sigh
            guards = item.get("guards")
            guard_list = list()
            if guards:
                for guard in guards:
                    guard_list.append(Guard(guard))
            if not self.apply_guards(one_object, guard_list):
                continue

            k = item["path"]
            d = defaultdict()

            # Create the nested objects and add the grouping attributes
            rules = item["config"].get("rules")
            if rules is not None:
                for rule in rules:
                    path = rule["path"]
                    match = self.dereference_json_path(one_object, path)
                    value = match.value if match else None
                    if self.remove_leading_trailing_whitespace and value and isinstance(value, basestring):
                        value = value.strip()
                    if value or not self.remove_blank_fields:
                        d[str(match.path)] = value
                    all_keys.discard(path)

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

    ti = TabularImport(csv_file, mapping_spec, )
    ti.apply_nested_configs_to_all_objects()
    ti.nest_generated_json()
    new_file = output_filename
    if not output_filename or output_filename == "":
        new_file = os.path.splitext(csv_file)[0] + ".jl"

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
        new_file = os.path.dirname(csv_file) + "/" + dataset_key + "-mapping.json"

    with open(new_file, 'w') as outfile:
        outfile.write(json.dumps(mapping, indent=2, sort_keys=True))
        outfile.write("\n")
        outfile.close()
        print "Wrote default mapping file:", new_file


# # Test code:
# path = "/Users/pszekely/github/sage/sage-research-tool/datasets/bokoharam/"
# input_path = path + "example/NST-BokoHaram_2.csv"
# mapping_file = path + "bokoharam_mapping.json"
# output_filemail
#  = path + "example/bokoharam_diginput_1.jl"
# create_jl_file_from_csv(input_path, mapping_file=mapping_file, output_filename=output_file)

if __name__ == '__main__':
    compression = "org.apache.hadoop.io.compress.GzipCodec"

    parser = OptionParser()

    (c_options, args) = parser.parse_args()
    input_path = args[0]
    mapping_file = args[1]
    output_file = args[2]
    create_jl_file_from_csv(input_path, mapping_file=mapping_file, output_filename=output_file)
