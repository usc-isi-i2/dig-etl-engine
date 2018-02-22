import json
import re

class parse_input:

    def __init__(self, file_type, file_path, out_path):
        self.type = file_type
        self.src = file_path
        self.dst = out_path

    def parse_line(self, line, series_alias):
        line_json = json.loads(line)
        return self.modify_input(line_json[series_alias])

    def parse_date(self, date):
        d = re.split("( +)|T", date)[0]
        splitted_date = d.split("-")
        year = int(splitted_date[0])
        month = 0
        day = 0
        if len(splitted_date)>1:
            month = int(splitted_date[1])
        if len(splitted_date)>2:
            day = int(splitted_date[2])
        return int(year), int(month), int(day)

    def is_greater(self, date, date1):
        year, month, day = self.parse_date(date)
        year1, month1, day1  = self.parse_date(date1)
        if year > year1:
            return True
        if year1 > year:
            return False
        if month > month1:
            return True
        if month < month1:
            return False
        if day > day1:
            return True
        return False

    def get_date_difference(self, date1, date2):
        year, month, day = self.parse_date(date1)
        year2, month2, day2 = self.parse_date(date2)
        diff = (year - year2) * 365
        diff += (month - month2) * 30 # some inaccuracies here
        diff += day - day2
        return 1.0 * diff / 365

# assuming the dates formats are yy/month/dayT00:00:00
    def modify_input(self, time_series, normalizing):
        xarray = []
        yarray = []
        x_labels = []
        for i in range(len(time_series)):
            if time_series[i][1] == '':
                continue
            yarray.append(time_series[i][1])
            x_labels.append(time_series[i][0])

    # sort the input here:
        sorted_indices = sorted(range(len(x_labels)), key=lambda x: x_labels[x])
        y = [yarray[x] for x in sorted_indices]
        x = sorted(x_labels)
        xarray.append(0)
        for i in range(len(x) - 1):
            xarray.append(self.get_date_difference(x[i+1], x[i]) + xarray[i])

        # scale the x here
        if normalizing:
            max_x = max(xarray)
            max_y = max(y)
            if max_x > 0:
                for i in range(len(xarray)):
                    xarray[i] *= 1.0/max_x
            if max_y > 0:
                for i in range(len(y)):
                    y[i] *= 1.0/max_y
        return x, xarray, y

    def append_trends_to_series(self, trend):
        self.current_series_ref['ts_description'] = trend

    def save_output(self):
        with open(self.dst, mode='w') as output:
            json.dump(self.source_json, output)
            output.close()

    def end_output(self):
        self.out_file.close()

    def save_and_store_output(self, trend):
        self.source_json['ts_description'] = trend
        json.dump(self.source_json, self.out_file)

    def parse_jl_file(self, in_file, ts_key):
        self.out_file = open(self.dst, mode='w')
        with open(in_file) as f:
            for line in f:
                self.source_json = json.loads(line)

                yield self.modify_input(self.source_json[ts_key], False)

    def parse_json_file(self, infile, ts_key):
        x_labels = []
        with open(infile) as f:
            for line in f:
                self.source_json = x = json.loads(line)
                for sheet in x:
                    for time_s in sheet:
                        self.current_series_ref = time_s
                        yield self.modify_input(time_s[ts_key], False)



    def parse_raw_knoema(self, infile):
        with open(infile) as f:
            for line in f:
                res = []
                json_obj = json.loads(line)
                ts_data = json_obj['data']
                for time_point in ts_data:
                    res.append([time_point['Time'], time_point['Value']])
                yield self.modify_input(res, True)
