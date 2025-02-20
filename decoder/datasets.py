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
    def __init__(self, dataset_path, layer_idx, transpose_weights=False, preprocessing=None):
        self.dataset_path = dataset_path
        self.layer = f'layers.{layer_idx}.weight'
        self.transpose_weights = transpose_weights
        self.preprocessing = preprocessing

        if not transpose_weights:
            self.num_classes = torch.load(self.dataset_path + f'/seed-{0}')[self.layer].shape[0]
        else:
            self.num_classes = torch.load(self.dataset_path + f'/seed-{0}')[self.layer].shape[1]

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
        if self.transpose_weights:
            weights = weights.T
        #weights = torch.zeros(weights.shape, device=weights.device)
        #weights[0, class_idx] = 1

        # shuffle rows of weight matrix
        tmp = weights[class_idx].clone()
        weights[class_idx] = weights[0]
        weights[0] = tmp

        weights[1:,:] = weights[1:,:][torch.randperm(weights.shape[0] - 1)]

        # apply preprocessing 
        if self.preprocessing == 'multiply_transpose':
            # compute matrix of angles between weight vectors
            weights = weights @ weights.T
            weights = weights / torch.norm(weights, dim=1).unsqueeze(1)
            weights = weights / torch.norm(weights, dim=0).unsqueeze(0)

        elif self.preprocessing == 'dim_reduction':
            U, _, _ = torch.pca_lowrank(weights.T, q=self.num_classes, center=True)
            weights = weights @ U
            
            # permute weights columns
            weights = weights[:,torch.randperm(weights.shape[1])]


        return weights, torch.Tensor([class_idx])

class OneLayerDataModule(pl.LightningDataModule):
    def __init__(self, dataset_path, layer_idx, input_dim, batch_size, num_workers, transpose_weights=False, preprocessing=None):
        super().__init__()
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.input_dim = input_dim
        self.dataset_path = dataset_path
        self.layer_idx = layer_idx
        self.transpose_weights = transpose_weights
        self.preprocessing = preprocessing

    def prepare_data(self):
        return

    def setup(self, stage=None):
        dataset = OneLayerDataset(self.dataset_path, self.layer_idx, transpose_weights=self.transpose_weights, preprocessing=self.preprocessing)

        # Created using indices from 0 to train_size.
        self.train = torch.utils.data.Subset(dataset, range(int(len(dataset) * 0.8)))
        self.valid = torch.utils.data.Subset(dataset, range(int(len(dataset) * 0.8), int(len(dataset))))
        self.test = None

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