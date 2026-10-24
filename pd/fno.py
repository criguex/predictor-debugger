import torch
from torch import nn
from torch.nn import functional as F

WIDTH, MODES, LAYERS, HIDDEN = 24, 8, 4, 128


class SpectralConv3d(nn.Module):
    def __init__(self, width, modes):
        super().__init__()
        self.modes = modes
        self.weights = nn.Parameter(torch.rand(4, width, width, modes, modes, modes, dtype=torch.cfloat) / (width * width))

    def forward(self, x):
        n, m = x.shape[-1], self.modes
        spectrum = torch.fft.rfftn(x, dim=(-3, -2, -1))
        out = torch.zeros_like(spectrum)
        corners = ((slice(0, m), slice(0, m)), (slice(-m, None), slice(0, m)), (slice(0, m), slice(-m, None)), (slice(-m, None), slice(-m, None)))
        for weights, (sx, sy) in zip(self.weights, corners):
            out[:, :, sx, sy, :m] = torch.einsum("bixyz,ioxyz->boxyz", spectrum[:, :, sx, sy, :m], weights)
        return torch.fft.irfftn(out, s=(n, n, n), dim=(-3, -2, -1))


class FNO(nn.Module):
    def __init__(self):
        super().__init__()
        self.lift = nn.Conv3d(3, WIDTH, 1)
        self.spectral = nn.ModuleList(SpectralConv3d(WIDTH, MODES) for _ in range(LAYERS))
        self.local = nn.ModuleList(nn.Conv3d(WIDTH, WIDTH, 1) for _ in range(LAYERS))
        self.head = nn.Sequential(nn.Conv3d(WIDTH, HIDDEN, 1), nn.GELU(), nn.Conv3d(HIDDEN, 3, 1))

    def forward(self, x):
        x = self.lift(x)
        for index, (spectral, local) in enumerate(zip(self.spectral, self.local)):
            x = spectral(x) + local(x)
            if index < LAYERS - 1:
                x = F.gelu(x)
        return self.head(x)
