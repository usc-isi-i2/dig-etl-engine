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
import copy
import LocationRange as lr
import LocationParser as lp

logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s', level=logging.WARN)


class TimeSeriesRegion(object):
    def __init__(self, orientation='row', series_range=None, data_range=None, metadata_spec = None,
                 time_coordinates=None, global_metadata=None, granularity=None, provenance=None):
        self.orientation = orientation
        self.series_range = series_range
        self.data_range = data_range
        self.granularity = granularity
        self.metadata_spec = metadata_spec
        self.time_coordinates = time_coordinates
        self.global_metadata = global_metadata
        self.provenance = provenance
        self.time_series = []

    def parse(self,data):
        metadata = self.parse_global_metadata(data)
        self.parse_ts(data, metadata)
        return self.time_series

    def data_to_string(self, data):
        if type(data) is unicode:
            return data
        if type(data) is str:
            return unicode(data, errors='replace')
        else:
            return unicode(str(data), errors='replace')


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
        metadata['provenance'] = self.provenance
        return metadata

    def parse_tsr_metadata(self,metadata,data,tsidx):
        mds = self.metadata_spec
        md_modes = {}
        all_blank = True
        for md_name in mds:
            if mds[md_name]['mode'] == 'normal':
                if mds[md_name]['source'] == 'cell':
                    metadata[md_name] = data[(mds[md_name]['loc'][0], mds[md_name]['loc'][1])]
                    if not self.is_blank(metadata[md_modes]):
                        all_blank = False
                elif mds[md_name]['source'] == 'const':
                    metadata[md_name] = mds[md_name]['val']
                else:
                    md_vals = []
                    for idx in mds[md_name]['loc']:
                        coords = self.orient_coords(tsidx, idx)
                        val = self.data_to_string(data[coords])
                        md_vals.append(val)
                        if not self.is_blank(val):
                            all_blank = False
                    metadata[md_name] = " ".join(md_vals)
            else:
                md_modes[mds[md_name]['mode']] = True
        if all_blank:
            raise IndexError("All metadata values blank")
        return md_modes

    def parse_inline_tsr_metadata(self,metadata,data,dataidx):
        mds = self.metadata_spec
        for md_name in mds:
            if mds[md_name]['mode'] == 'inline':
                md_vals = []
                for idx in mds[md_name]['loc']:
                    coords = self.orient_coords(idx, dataidx)
                    md_vals.append(self.data_to_string(data[coords]))
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
            val = self.data_to_string(data[coords[0], coords[1]])
            if self.is_blank(val) and self.time_coordinates['mode'] == 'backfill':
                t_idx = d_idx - 1
                while t_idx > 0 and self.is_blank(val):
                    coords = self.orient_coords(tc, t_idx)
                    val = self.data_to_string(data[coords[0], coords[1]])
                    t_idx -= 1
            time_labels.append(val)
        time_label = " ".join(time_labels)
        return time_label

    def parse_ts(self, data, metadata):
        self.time_series = []
        for ts_idx in self.series_range:
            timeseries = []
            ts_metadata = copy.deepcopy(metadata)
            ts_metadata['provenance'][self.orientation]=ts_idx

            try:
                md_modes = self.parse_tsr_metadata(ts_metadata, data, ts_idx)
            except IndexError as ie:
                if type(self.series_range.curr_component()) is lr.LocationRangeInfiniteIntervalComponent:
                    logging.info("all blank metadata cells in infinite interval")
                    break
                else:
                    logging.error("metadata specifcation indexing error for time series index {}".format(ts_idx))
                    raise ie

            inline_md_curr = {}
            inline_md_prev = None

            for d_idx in self.data_range:
                time_label = ''
                try:
                    time_label = self.generate_time_label(data, d_idx)
                except IndexError as ie:
                    if type(self.data_range.curr_component()) is lr.LocationRangeInfiniteIntervalComponent:
                        break
                    else:
                        logging.error("metadata specifcation indexing error for data point index {}".format(d_idx))
                        raise ie

                if type(self.data_range.curr_component()) is lr.LocationRangeInfiniteIntervalComponent and self.is_blank(time_label):
                    logging.info("blank cell in infinite interval")
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
    def __init__(self, annotation, fn):
        self.locparser = lp.LocationParser()

        self.properties = annotation['Properties']
        self.sheet_indices = self.locparser.parse_range(annotation['Properties']['sheet_indices'])

        self.metadata = self.parse_md(annotation['GlobalMetadata'])
        self.provenance = dict(filename=fn)

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
                                metadata_spec=mdspec, time_coordinates=time_coords, global_metadata=self.metadata,
                                provenance = self.provenance)

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
        self.normalized_source_file = os.path.basename(spreadsheet_fn)
        self.book = pyexcel.get_book(file_name=spreadsheet_fn, auto_detect_datetime=False)
        self.annotations = self.load_annotations(annotations_fn)

    def process(self):
        timeseries = []
        for annotation in self.annotations:
            ssa = SpreadsheetAnnotation(annotation, self.normalized_source_file)
            parsed = []
            for anidx in ssa.sheet_indices:
                data = self.book.sheet_by_index(anidx)
                for tsr in ssa.timeseries_regions:
                    tsr.provenance['sheet']=anidx
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
