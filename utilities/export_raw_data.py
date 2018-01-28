import json
import os
import codecs
import gzip
from argparse import ArgumentParser

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-i", "--src", action="store", type=str, dest="src_path", required=True)
    parser.add_argument("-o", "--dst", action="store", type=str, dest="dst_path", required=True)
    parser.add_argument("--gzip", action="store_true", dest="gzip")
    args, _ = parser.parse_known_args()

    src_path = os.path.abspath(args.src_path)
    dst_path = os.path.abspath(args.dst_path)
    if not os.path.exists(src_path) or not os.path.isdir(src_path):
        print 'invalid source path'
        exit()

    data_paths = list()
    for data_name in os.listdir(src_path):
        data_path = os.path.join(src_path, data_name)
        if os.path.isdir(data_path):
            data_paths.append(data_path)

    output = gzip.open(dst_path, 'w') if args.gzip else codecs.open(dst_path, 'w')
    for data_path in data_paths:
        for name in os.listdir(data_path):
            name, ext = os.path.splitext(name)
            if ext == '.json':
                obj = None
                print 'processing', name
                with codecs.open(os.path.join(data_path, name + '.json'), 'r') as f:
                    obj = json.loads(f.read())
                with codecs.open(os.path.join(data_path, name + '.html'), 'r') as f:
                    obj['raw_content'] = f.read()
                output.write(json.dumps(obj) + '\n')
    output.close()
    print 'done'
