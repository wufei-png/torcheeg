from typing import Tuple

import torch
import torch.nn as nn


class BGenerator(nn.Module):
    r'''
    TorchEEG provides an EEG feature generator based on CNN architecture and GAN for generating EEG grid representations of different frequency bands based on a given class label.

    .. code-block:: python

        import torch

        from torcheeg.models.gan.bgan import BGenerator
        
        g_model = BGenerator(in_channels=128)
        z = torch.normal(mean=0, std=1, size=(1, 128))
        fake_X = g_model(z)

    Args:
        in_channels (int): The input feature dimension (of noise vectors). (default: :obj:`128`)
        out_channels (int): The generated feature dimension of each electrode. (default: :obj:`4`)
        grid_size (tuple): Spatial dimensions of grid-like EEG representation. (default: :obj:`(9, 9)`)
    '''
    def __init__(self,
                 in_channels: int = 128,
                 out_channels: int = 4,
                 grid_size: Tuple[int, int] = (9, 9)):
        super(BGenerator, self).__init__()

        self.in_channels = in_channels
        self.out_channels = out_channels
        self.grid_size = grid_size

        self.deproj = nn.Sequential(
            nn.Linear(in_channels, in_channels * 4 * 3 * 3), nn.LeakyReLU())

        self.deconv1 = nn.Sequential(
            nn.ConvTranspose2d(in_channels * 4,
                               in_channels * 2,
                               kernel_size=3,
                               stride=2,
                               padding=1,
                               bias=True), nn.BatchNorm2d(in_channels * 2),
            nn.LeakyReLU())
        self.deconv2 = nn.Sequential(
            nn.ConvTranspose2d(in_channels * 2,
                               in_channels * 2,
                               kernel_size=3,
                               stride=1,
                               padding=1,
                               bias=True), nn.BatchNorm2d(in_channels * 2),
            nn.LeakyReLU())
        self.deconv3 = nn.Sequential(
            nn.ConvTranspose2d(in_channels * 2,
                               in_channels,
                               kernel_size=3,
                               stride=2,
                               padding=1,
                               bias=True), nn.BatchNorm2d(in_channels),
            nn.LeakyReLU())
        self.deconv4 = nn.ConvTranspose2d(in_channels,
                                          out_channels,
                                          kernel_size=3,
                                          stride=1,
                                          padding=1,
                                          bias=True)

    def forward(self, x: torch.Tensor):
        r'''
        Args:
            x (torch.Tensor): a random vector, the ideal input shape is :obj:`[n, 128]`. Here, :obj:`n` corresponds to the batch size, and :obj:`128` corresponds to :obj:`in_channels`.

        Returns:
            torch.Tensor[n, 4, 9, 9]: the generated fake EEG signals. Here, :obj:`4` corresponds to the :obj:`out_channels`, and :obj:`(9, 9)` corresponds to the :obj:`grid_size`.
        '''
        x = self.deproj(x)
        x = x.view(-1, self.in_channels * 4, 3, 3)
        x = self.deconv1(x)
        x = self.deconv2(x)
        x = self.deconv3(x)
        x = self.deconv4(x)
        return x


class BDiscriminator(nn.Module):
    r'''
    TorchEEG provides an EEG feature generator based on CNN architecture and GAN for generating EEG grid representations of different frequency bands based on a given class label.

    .. code-block:: python

        g_model = BGenerator(in_channels=128)
        d_model = BDiscriminator(in_channels=4)
        z = torch.normal(mean=0, std=1, size=(1, 128))
        fake_X = g_model(z)
        disc_X = d_model(fake_X)

    Args:
        in_channels (int): The feature dimension of each electrode. (default: :obj:`4`)
        grid_size (tuple): Spatial dimensions of grid-like EEG representation. (default: :obj:`(9, 9)`)
        hid_channels (int): The number of hidden nodes in the first fully connected layer. (default: :obj:`32`)
    '''
    def __init__(self,
                 in_channels: int = 4,
                 grid_size: Tuple[int, int] = (9, 9),
                 hid_channels: int = 64):
        super(BDiscriminator, self).__init__()

        self.in_channels = in_channels
        self.grid_size = grid_size
        self.hid_channels = hid_channels

        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels,
                      hid_channels,
                      kernel_size=3,
                      stride=1,
                      padding=1,
                      bias=True), nn.BatchNorm2d(hid_channels), nn.LeakyReLU())
        self.conv2 = nn.Sequential(
            nn.Conv2d(hid_channels,
                      hid_channels * 2,
                      kernel_size=3,
                      stride=2,
                      padding=1,
                      bias=True), nn.BatchNorm2d(hid_channels * 2),
            nn.LeakyReLU())
        self.conv3 = nn.Sequential(
            nn.Conv2d(hid_channels * 2,
                      hid_channels * 2,
                      kernel_size=3,
                      stride=1,
                      padding=1,
                      bias=True), nn.BatchNorm2d(hid_channels * 2),
            nn.LeakyReLU())
        self.conv4 = nn.Sequential(
            nn.Conv2d(hid_channels * 2,
                      hid_channels * 4,
                      kernel_size=3,
                      stride=2,
                      padding=1,
                      bias=True), nn.BatchNorm2d(hid_channels * 4),
            nn.LeakyReLU())

        self.proj = nn.Linear(self.feature_dim, 1)

    @property
    def feature_dim(self):
        with torch.no_grad():
            mock_eeg = torch.zeros(1, self.in_channels, *self.grid_size)

            mock_eeg = self.conv1(mock_eeg)
            mock_eeg = self.conv2(mock_eeg)
            mock_eeg = self.conv3(mock_eeg)
            mock_eeg = self.conv4(mock_eeg)

        return mock_eeg.flatten(start_dim=1).shape[-1]

    def forward(self, x: torch.Tensor):
        r'''
        Args:
            x (torch.Tensor): EEG signal representation, the ideal input shape is :obj:`[n, 4, 9, 9]`. Here, :obj:`n` corresponds to the batch size, :obj:`4` corresponds to the :obj:`in_channels`, and :obj:`(9, 9)` corresponds to the :obj:`grid_size`.

        Returns:
            torch.Tensor[n, 1]: Predicts the result of whether a given sample is a fake sample or not. Here, :obj:`n` corresponds to the batch size.
        '''
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x)
        x = x.flatten(start_dim=1)
        x = self.proj(x)
        return x