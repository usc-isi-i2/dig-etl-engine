import re
import LocationRange as lr

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
        rnge = lr.LocationRange()
        if match:
            for val in [x.strip() for x in match.group(1).split(',')]:
                parts = val.split(':')
                translate_fn = self.translate_row_label
                if self.is_column(parts[0]):
                    translate_fn = self.translate_col_label

                if len(parts) == 1:
                        rnge.add_component(lr.LocationRangeSingletonComponent(translate_fn(parts[0])-1))

                elif len(parts) == 2:
                    if self.is_sentinel(parts[1]):
                        rnge.add_component(lr.LocationRangeInfiniteIntervalComponent(start=translate_fn(parts[0])-1))
                    else:
                        rnge.add_component(lr.LocationRangeIntervalComponent(start=translate_fn(parts[0])-1,
                                                                             end=translate_fn(parts[1])))

                elif len(parts) == 3:

                    if self.is_sentinel(parts[1]):
                        rnge.add_component(lr.LocationRangeInfiniteIntervalComponent(start=translate_fn(parts[0])-1,
                                                                                     increment=int(parts[1])))
                    else:
                        rnge.add_component(lr.LocationRangeIntervalComponent(start=translate_fn(parts[0])-1,
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