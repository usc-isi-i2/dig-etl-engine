

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