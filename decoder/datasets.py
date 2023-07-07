import os
import numpy as np
import torch
from torch.utils.data import Dataset
import pytorch_lightning as pl
from torch.utils.data.dataset import random_split
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision import datasets

class OneLayerDataset(Dataset):
    def __init__(self, model_type, dataset_type, layer_idx):
        self.dataset_path = f'../underlying/saved_models/{model_type}-{dataset_type}/'
        self.layer = f'layers.{layer_idx}.weight'
        self.num_classes = torch.load(self.dataset_path + f'seed-{0}')[self.layer].shape[0]

    def __len__(self):
        num_models = len(os.listdir(self.dataset_path))
        return num_models * self.num_classes

    def __getitem__(self, idx):
        # get model and class indices
        model_idx = idx // self.num_classes
        class_idx = idx % self.num_classes

        # load relevant data
        model = torch.load(self.dataset_path + f'seed-{model_idx}')
        weights = model[self.layer].to('cpu')

        # extend weight vectors with chosen class marked
        weights = torch.cat((weights, torch.zeros((weights.shape[0], 1), device=weights.device)), dim=1)
        weights[class_idx, -1] = 1

        #weights = torch.zeros(weights.shape, device=weights.device)
        #weights[0, class_idx] = 1

        # shuffle rows of weight matrix
        weights = weights[torch.randperm(weights.shape[0])]

        return weights, torch.Tensor([class_idx])

class OneLayerDataModule(pl.LightningDataModule):
    def __init__(self, model_type, dataset_type, layer_idx, input_dim, batch_size, num_workers):
        super().__init__()
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.input_dim = input_dim
        self.model_type = model_type
        self.dataset_type = dataset_type
        self.layer_idx = layer_idx

    def prepare_data(self):
        return

    def setup(self, stage=None):
        dataset = OneLayerDataset(self.model_type, self.dataset_type, self.layer_idx)
       
        self.train, self.valid, self.test = random_split(dataset, lengths=[0.8, 0.1, 0.1])

    def train_dataloader(self):
        train_loader = DataLoader(
            dataset=self.train,
            batch_size=self.batch_size,
            drop_last=True,
            shuffle=True,
            num_workers=self.num_workers,
        )
        return train_loader

    def val_dataloader(self):
        valid_loader = DataLoader(
            dataset=self.valid,
            batch_size=self.batch_size,
            drop_last=True, # TODO: need to figure out why this is necessary
            shuffle=False,
            num_workers=self.num_workers,
        )
        return valid_loader

    def test_dataloader(self):
        test_loader = DataLoader(
            dataset=self.test,
            batch_size=self.batch_size,
            drop_last=False,
            shuffle=False,
            num_workers=self.num_workers,
        )
        return test_loader