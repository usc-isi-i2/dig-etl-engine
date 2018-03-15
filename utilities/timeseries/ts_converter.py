import decimal
import demjson
import json
import logging
import hashlib
import numbers
import sys
from dateutil import parser
from optparse import OptionParser


class DecimalJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalJSONEncoder, self).default(o)


class Measurement(object):
    def __init__(self, timeseries_id, timeseries_element, filename):
        self.date = timeseries_element[0]
        if len(timeseries_element) <= 2:
            self.value = timeseries_element[1]
        else:
            self.value = timeseries_element[1:]
        self.doc_id = self.get_doc_id(timeseries_element)
        self.timeseries_id = timeseries_id
        self.filename = filename

    def get_doc_id(self, array):
        array_str = json.dumps(array, cls=DecimalJSONEncoder)
        hash_object = hashlib.sha1(array_str)
        return hash_object.hexdigest()

    def to_dict(self):
        dct = {}
        dct["measurement"] = {}
        dct["measurement"]['date'] = self.date
        if isinstance(self.value, numbers.Number):
            dct["measurement"]['number'] = self.value
        elif isinstance(self.value, basestring):
            dct["measurement"]['text'] = self.value

        dct["measurement"]['timeseries'] = self.timeseries_id
        dct["measurement"]['type'] = "Measurement"
        dct['doc_id'] = self.doc_id
        dct['measurement']['provenance_filename'] = self.filename
        return dct


class Trend(object):
    def __init__(self, timeseries_id, trend_element, filename):
        self.value = trend_element
        self.doc_id = self.get_doc_id(trend_element)
        self.timeseries_id = timeseries_id
        self.filename = filename

    def get_doc_id(self, array):
        array_str = json.dumps(array, cls=DecimalJSONEncoder)
        hash_object = hashlib.sha1(array_str)
        return hash_object.hexdigest()

    def to_dict(self):
        dct = {}
        dct['doc_id'] = self.doc_id
        dct["trend"] = self.value
        dct['trend']['provenance_filename'] = self.filename
        dct["trend"]['timeseries'] = self.timeseries_id
        dct["trend"]['type'] = "Trend"
        return dct


class TimeSeries(object):
    def __init__(self, meta_data, dataset):
        self.meta_data = meta_data
        self.dataset = dataset
        self.doc_id = self.get_doc_id(meta_data)

    def get_doc_id(self, meta_data):
        if self.dataset.strip() != "" and 'name' in meta_data:
            hash_object = hashlib.sha256('{} {}'.format(self.dataset, meta_data['name']))
        else:
            print('WARNING: Creating doc id for time series using metadata and not a combination of \"dataset\" '
                  'and \"metadata[\'name\']. This can result in inconsistencies in future datasets of the same '
                  'timeseries. You have been warned!')

            md_str = json.dumps(meta_data, sort_keys=True, cls=DecimalJSONEncoder)
            hash_object = hashlib.sha1(md_str)
        return hash_object.hexdigest().upper()

    def to_dict(self):
        dct = {}
        dct["measure"] = {}
        dct["measure"]["metadata"] = self.meta_data
        dct["measure"]['type'] = "Measure"
        dct['doc_id'] = self.doc_id
        dct["measure"]['provenance_filename'] = dct['measure']['metadata']['provenance']['filename']
        return dct


class ProcessTimeSeries():
    def is_number(self, s):
        try:
            number = float(s)
            return True, number
        except ValueError:
            pass

        try:
            import unicodedata
            number = unicodedata.numeric(s)
            return True, number
        except (TypeError, ValueError):
            pass
        return False, 0

    def impute_values(self, ts, threshold):
        total = 0
        index = 0
        missing_value_index = []
        total_str = 0
        for element in ts:
            if len(element) <= 2:
                value = element[1]
                if isinstance(value, numbers.Number):
                    total += 1
                elif isinstance(value, basestring):
                    is_n, n_value = self.is_number(value)
                    if is_n:
                        total += 1
                        ts[index] = [element[0], n_value]
                    else:
                        missing_value_index.append(index)
                        total_str += 1
                else:
                    missing_value_index.append(index)

                index += 1
        print total_str

        if total * 1.0 / len(ts) >= threshold:
            n_missing = len(missing_value_index)
            for i in range(n_missing):
                index = missing_value_index[i]
                print index
                if index == 0:
                    next = 1
                    while next < n_missing and next == missing_value_index[next]:
                        next += 1
                    ts[index] = [ts[index][0], ts[next][1]]
                else:
                    ts[index] = [ts[index][0], ts[index - 1][1]]

            return ts

        elif total_str == len(ts):
            return ts

        else:
            for i in range(0, len(ts)):
                value = ts[i][1]
                if value is not None:
                    ts[i] = [ts[i][0], str(value)]
            return ts

    def processs(self, tables, dataset_name):
        result = []
        for sheet in tables:
            for timeseries in sheet:
                ts = TimeSeries(timeseries['metadata'], dataset_name)
                processed_ts = self.impute_values(timeseries['ts'], 0.8)
                if processed_ts is not None:
                    ts_dict = ts.to_dict()
                    try:
                        start, end = self.get_temporal_region(processed_ts)
                        ts_dict["measure"]["temporal_region"] = {
                            'start_date_time': start,
                            'end_date_time': end
                        }
                    except:
                        pass
                    result.append(ts_dict)
                    filename = ts_dict["measure"]['provenance_filename']
                    # measurement
                    for ts_element in processed_ts:
                        measurement = Measurement(ts.doc_id, ts_element, filename)
                        result.append(measurement.to_dict())
                    # trend
                    if 'ts_description' in timeseries:
                        try:
                            for trend_element in timeseries['ts_description']['linear fits']:
                                trend = Trend(ts.doc_id, trend_element, filename)
                                result.append(trend.to_dict())
                        except:
                            pass

        return result

    def get_temporal_region(self, ts_array):
        max_dt, min_dt = None, None
        for ts in ts_array:
            dt = parser.parse(ts[0])
            if not max_dt:
                max_dt = dt
            if not min_dt:
                min_dt = dt
            max_dt = max(max_dt, dt)
            min_dt = min(min_dt, dt)
        return min_dt.isoformat(), max_dt.isoformat()

    def load_json(self, json_fn):
        anfile = open(json_fn)
        json_decoded = demjson.decode(anfile.read(), return_errors=True)
        for msg in json_decoded[1]:
            if msg.severity == "error":
                logging.error(msg.pretty_description())
        return json_decoded[0]

    def write_result_to_file(self, output_fn, output, ts_measure_transfer=None):

        with open(output_fn, 'w') as fp:
            for obj in output:
                if ts_measure_transfer and isinstance(ts_measure_transfer, dict) and 'measure' in obj:
                    meta = obj['measure']['metadata']
                    for k, v in ts_measure_transfer.items():
                        obj['measure']['metadata'][k] = v.format(**meta)
                fp.write(json.dumps(obj, cls=DecimalJSONEncoder))
                fp.write('\n')


def main():
    parser = OptionParser()
    parser.add_option("-d", "--dataset", dest="dataset", type="string",
                      help="dataset name", default="")
    (c_options, args) = parser.parse_args()
    input_path = args[0]
    output_file = args[1]
    dataset_name = c_options.dataset

    test = ProcessTimeSeries()
    tables = test.load_json(input_path)
    # print test.processs(tables)
    test.write_result_to_file(output_file, test.processs(tables, dataset_name))


if __name__ == "__main__":
    main()
