import os
from hangar import Repository
import torchvision
import numpy as np

data = torchvision.datasets.MNIST('.', download=True)
path = os.path.dirname(os.path.abspath(__file__))
repo = Repository(path=path)
repo.init(user_name='hhsecond', user_email='sherin@tensorwerk.com', remove_old=True)
co = repo.checkout(write=True)
co.datasets.init_dataset('MNIST', shape=(28, 28), dtype=np.uint8)
co.datasets.init_dataset('Label', shape=(1,), dtype=np.int64)
mnist_dset = co.datasets['MNIST']
label_dset = co.datasets['Label']

with mnist_dset, label_dset:
    for i, (image, label) in enumerate(data):
        print(i)
        mnist_dset[str(i)] = np.array(image)
        label_dset[str(i)] = np.array([label])
co.commit('0.1')
co.close()

co = repo.checkout()
mnist = co.datasets['MNIST']
mnistlabel = co.datasets['Label']
print(len(mnist))
print(len(mnistlabel))
