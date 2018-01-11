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
logging.basicConfig(level=logging.WARN)

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


    def parse(self,data):
        metadata = self.parse_metadata(data)
        if self.orientation == 'row':
            self.parse_row_ts(data,metadata)
        else:
            self.parse_col_ts(data,metadata)        
        return self.time_series

    def parse_metadata(self,data):
        metadata = {}
        for mdname, mdspec in self.global_metadata.iteritems():
            if mdspec['source'] == 'sheet_name':
                metadata[mdname] = data.name
            elif mdspec['source'] == 'cell':
                metadata[mdname] = data[mdspec['row'],mdspec['col']]
            else:
                logging.warn("Unknown metadata source %s", mdspec['source'])
        return metadata

    def parse_col_ts(self,data, metadata):
        self.time_series = []
        for c_idx in self.series_range:
            timeseries = []
            ts_metadata = dict(metadata)
            for (md_name,md_loc) in self.metadata_spec.iteritems():
                ts_metadata[md_name]=data.column[c_idx][md_loc]

            for d_idx in self.data_range:
                time_label = ''
                for tc in self.time_coordinates:
                    time_label+=str(data.column[tc][d_idx])
                    time_label+=' '
                time_label.strip()
                time_label.rstrip()
                timeseries.append((time_label,data.column[c_idx][d_idx]))
            self.time_series.append( {
                'metadata': ts_metadata,
                'ts': timeseries
            })

    def parse_row_ts(self, data, metadata):
        self.time_series = []
        for r_idx in self.series_range:
            timeseries = []
            ts_metadata = dict(metadata)
            for (md_name,md_loc) in self.metadata_spec.iteritems():
                ts_metadata[md_name]=data.row[r_idx][md_loc]
                logging.info("%s set to %s", md_name, data.row[r_idx][md_loc])
            for d_idx in self.data_range:
                time_label = ''
                for tc in self.time_coordinates:
                    time_label+=str(data.row[tc][d_idx])
                    time_label+=' '
                time_label = time_label.strip()
                timeseries.append((time_label.strip(),data.row[r_idx][d_idx]))
            self.time_series.append( {
                'metadata': ts_metadata,
                'ts': timeseries
            })


class SpreadsheetAnnotation(object):
    def __init__(self, annotation):
        self.timeseries_regions = []
        self.patterns = {
            'row_label': re.compile('\d+'),
            'col_label': re.compile('[A-Z]+'),
            'col_label_2': re.compile('[A-Z]{2}'),
            'series_num': re.compile('\[(\d+):(\d+)\]'),
            'series_alpha': re.compile('\[([A-Z]+):([A-Z]+)\]'),
            'singleton_alpha': re.compile('\[([A-Z]+)\]'),
            'singleton_num': re.compile('\[(\d+)\]'),
            'tuple_num_1': re.compile('\[(\d+),(\d+)\]'),
            'tuple_num_2': re.compile('\((\d+),(\d+)\)'),
            'tuple_alpha_1': re.compile('\[([A-Z]+),([A-Z]+)\]'),
            'tuple_alpha_2': re.compile('\(([A-Z]+),([A-Z]+)\)'),
            'cell_coord': re.compile('\(([A-Z]+),(\d+)\)'),
        }
        self.metadata = self.parse_md(annotation['Metadata'])

        for tsr in annotation['TimeSeriesRegions']:
            self.timeseries_regions.append(self.parse_tsr(tsr))

    def parse_md(self, md_json):
        md_dict = {}
        for mdspec in md_json:
            mdname = mdspec['name']
            md_dict[mdname] = {}
            md_dict[mdname]['source'] = mdspec['source']
            if mdspec['source'] == 'cell':
                match = self.patterns['cell_coord'].match(mdspec['loc'])
                if match:
                    md_dict[mdname]['row'] = int(match.group(2))-1
                    md_dict[mdname]['col'] = self.translate_col_label(match.group(1))-1
                else:
                    logging.error("Could not parse metadata cell location %s",mdspec['loc'])
        return md_dict

    def parse_tsr(self, tsr_json):
        orientation = tsr_json['orientation']
        series_range = None
        if orientation == 'row':
            logging.debug("Row orientation")
            series_range = self.parse_range(tsr_json['rows'])
        elif orientation == 'col':
            logging.debug("Column orientation")
            series_range = self.parse_range(tsr_json['cols'])
        data_range = self.parse_range(tsr_json['locs'])
        time_coords = self.parse_timecoords(tsr_json['times'])
        mdspec = self.parse_tsr_metadata(tsr_json['metadata'])
        return TimeSeriesRegion(orientation=orientation, series_range=series_range, data_range=data_range,
                                metadata_spec=mdspec, time_coordinates=time_coords, global_metadata=self.metadata)

    def translate_col_label(self, col_label):
        cl = col_label
        if self.patterns['col_label_2'].match(col_label):
            return 26 * (ord(cl[0]) - ord('A') + 1) + (ord(cl[1]) - ord('A') + 1)
        else:
            return ord(cl[0]) - ord('A') + 1

    def parse_range(self, range_str):
        logging.debug("Parsing %s", range_str)

        match = self.patterns['series_num'].match(range_str)
        if match:
            logging.debug("Matched a range of row numbers: %s", range_str)
            return range(int(match.group(1))-1,int(match.group(2)))

        match = self.patterns['series_alpha'].match(range_str)
        if match:
            logging.debug("Matched a range of columns: %s", range_str)
            return range(self.translate_col_label(match.group(1))-1,self.translate_col_label(match.group(2)))

        match = self.patterns['col_label'].match(range_str)
        if match:
            logging.debug("Matched a column: %s", range_str)
            return [self.translate_col_label(range_str)-1]

        match = self.patterns['row_label'].match(range_str)
        if match:
            logging.debug("Matched a row: %s", range_str)
            return [int(locs)-1]

        logging.error("Could not parse a range from %s",range_str)

    def parse_timecoords(self, tc_json):
        locs = tc_json['locs']
        logging.debug("Parsing time spec %s", locs)

        if type(locs) == list:
            return [i-1 for i in locs]

        match = self.patterns['tuple_num_1'].match(locs)
        if match:
            return range(int(match.group(1))-1,int(match.group(2)))
            logging.debug("Matched a tuple of row numbers: %s", locs)

        match = self.patterns['tuple_num_2'].match(locs)
        if match:
            logging.debug("Matched a tuple of row numbers-2: %s", locs)
            return range(int(match.group(1))-1,int(match.group(2)))

        match = self.patterns['tuple_alpha_1'].match(locs)
        if match:
            logging.debug("Matched a tuple of cols: %s", locs)
            return range(self.translate_col_label(match.group(1))-1,
                         self.translate_col_label(match.group(2)))

        match = self.patterns['tuple_alpha_2'].match(locs)
        if match:
            logging.debug("Matched a tuple of cols-2: %s", locs)
            return range(self.translate_col_label(match.group(1))-1,
                         self.translate_col_label(match.group(2)))

        match = self.patterns['singleton_alpha'].match(locs)
        if match:
            logging.debug("Matched a singleton column: %s", locs)
            return [self.translate_col_label(match.group(1))-1]

        match = self.patterns['singleton_num'].match(locs)
        if match:
            logging.debug("Matched a singleton row: %s", locs)
            return [int(match.group(1))-1]

        match = self.patterns['col_label'].match(locs)
        if match:
            logging.debug("Matched a column: %s", locs)
            return [self.translate_col_label(locs)]

        match = self.patterns['row_label'].match(locs)
        if match:
            logging.debug("Matched a row: %s", locs)
            return [int(locs)-1]

        logging.error("Could not parse a time coordinate from %s",locs)

    def parse_tsr_metadata(self, md_json):
        md_dict = {}
        for md_sec in md_json:
            loc = md_sec['loc']
            if type(loc) == int:
                md_dict[md_sec['name']] = int(loc)-1
            else:
                md_dict[md_sec['name']]= self.translate_col_label(loc)-1

        return md_dict


class SpreadsheetObject(object):
    def __init__(self):
        self.TimeSeries = []
        self.Metadata = {}

    def add_timeseries(self, tsobj):
        self.TimeSeries.append(tsobj)

    def add_metadata(self, mdvals):
        self.Metadata.update(mdvals)

class ExtractSpreadsheet(object):

    def __init__(self, spreadsheet_fn, annotations_fn):
        self.book = pyexcel.get_book(file_name=spreadsheet_fn,auto_detect_datetime=False)
        self.annotations = self.load_annotations(annotations_fn)


    def process(self):
        anidx=0
        timeseries = []
        for annotation in self.annotations:
            #spreadsheet = SpreadsheetObject()
            ssa = SpreadsheetAnnotation(annotation)
            data = self.book.sheet_by_index(anidx)
            parsed = []
            for tsr in ssa.timeseries_regions:
                for parsed_tsr in tsr.parse(data):
                    parsed.append(parsed_tsr)
#                logging.info("%s",parsed)
            timeseries.append(parsed)
                # for ts in tsr.parse(data):
                #     spreadsheet.add_timeseries(ts)
            # self.spreadsheets.append(spreadsheet)
            # for md in ssa.metadata:
            #     self.spreadsheet.add_metadata(md.parse(data))
            anidx+=1
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
