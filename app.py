import argparse
import ast
from sanic import Sanic
from sanic_cors import CORS
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
    # raise RuntimeError('Repository not initialized')
    pass
    # TODO do this check

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
CORS(app, automatic_options=True)


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
    co = repo.checkout()
    arr = co.datasets[dset][sample]
    if fn_name:
        code = co.metadata[f'fn_name__{fn_name}']
        fn = compile_function(code, fn_name)
        out = fn(repo, arr)
        return json([{'status': 'success', 'data': out}])
    else:
        return json([{'status': 'failure', 'message': 'NoFunctionNameProvided Error'}])


@app.route("/upload-function", methods=["POST"])
async def upload_function(request):
    code = request.json['function']
    fn_name = compile_and_get_name(code)
    if fn_name:
        try:
            co = repo.checkout(write=True)
            co.metadata[f'fn_name__{fn_name}'] = code
            co.commit(f'Added fn_name__{fn_name}')
        except Exception as e:
            ret = json([{'status': 'failure', 'message': 'FunctionNameExist Error'}])
        finally:
            co.close()
        ret = json([{'status': 'success'}])
    else:
        ret = json([{'status': 'failure'}])
    return ret


@app.route("/get-functions")
async def get_functions(request):
    co = repo.checkout()
    out = []
    for key, val in co.metadata.items():
        if key.startswith('fn_name__'):
            out.append({'functionName': key[9:], 'function': val})
    return json(out)


app.static('/', './dist')
app.static('/index', './dist/index.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
