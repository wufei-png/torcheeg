import os
from typing import Any, Callable, Dict, Tuple, Union

import numpy as np

from torcheeg.io import EEGSignalIO, MetaInfoIO

from .base_dataset import BaseDataset


class NumpyDataset(BaseDataset):
    r'''
    A general dataset, this class converts EEG signals and annotations in Numpy format into dataset types, and caches the generated results in a unified input and output format (IO).

    A tiny case shows the use of :obj:`NumpyDataset`:

    .. code-block:: python

        # Mock 100 EEG samples. Each EEG signal contains a signal of length 1 s at a sampling rate of 128 sampled by 32 electrodes.
        X = np.random.randn(100, 32, 128)

        # Mock 100 labels, denoting valence and arousal of subjects during EEG recording.
        y = {
            'valence': np.random.randint(10, size=100),
            'arousal': np.random.randint(10, size=100)
        }
        dataset = NumpyDataset(X=X,
                               y=y,
                               io_path=io_path,
                               offline_transform=transforms.Compose(
                                   [transforms.BandDifferentialEntropy()]),
                               online_transform=transforms.ToTensor(),
                               label_transform=transforms.Compose([
                                   transforms.Select('valence'),
                                   transforms.Binary(5.0),
                               ]),
                               num_worker=2,
                               num_samples_per_worker=50)
        print(dataset[0])
        # EEG signal (torch.Tensor[32, 4]),
        # coresponding baseline signal (torch.Tensor[32, 4]),
        # label (int)

    In particular, TorchEEG utilizes the producer-consumer model to allow multi-process data preprocessing. If your data preprocessing is time consuming, consider increasing :obj:`num_worker` for higher speedup. If running under Windows, please use the proper idiom in the main module:

    .. code-block:: python
    
        if __name__ == '__main__':
            # Mock 100 EEG samples. Each EEG signal contains a signal of length 1 s at a sampling rate of 128 sampled by 32 electrodes.
            X = np.random.randn(100, 32, 128)

            # Mock 100 labels, denoting valence and arousal of subjects during EEG recording.
            y = np.random.randint(10, size=100, 2)
            dataset = NumpyDataset(X=X,
                                y=y,
                                io_path=io_path,
                                offline_transform=transforms.Compose(
                                    [transforms.BandDifferentialEntropy()]),
                                online_transform=transforms.ToTensor(),
                                label_transform=transforms.Compose([
                                    transforms.Select('0'),
                                    transforms.Binary(5.0),
                                ]),
                                num_worker=2,
                                num_samples_per_worker=50)
            print(dataset[0])
            # EEG signal (torch.Tensor[32, 4]),
            # coresponding baseline signal (torch.Tensor[32, 4]),
            # label (int)

    Args:
        X (np.ndarray): An array in :obj:`numpy.ndarray` format representing the EEG signal samples in the dataset. The shape of the array is :obj:`[num_sample, ...]` where :obj:`num_sample` is the number of samples. :obj:`X` and :obj:`y` also allow lists of strings to be used together, representing paths to corresponding files of :obj:`X` and :obj:`y` (generated using :obj:`np.save`).
        y (np.ndarray):An array in :obj:`numpy.ndarray` format representing the labels of EEG signal samples, and the values are lists of labels whose length is consistent with the EEG signal samples. The name of the label is automatically generated from the string corresponding to its index.
        online_transform (Callable, optional): The transformation of the EEG signals and baseline EEG signals. The input is a :obj:`np.ndarray`, and the ouput is used as the first and second value of each element in the dataset. (default: :obj:`None`)
        offline_transform (Callable, optional): The usage is the same as :obj:`online_transform`, but executed before generating IO intermediate results. (default: :obj:`None`)
        label_transform (Callable, optional): The transformation of the label. The input is an information dictionary, and the ouput is used as the third value of each element in the dataset. (default: :obj:`None`)
        before_trial (Callable, optional): The hook performed on the trial to which the sample belongs. It is performed before the offline transformation and thus typically used to implement context-dependent sample transformations, such as moving averages, etc. The input and output of this hook function should be a :obj:`np.ndarray`, whose shape is (number of EEG samples per trial, ...).
        after_trial (Callable, optional): The hook performed on the trial to which the sample belongs. It is performed after the offline transformation and thus typically used to implement context-dependent sample transformations, such as moving averages, etc. The input and output of this hook function should be a sequence of dictionaries representing a sequence of EEG samples. Each dictionary contains two key-value pairs, indexed by :obj:`eeg` (the EEG signal matrix) and :obj:`key` (the index in the database) respectively
        io_path (str): The path to generated unified data IO, cached as an intermediate result. (default: :obj:`./io/deap`)
        io_size (int): Maximum size database may grow to; used to size the memory mapping. If database grows larger than ``map_size``, an exception will be raised and the user must close and reopen. (default: :obj:`10485760`)
        io_mode (str): Storage mode of EEG signal. When io_mode is set to :obj:`lmdb`, TorchEEG provides an efficient database (LMDB) for storing EEG signals. LMDB may not perform well on limited operating systems, where a file system based EEG signal storage is also provided. When io_mode is set to :obj:`pickle`, pickle-based persistence files are used. (default: :obj:`lmdb`)
        num_worker (int): How many subprocesses to use for data processing. (default: :obj:`0`)
        num_samples_per_worker (int): The number of samples processed by each process. Once the specified number of samples are processed, the process will be destroyed and new processes will be created to perform new tasks. (default: :obj:`100`)
        verbose (bool): Whether to display logs during processing, such as progress bars, etc. (default: :obj:`True`)
        in_memory (bool): Whether to load the entire dataset into memory. If :obj:`in_memory` is set to True, then the first time an EEG sample is read, the entire dataset is loaded into memory for subsequent retrieval. Otherwise, the dataset is stored on disk to avoid the out-of-memory problem. (default: :obj:`False`)    
    '''

    def __init__(self,
                 X: np.ndarray,
                 y: Dict,
                 online_transform: Union[None, Callable] = None,
                 offline_transform: Union[None, Callable] = None,
                 label_transform: Union[None, Callable] = None,
                 before_trial: Union[None, Callable] = None,
                 after_trial: Union[Callable, None] = None,
                 io_path: str = './io/numpy',
                 io_size: int = 10485760,
                 io_mode: str = 'lmdb',
                 num_worker: int = 0,
                 num_samples_per_worker: int = 100,
                 verbose: bool = True,
                 in_memory: bool = False):
        # pass all arguments to super class
        params = {
            'online_transform': online_transform,
            'offline_transform': offline_transform,
            'label_transform': label_transform,
            'before_trial': before_trial,
            'after_trial': after_trial,
            'io_path': io_path,
            'io_size': io_size,
            'io_mode': io_mode,
            'num_worker': num_worker,
            'num_samples_per_worker': num_samples_per_worker,
            'verbose': verbose,
            'in_memory': in_memory
        }
        super().__init__(**params, X=X, y=y)
        # save all arguments to __dict__
        self.__dict__.update(params)

    @staticmethod
    def __io__(io_path: str = None,
               io_size: int = 10485760,
               io_mode: str = 'lmdb',
               block: Any = None,
               lock: Any = None,
               **kwargs):
        X_block_path, y_block_path, block_id = block
        X = np.load(X_block_path)
        y = np.load(y_block_path)

        before_trial = kwargs.pop('before_trial', None)
        transform = kwargs.pop('offline_transform', None)
        after_trial = kwargs.pop('after_trial', None)

        meta_info_io_path = os.path.join(io_path, 'info.csv')
        eeg_signal_io_path = os.path.join(io_path, 'eeg')

        info_io = MetaInfoIO(meta_info_io_path)
        eeg_io = EEGSignalIO(eeg_signal_io_path,
                             io_size=io_size,
                             io_mode=io_mode)

        if before_trial:
            X = before_trial(X)

        trial_queue = []
        for write_pointer, clip_sample in enumerate(X):

            t_eeg = clip_sample

            if not transform is None:
                t = transform(eeg=clip_sample)
                t_eeg = t['eeg']

            clip_id = f'{block_id}_{write_pointer}'

            # record meta info for each signal
            record_info = {'clip_id': clip_id}
            # y is np.ndarray (n_samples, n_labels)
            record_info.update(
                {f'{i}': y[write_pointer, i] for i in range(y.shape[1])})
            
            if after_trial:
                trial_queue.append({
                    'eeg': t_eeg,
                    'key': clip_id,
                    'info': record_info
                })
            else:
                with lock:
                    eeg_io.write_eeg(t_eeg, clip_id)
                    info_io.write_info(record_info)

        if len(trial_queue) and after_trial:
            trial_queue = after_trial(trial_queue)
            for obj in trial_queue:
                assert 'eeg' in obj and 'key' in obj and 'info' in obj, 'after_trial must return a list of dictionaries, where each dictionary corresponds to an EEG sample, containing `eeg`, `key` and `info` as keys.'
                with lock:
                    eeg_io.write_eeg(obj['eeg'], obj['key'])
                    info_io.write_info(obj['info'])

    @staticmethod
    def __block__(**kwargs):
        io_path = kwargs.pop('io_path', '.')  # str
        X = kwargs.pop('X', None)  # np.ndarray
        y = kwargs.pop('y', None)  # dict
        num_samples_per_worker = kwargs.pop('num_samples_per_worker',
                                            100)  # int

        # check if X is a list of str
        X_str = isinstance(X, list) and all([isinstance(x, str) for x in X])
        y_str = isinstance(y, list) and all([isinstance(y, str) for y in y])

        if X_str and y_str:
            X_y_block_id_list = []
            for block_id, (X_block_path, y_block_path) in enumerate(zip(X, y)):
                X_y_block_id_list.append((X_block_path, y_block_path, block_id))
            return X_y_block_id_list

        X_ndarray = isinstance(X, np.ndarray)
        y_ndarray = isinstance(y, np.ndarray)

        if X_ndarray and y_ndarray:
            indices = np.arange(len(X))
            block_samples_list = np.array_split(
                indices,
                len(X) // num_samples_per_worker)

            X_y_block_id_list = []
            for block_id, sample_indices in enumerate(block_samples_list):
                X_block = X[sample_indices]
                y_block = y[sample_indices]
                # save block to disk
                if not os.path.exists(os.path.join(io_path, 'tmp')):
                    os.makedirs(os.path.join(io_path, 'tmp'))

                X_block_path = os.path.join(io_path, 'tmp', f'{block_id}_x.npy')
                np.save(X_block_path, X_block)

                y_block_path = os.path.join(io_path, 'tmp', f'{block_id}_y.npy')
                np.save(y_block_path, y_block)

                X_y_block_id_list.append((X_block_path, y_block_path, block_id))

            return X_y_block_id_list

        raise ValueError(
            'X and y must be either a list of paths to np.ndarray, or a np.ndarray.'
        )

    def __getitem__(self, index: int) -> Tuple:
        info = self.read_info(index)

        eeg_index = str(info['clip_id'])
        eeg = self.read_eeg(eeg_index)

        signal = eeg
        label = info

        if self.online_transform:
            signal = self.online_transform(eeg=eeg)['eeg']

        if self.label_transform:
            label = self.label_transform(y=info)['y']

        return signal, label

    @property
    def repr_body(self) -> Dict:
        return dict(
            super().repr_body, **{
                'online_transform': self.online_transform,
                'offline_transform': self.offline_transform,
                'label_transform': self.label_transform,
                'before_trial': self.before_trial,
                'after_trial': self.after_trial,
                'num_worker': self.num_worker,
                'num_samples_per_worker': self.num_samples_per_worker,
                'verbose': self.verbose,
                'io_size': self.io_size
            })
