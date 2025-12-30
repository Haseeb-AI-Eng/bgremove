"""
Refinement GAN Module
Implements a U-Net based refinement network for improving photorealism
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from PIL import Image


class UNetRefinement(nn.Module):
    """
    U-Net based refinement network for improving the composition result
    """
    def __init__(self, in_channels=3, out_channels=3, features=[64, 128, 256, 512]):
        super(UNetRefinement, self).__init__()
        self.ups = nn.ModuleList()
        self.downs = nn.ModuleList()
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

        # Down part of UNET
        for feature in features:
            self.downs.append(DoubleConv(in_channels, feature))
            in_channels = feature

        # Up part of UNET
        for feature in reversed(features):
            self.ups.append(
                nn.ConvTranspose2d(
                    feature*2, feature, kernel_size=2, stride=2,
                )
            )
            self.ups.append(DoubleConv(feature*2, feature))

        self.bottleneck = DoubleConv(features[-1], features[-1]*2)
        self.final_conv = nn.Conv2d(features[0], out_channels, kernel_size=1)

    def forward(self, x):
        skip_connections = []

        for down in self.downs:
            x = down(x)
            skip_connections.append(x)
            x = self.pool(x)

        x = self.bottleneck(x)
        skip_connections = skip_connections[::-1]

        for idx in range(0, len(self.ups), 2):
            x = self.ups[idx](x)
            skip_connection = skip_connections[idx//2]

            if x.shape != skip_connection.shape:
                x = F.interpolate(x, size=skip_connection.shape[2:])

            concat_skip = torch.cat((skip_connection, x), dim=1)
            x = self.ups[idx+1](concat_skip)

        return torch.sigmoid(self.final_conv(x))


class DoubleConv(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(DoubleConv, self).__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, 1, 1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, 1, 1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.conv(x)


class SPADELayer(nn.Module):
    """
    Simplified SPADE (Spatially-Adaptive Normalization) layer
    """
    def __init__(self, norm_nc, label_nc):
        super().__init__()

        self.param_free_norm = nn.BatchNorm2d(norm_nc, affine=False)
        
        nhidden = 128
        self.mlp_shared = nn.Sequential(
            nn.Conv2d(label_nc, nhidden, kernel_size=3, padding=1),
            nn.ReLU()
        )
        self.mlp_gamma = nn.Conv2d(nhidden, norm_nc, kernel_size=3, padding=1)
        self.mlp_beta = nn.Conv2d(nhidden, norm_nc, kernel_size=3, padding=1)

    def forward(self, x, segmap):
        normalized = self.param_free_norm(x)
        
        # Resize segmap to match x's size
        segmap = F.interpolate(segmap, size=x.size()[2:], mode='nearest')
        
        actv = self.mlp_shared(segmap)
        gamma = self.mlp_gamma(actv)
        beta = self.mlp_beta(actv)
        
        out = normalized * (1 + gamma) + beta
        
        return out


class ALIASRefinement(nn.Module):
    """
    Implementation of ALIAS (Adaptive Layout-Identity Aware Normalization) inspired refinement
    """
    def __init__(self, in_channels=3, out_channels=3):
        super(ALIASRefinement, self).__init__()
        
        # Encoder
        self.enc1 = self._make_encoder_block(in_channels, 64)
        self.enc2 = self._make_encoder_block(64, 128)
        self.enc3 = self._make_encoder_block(128, 256)
        self.enc4 = self._make_encoder_block(256, 512)
        
        # Bottleneck
        self.bottleneck = nn.Sequential(
            nn.Conv2d(512, 1024, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(1024, 1024, 3, padding=1),
            nn.ReLU(inplace=True)
        )
        
        # Decoder with skip connections - standard U-Net design
        # Each block handles the concatenated skip connection input
        self.dec4 = self._make_decoder_block(1024, 512)  # bottleneck (no skip conn yet)
        self.dec3 = self._make_decoder_block(1024, 256)  # upsampled dec4 (512) + e4 skip (512) = 1024 total
        self.dec2 = self._make_decoder_block(512, 128)   # upsampled dec3 (256) + e3 skip (256) = 512 total
        self.dec1 = self._make_decoder_block(256, 64)    # upsampled dec2 (128) + e2 skip (128) = 256 total
        
        # Output layer - expects concatenated final layer (64 from upsampled + 64 from skip = 128 channels)
        self.out_conv = nn.Sequential(
            nn.Conv2d(128, out_channels, 1),
            nn.Tanh()
        )
    
    def _make_encoder_block(self, in_channels, out_channels):
        return nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2)
        )
    
    def _make_decoder_block(self, in_channels, out_channels):
        return nn.Sequential(
            nn.ConvTranspose2d(in_channels, out_channels, kernel_size=4, stride=2, padding=1),  # Transposed conv for upsampling
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1),
            nn.ReLU(inplace=True)
        )
    
    def forward(self, x):
        # Encoder
        e1 = self.enc1(x)
        e2 = self.enc2(e1)
        e3 = self.enc3(e2)
        e4 = self.enc4(e3)

        # Bottleneck
        b = self.bottleneck(e4)

        # Decoder with skip connections - proper U-Net implementation
        d4 = self.dec4(b)  # Input: 1024 channels -> Output: 512 channels, upsampled spatially
        # Match spatial dimensions of upsampled d4 with e4 before concatenating
        e4_resized = self._match_size(d4, e4)  # Resize e4 to match d4's spatial dimensions
        d4_cat = torch.cat([d4, e4_resized], dim=1)  # Concatenate: 512 + 512 = 1024 channels

        d3 = self.dec3(d4_cat)  # Input: 1024 channels -> Output: 256 channels, upsampled spatially
        e3_resized = self._match_size(d3, e3)  # Resize e3 to match d3's spatial dimensions
        d3_cat = torch.cat([d3, e3_resized], dim=1)  # Concatenate: 256 + 256 = 512 channels

        d2 = self.dec2(d3_cat)  # Input: 512 channels -> Output: 128 channels, upsampled spatially
        e2_resized = self._match_size(d2, e2)  # Resize e2 to match d2's spatial dimensions
        d2_cat = torch.cat([d2, e2_resized], dim=1)  # Concatenate: 128 + 128 = 256 channels

        d1 = self.dec1(d2_cat)  # Input: 256 channels -> Output: 64 channels, upsampled spatially
        e1_resized = self._match_size(d1, e1)  # Resize e1 to match d1's spatial dimensions
        d1_cat = torch.cat([d1, e1_resized], dim=1)  # Concatenate: 64 + 64 = 128 channels

        # Output
        out = self.out_conv(d1_cat)

        # Residual connection: add original input to refined output
        refined = torch.tanh(out + F.interpolate(x, size=out.shape[2:], mode='bilinear', align_corners=True))

        # Scale to [0, 1]
        refined = (refined + 1) / 2.0

        return refined

    def _match_size(self, target_tensor, source_tensor):
        """
        Resize source_tensor to match target_tensor's spatial dimensions
        """
        if target_tensor.shape[2:] != source_tensor.shape[2:]:
            return F.interpolate(source_tensor, size=target_tensor.shape[2:],
                                mode='bilinear', align_corners=True)
        return source_tensor


def refine_image_with_unet(input_image, device='cpu'):
    """
    Refine an image using the U-Net refinement network
    """
    # Convert PIL image to tensor
    if isinstance(input_image, Image.Image):
        np_image = np.array(input_image).astype(np.float32) / 255.0
        tensor = torch.from_numpy(np_image).permute(2, 0, 1).unsqueeze(0)
    else:
        tensor = input_image

    # Move to device
    tensor = tensor.to(device)

    # Initialize refinement model
    refinement_model = ALIASRefinement(in_channels=3, out_channels=3)
    refinement_model = refinement_model.to(device)
    refinement_model.eval()

    # Apply refinement
    with torch.no_grad():
        # Ensure input tensor has dimensions divisible by 16 to avoid size mismatches in U-Net
        original_size = tensor.shape[2:]
        # Round to nearest multiple of 16 for both dimensions
        new_h = ((original_size[0] // 16) + 1) * 16 if original_size[0] % 16 != 0 else original_size[0]
        new_w = ((original_size[1] // 16) + 1) * 16 if original_size[1] % 16 != 0 else original_size[1]

        # Pad tensor if needed to make dimensions divisible by 16
        if new_h != original_size[0] or new_w != original_size[1]:
            tensor = F.pad(tensor, (0, new_w - original_size[1], 0, new_h - original_size[0]), mode='reflect')

        refined_tensor = refinement_model(tensor)

        # Crop back to original size if padding was applied
        if new_h != original_size[0] or new_w != original_size[1]:
            refined_tensor = refined_tensor[:, :, :original_size[0], :original_size[1]]

    # Convert back to numpy/image
    refined_np = refined_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
    refined_np = (refined_np * 255).clip(0, 255).astype(np.uint8)

    return Image.fromarray(refined_np, 'RGB')


def enhance_realism(result_image, person_image, cloth_image, device='cpu'):
    """
    Apply realism enhancement to the try-on result
    """
    # Apply U-Net refinement
    refined_image = refine_image_with_unet(result_image, device)
    
    # Additional enhancement could include:
    # - Texture enhancement
    # - Contrast adjustment
    # - Color correction
    # - Shadow addition
    
    return refined_image


if __name__ == "__main__":
    print("Refinement Module ready!")