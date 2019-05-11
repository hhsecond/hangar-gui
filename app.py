import argparse
import ast
from sanic import Sanic
from sanic.response import json
from hangar import Repository
from PIL import Image
import base64
from io import BytesIO


parser = argparse.ArgumentParser()
parser.add_argument('--path', type=str, help='Path to a hangar repo')
args = parser.parse_args()
repo = Repository(path=args.path)
co = repo.checkout()
try:
    repo.status()
except AttributeError:
    raise RuntimeError('Repository not initialized')

dtypenummap = {2: 'uint8', 7: 'int64'}


def get_dset_info():
    dset2frontend = []
    for k, v in co.datasets.items():
        each = {}
        each['name'] = v._dsetn
        each['is_var'] = v._schema_variable
        each['max_shape'] = str(v._schema_max_shape)
        each['dtype'] = dtypenummap.get(v._schema_dtype_num, v._schema_dtype_num)
        each['no_of_samples'] = len(v)
        dset2frontend.append(each)
    return dset2frontend


def get_samples_info(dset_name, limit):
    totalsamples = []
    dset = co.datasets[dset_name]
    for name, sample in dset.items():
        limit -= 1
        each = {}
        each['name'] = name
        each['shape'] = str(sample.shape)
        totalsamples.append(each)
        if limit == 0:
            return totalsamples


def get_one_sample(dset_name, sample_name):
    return co.datasets[dset_name][sample_name].tolist()


def compile_function(code, fn_name):
    c = compile(code, 'postprocess', 'exec')
    exec(c)
    return locals()[fn_name]


def compile_and_get_name(code):
    c = compile(code, 'postprocess', 'exec', ast.PyCF_ONLY_AST)
    if len(c.body) > 1:
        return None
    else:
        fn_name = c.body[0].name
        c = compile(code, 'postprocess', 'exec')
        exec(c)
        try:
            locals()[fn_name]
        except KeyError:
            return None
        else:
            return fn_name


app = Sanic()


@app.route("/datasets")
async def datasets(request):
    dsetinfo = get_dset_info()
    return json(dsetinfo)


@app.route("/datasets/<dset>/samples")
async def samples(request, dset):
    limit = int(request.args.get('limit', 100))
    allsamples = get_samples_info(dset, limit)
    return json(allsamples)


@app.route("/datasets/<dset>/samples/<sample>")
async def each_sample(request, dset, sample):
    fn_name = request.args.get('function-name')
    if fn_name:
        code = co.metadata[fn_name]
        fn = compile_function(code, fn_name)
        arr = co.datasets[dset][sample]
        out = fn(repo, arr)
        return json({'status': 'success', 'data': out})
    else:
        return json({'status': 'failure'})


@app.route("/upload-function", methods=["POST"])
async def upload_function(request):
    code = request.json['function']
    fn_name = compile_and_get_name(code)
    if fn_name:
        co = repo.checkout(write=True)
        co.metadata[fn_name] = code
        co.commit()
        co.close()
        return json({'status': 'success'})
    else:
        return json({'status': 'failure'})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
