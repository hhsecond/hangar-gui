import requests

# function = """
# def get_previous(repo, arr):
#     co = repo.checkout()
#     data = co.datasets['MNIST']['1']
#     img = Image.fromarray(data)
#     buffered = BytesIO()
#     img.save(buffered, format="JPEG")
#     return base64.b64encode(buffered.getvalue())
# """
# url = 'http://0.0.0.0:8001/upload-function'
# out = requests.post(url, json={'function': function})
# print(out.text)


url = 'http://0.0.0.0:8001/datasets/MNIST/samples/1?function-name=get_previous'
out = requests.get(url)
print(out.text)
