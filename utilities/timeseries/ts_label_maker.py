import json
import codecs
import sys
import os
import string

spec = sys.argv[1]
fn = sys.argv[2]
fn_temp = fn + '.tmp'

class PartialFormatter(string.Formatter):
    def __init__(self, missing='~~', bad_fmt='!!'):
        self.missing, self.bad_fmt=missing, bad_fmt

    def get_field(self, field_name, args, kwargs):
        # Handle a key not found
        try:
            val=super(PartialFormatter, self).get_field(field_name, args, kwargs)
            # Python 3, 'super().get_field(field_name, args, kwargs)' works
        except (KeyError, AttributeError):
            val=None,field_name
        return val

    def format_field(self, value, spec):
        # handle an invalid format
        if value==None: return self.missing
        try:
            return super(PartialFormatter, self).format_field(value, spec)
        except ValueError:
            if self.bad_fmt is not None: return self.bad_fmt
            else: raise

f_spec = codecs.open(spec, 'r')
f_input = codecs.open(fn, 'r')
f_output = codecs.open(fn_temp, 'w')

fmt = PartialFormatter(missing='')

label_generator = json.loads(f_spec.read())['TS_meaure_transfer']['label']
for line in f_input:
    obj = json.loads(line)
    if 'measure' in obj:
        obj['measure']['metadata']['label'] = fmt.format(label_generator, **obj['measure']['metadata'])
    f_output.write(json.dumps(obj) + '\n')

f_spec.close()
f_input.close()
f_output.close()

# os.remove(fn)
# os.rename(fn_temp, fn)