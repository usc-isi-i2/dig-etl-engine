import sys
import os
import re
import argparse
import pyexcel
import numpy
from datetime import date, datetime
import pyexcel
import logging
import re
import demjson
import json
logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)


class LocationRangeComponent(object):
    def __init__(self, rtype):
        self.rtype = rtype


class LocationRangeSingletonComponent(LocationRangeComponent):
    def __init__(self, val, rtype='singleton'):
        super(LocationRangeSingletonComponent, self).__init__(rtype)
        self.val = val

    def generator(self):
        yield self.val


class LocationRangeIntervalComponent(LocationRangeComponent):
    def __init__(self, start, end, rtype='range', increment=1):
        super(LocationRangeIntervalComponent, self).__init__(rtype)
        self.start = start
        self.end = end
        self.incr = increment

    def generator(self):
        for x in range(self.start, self.end, self.incr):
            yield x


class LocationRangeInfiniteIntervalComponent(LocationRangeComponent):
    def __init__(self, start, rtype='range', increment=1):
        super(LocationRangeInfiniteIntervalComponent, self).__init__(rtype)
        self.start = start
        self.incr = increment

    def generator(self):
        x = self.start
        while True:
            yield x
            x += self.incr


class LocationRange(object):
    def __init__(self):
        self.vals = []
        self.iteridx=0
        self.generator = None

    def add_component(self, component):
        self.vals.append(component)

    def curr_component(self):
        return self.vals[self.iteridx]

    def __iter__(self):
        self.iteridx=0
        self.generator = None
        return self

    def next(self):
        if self.iteridx >= len(self.vals):
            raise StopIteration
        elif self.generator is None:
            self.generator=self.vals[self.iteridx].generator()

        try:
            return self.generator.next()
        except StopIteration:
            self.generator = None
            self.iteridx += 1
            return self.next()


class LocationParser(object):
    def __init__(self):
        self.patterns = {
            'range': re.compile('\[(.+?)\]'),
            'cell_coord': re.compile('\(([A-Z]+),(\d+)\)'),
            'row_label': re.compile('\d+'),
            'col_label': re.compile('[A-Z]+'),
        }

    def parse_range(self, data):
        match = self.patterns['range'].match(data)
        rnge = LocationRange()
        if match:
            for val in [x.strip() for x in match.group(1).split(',')]:
                parts = val.split(':')
                translate_fn = self.translate_row_label
                if self.is_column(parts[0]):
                    translate_fn = self.translate_col_label

                if len(parts) == 1:
                        rnge.add_component(LocationRangeSingletonComponent(translate_fn(parts[0])-1))

                elif len(parts) == 2:
                    if self.is_sentinel(parts[1]):
                        rnge.add_component(LocationRangeInfiniteIntervalComponent(start=translate_fn(parts[0])-1))
                    else:
                        rnge.add_component(LocationRangeIntervalComponent(start=translate_fn(parts[0])-1,
                                                                          end=translate_fn(parts[1])))

                elif len(parts) == 3:

                    if self.is_sentinel(parts[1]):
                        rnge.add_component(LocationRangeInfiniteIntervalComponent(start=translate_fn(parts[0])-1,
                                                                                  increment=int(parts[1])))
                    else:
                        rnge.add_component(LocationRangeIntervalComponent(start=translate_fn(parts[0])-1,
                                                                          end=translate_fn(parts[2]),
                                                                          increment=int(parts[1])))

                else:
                    raise Exception("Error parsing element of range: %s"%val)
        else:
            raise Exception('Error parsing range, data %s did not match pattern'%data)

        return rnge

    def parse_coords(self, data):
        match = self.patterns['cell_coord'].match(data)
        if match:
            return (int(match.group(2)) - 1, self.translate_col_label(match.group(1)) - 1)
        else:
            raise Exception('Error passing cell coordinates: %s'%data)

    def is_column(self, data):
        return self.patterns['col_label'].match(data)

    def is_sentinel(self, data):
        return data == '*'

    def translate_col_label(self, col_label):
        cl = col_label
        if len(cl) == 2:
            return 26 * (ord(cl[0]) - ord('A') + 1) + (ord(cl[1]) - ord('A') + 1)
        elif len(cl) == 1:
            return ord(cl[0]) - ord('A') + 1
        else:
            raise Exception("Unexpected column label: %s"%cl)

    def translate_row_label(self, row_label):
        return int(row_label)



class TimeSeriesRegion(object):
    def __init__(self, orientation='row', series_range=None, data_range=None, metadata_spec = None,
                 time_coordinates=None, global_metadata=None, granularity=None):
        self.orientation = orientation
        self.series_range = series_range
        self.data_range = data_range
        self.granularity = granularity
        self.metadata_spec = metadata_spec
        self.time_coordinates = time_coordinates
        self.global_metadata = global_metadata
        self.time_series = []


    def parse(self,data):
        metadata = self.parse_global_metadata(data)
        self.parse_ts(data, metadata)
        return self.time_series

    def parse_global_metadata(self,data):
        metadata = {}
        for mdname, mdspec in self.global_metadata.iteritems():
            if mdspec['source'] == 'sheet_name':
                metadata[mdname] = data.name
            elif mdspec['source'] == 'cell':
                metadata[mdname] = data[(mdspec['row'], mdspec['col'])]
            elif mdspec['source'] == 'const':
                metadata[mdname] = mdspec['val']
            else:
                logging.warn("Unknown metadata source %s", mdspec['source'])
        return metadata

    def parse_tsr_metadata(self,metadata,data,tsidx):
        mds = self.metadata_spec
        md_modes = {}
        for md_name in mds:
            if mds[md_name]['mode'] == 'normal':
                if mds[md_name]['source'] == 'cell':
                    metadata[md_name] = data[(mds[md_name]['loc'][0], mds[md_name]['loc'][1])]
                elif mds[md_name]['source'] == 'const':
                    metadata[md_name] = mds[md_name]['val']
                else:
                    md_vals = []
                    for idx in mds[md_name]['loc']:
                        coords = self.orient_coords(tsidx, idx)
                        md_vals.append(str(data[coords]))
                    metadata[md_name] = " ".join(md_vals)
            else:
                md_modes[mds[md_name]['mode']] = True
        return md_modes

    def parse_inline_tsr_metadata(self,metadata,data,dataidx):
        mds = self.metadata_spec
        for md_name in mds:
            if mds[md_name]['mode'] == 'inline':
                md_vals = []
                for idx in mds[md_name]['loc']:
                    coords = self.orient_coords(idx, dataidx)
                    md_vals.append(str(data[coords]))
                metadata[md_name] = " ".join(md_vals)


    def orient_coords(self, tsidx, dataidx):
        if self.orientation == 'row':
            return (tsidx, dataidx)
        else:
            return (dataidx, tsidx)

    def generate_time_label(self, data, d_idx):
        time_labels = []
        for tc in self.time_coordinates['locs']:
            coords = self.orient_coords(tc, d_idx)
            val = str(data[coords[0], coords[1]])
            if self.is_blank(val) and self.time_coordinates['mode'] == 'backfill':
                t_idx = d_idx - 1
                while t_idx > 0 and self.is_blank(val):
                    coords = self.orient_coords(tc, t_idx)
                    val = str(data[coords[0], coords[1]])
                    t_idx -= 1
            time_labels.append(val)
        time_label = " ".join(time_labels)
        return time_label

    def parse_ts(self, data, metadata):
        self.time_series = []
        for ts_idx in self.series_range:
            timeseries = []
            ts_metadata = dict(metadata)

            md_modes = self.parse_tsr_metadata(ts_metadata, data, ts_idx)
            inline_md_curr = {}
            inline_md_prev = None

            for d_idx in self.data_range:
                time_label = ''
                try:
                    time_label = self.generate_time_label(data, d_idx)
                except IndexError as ie:
                    if type(self.data_range.curr_component()) is LocationRangeInfiniteIntervalComponent:
                        break
                    else:
                        raise ie

                if type(self.data_range.curr_component()) is LocationRangeInfiniteIntervalComponent and self.is_blank(time_label):
                    logging.error("blank cell in infinite interval")
                    break

                # if inline metadata has changed (in auto-detect mode)
                    # merge previous metadata
                    # output old time series
                    # re-initialize time series array
                if 'inline' in md_modes:
                    self.parse_inline_tsr_metadata(inline_md_curr, data, d_idx)
                    if inline_md_prev:
                        md_changed = False
                        for md_name in inline_md_prev:
                            if inline_md_curr[md_name] != inline_md_prev[md_name]:
                                md_changed = True

                        if md_changed:
                            new_metadata = dict(ts_metadata)
                            for md_name in inline_md_prev:
                                new_metadata[md_name] = inline_md_prev[md_name]
                            self.time_series.append({
                                'metadata': new_metadata,
                                'ts': timeseries
                            })
                            timeseries = []

                        inline_md_prev = inline_md_curr
                        inline_md_curr = {}

                    else:
                        inline_md_prev = inline_md_curr
                        inline_md_curr = {}

                coords = self.orient_coords(ts_idx, d_idx)
                timeseries.append((time_label,data[coords[0],coords[1]]))

            self.time_series.append(dict(metadata=ts_metadata, ts=timeseries))

    def is_blank(self, data):
        return len(data.strip()) == 0

class SpreadsheetAnnotation(object):
    def __init__(self, annotation):
        self.locparser = LocationParser()

        self.properties = annotation['Properties']
        self.sheet_indices = self.locparser.parse_range(annotation['Properties']['sheet_indices'])

        self.metadata = self.parse_md(annotation['GlobalMetadata'])

        self.timeseries_regions = []
        for tsr in annotation['TimeSeriesRegions']:
            self.timeseries_regions.append(self.parse_tsr(tsr))

    def parse_md(self, md_json):
        md_dict = {}
        for mdspec in md_json:
            mdname = mdspec['name']
            md_dict[mdname] = {}
            md_dict[mdname]['source'] = mdspec['source']
            if mdspec['source'] == 'cell':
                (md_dict[mdname]['row'], md_dict[mdname]['col']) = self.locparser.parse_coords(mdspec['loc'])
            if mdspec['source'] == 'const':
                md_dict[mdname]['val'] = mdspec['val']
        return md_dict

    def parse_tsr(self, tsr_json):
        orientation = tsr_json['orientation']
        series_range = None
        if orientation == 'row':
            series_range = self.locparser.parse_range(tsr_json['rows'])
        else:
            series_range = self.locparser.parse_range(tsr_json['cols'])

        data_range = self.locparser.parse_range(tsr_json['locs'])
        time_coords = {}
        time_coords['locs'] = self.locparser.parse_range(tsr_json['times']['locs'])
        if 'mode' in tsr_json['times']:
            time_coords['mode'] = tsr_json['times']['mode']
        else:
            time_coords['mode'] = None

        mdspec = self.parse_tsr_metadata(tsr_json['metadata'], orientation)

        return TimeSeriesRegion(orientation=orientation, series_range=series_range, data_range=data_range,
                                metadata_spec=mdspec, time_coordinates=time_coords, global_metadata=self.metadata)

    def parse_tsr_metadata(self, md_json, orientation):
        md_dict = {}
        reverse_orientation = {'row': 'col', 'col': 'row'}
        for md_sec in md_json:
            name = md_sec['name']
            md_dict[name] = {}

            if 'source' in md_sec:
                md_dict[name]['source'] = md_sec['source']
            else:
                md_dict[name]['source'] = reverse_orientation[orientation]

            loc = None
            if 'loc' in md_sec:
                loc = md_sec['loc']

            if md_dict[name]['source'] == 'cell':
                md_dict[name]['loc'] = self.locparser.parse_coords(loc)

            elif md_dict[name]['source'] == 'row':
                md_dict[name]['loc'] = self.locparser.parse_range(loc)

            elif md_dict[name]['source'] == 'col':
                md_dict[name]['loc'] = self.locparser.parse_range(loc)

            elif md_dict[name]['source'] == 'const':
                md_dict[name]['val'] = md_sec['val']

            if 'mode' in md_sec:
                md_dict[name]['mode'] = md_sec['mode']
            else:
                md_dict[name]['mode'] = 'normal'

        return md_dict

class ExtractSpreadsheet(object):

    def __init__(self, spreadsheet_fn, annotations_fn):
        self.book = pyexcel.get_book(file_name=spreadsheet_fn, auto_detect_datetime=False)
        self.annotations = self.load_annotations(annotations_fn)

    def process(self):
        timeseries = []
        for annotation in self.annotations:
            ssa = SpreadsheetAnnotation(annotation)
            parsed = []
            for anidx in ssa.sheet_indices:
                data = self.book.sheet_by_index(anidx)
                for tsr in ssa.timeseries_regions:
                    for parsed_tsr in tsr.parse(data):
                        parsed.append(parsed_tsr)
                logging.debug("%s",parsed)
            timeseries.append(parsed)
        return timeseries

    def load_annotations(self,annotations_fn):
        anfile = open(annotations_fn)
        annotations_decoded = demjson.decode(anfile.read(), return_errors=True)
        for msg in annotations_decoded[1]:
            if msg.severity == "error":
                logging.error(msg.pretty_description())
        return annotations_decoded[0]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("annotation", help='Annotation of time series in custom JSON format')
    ap.add_argument("spreadsheet", help='Excel spreadsheet file')
    ap.add_argument("outfile", help='file to write results')
    args = ap.parse_args()
    es = ExtractSpreadsheet(args.spreadsheet, args.annotation)
    timeseries = es.process()
    demjson.encode_to_file(args.outfile,timeseries,overwrite=True)

if __name__ == "__main__":
    main()
