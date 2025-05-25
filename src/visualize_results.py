#!/usr/bin/env python3

import os
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
from pathlib import Path
import json
from skimage.util import montage
from skimage.transform import resize
from matplotlib.colors import ListedColormap

def create_view_montage(volume_data, view='axial', n_images=16):
    """Create a montage for a specific view"""
    if view == 'axial':
        slices = [volume_data[:, :, i] for i in np.linspace(0, volume_data.shape[2]-1, n_images, dtype=int)]
    elif view == 'sagittal':
        slices = [volume_data[i, :, :] for i in np.linspace(0, volume_data.shape[0]-1, n_images, dtype=int)]
    else:  # coronal
        slices = [volume_data[:, i, :] for i in np.linspace(0, volume_data.shape[1]-1, n_images, dtype=int)]
    
    # Normalize and resize slices to be square
    max_dim = max(slices[0].shape)
    normalized_slices = []
    for slice_data in slices:
        # Resize to square shape
        if slice_data.shape[0] != slice_data.shape[1]:
            resized = resize(slice_data, (max_dim, max_dim), preserve_range=True)
        else:
            resized = slice_data
        # Normalize to [0, 1]
        if resized.max() != resized.min():
            normalized = (resized - resized.min()) / (resized.max() - resized.min())
        else:
            normalized = resized
        normalized_slices.append(normalized)
    
    # Stack slices into a 3D array
    stacked_slices = np.stack(normalized_slices)
    
    # Reshape to 4D array with channel axis
    reshaped_slices = stacked_slices.reshape((-1, max_dim, max_dim, 1))
    
    # Create montage
    montage_array = montage(reshaped_slices, channel_axis=-1, padding_width=2)
    return np.squeeze(montage_array)  # Remove channel axis for display

def create_segmentation_montages(ct_data, seg_data, output_path: Path):
    """Create montages for all three views"""
    views = ['axial', 'sagittal', 'coronal']
    
    # Create yellow colormap (bright yellow with 70% opacity)
    yellow_colors = np.array([[1, 1, 0, 0], [1, 1, 0, 0.7]])
    segmentation_cmap = ListedColormap(yellow_colors)
    
    for view in views:
        # Create figure with two subplots side by side
        plt.figure(figsize=(20, 10))
        
        # Create montages
        ct_montage = create_view_montage(ct_data, view)
        seg_montage = create_view_montage(seg_data, view)
        
        # Plot CT montage
        plt.subplot(121)
        plt.imshow(ct_montage, cmap='gray')
        plt.title(f'{view.capitalize()} View - CT', fontsize=14)
        plt.axis('off')
        
        # Plot segmentation montage with yellow mask
        plt.subplot(122)
        plt.imshow(ct_montage, cmap='gray')
        # Create a mask for segmentation
        mask = seg_montage > 0
        # Apply color to segmented regions
        plt.imshow(mask, cmap=segmentation_cmap, vmin=0, vmax=1)
        plt.title(f'{view.capitalize()} View - Segmentation Mask', fontsize=14)
        plt.axis('off')
        
        plt.tight_layout()
        plt.savefig(output_path / f'{view}_montage.png', bbox_inches='tight', dpi=300)
        plt.close()

def create_visualizations(nifti_file: str, seg_file: str, metrics_file: str, output_dir: str):
    """
    Create visualizations of the bone segmentation results
    """
    # Load images
    nifti_img = nib.load(nifti_file)
    seg_img = nib.load(seg_file)
    
    # Get data
    ct_data = nifti_img.get_fdata()
    seg_data = seg_img.get_fdata()
    
    # Load metrics
    with open(metrics_file, 'r') as f:
        metrics = json.load(f)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create montages
    print("Creating montages...")
    create_segmentation_montages(ct_data, seg_data, output_path)
    
    # Save metrics as JSON with additional information
    metrics_with_info = {
        'bone_metrics': {
            k: float(v) if isinstance(v, np.floating) else v 
            for k, v in metrics.items()
        },
        'image_info': {
            'dimensions': tuple(int(x) for x in ct_data.shape),
            'spacing': tuple(float(x) for x in nifti_img.header.get_zooms()),
            'orientation': [[float(x) for x in row] for row in nifti_img.affine.tolist()]
        },
        'segmentation_info': {
            'total_voxels': int(np.prod(ct_data.shape)),
            'bone_voxels': int(np.sum(seg_data > 0)),
            'bone_percentage': float(np.sum(seg_data > 0) / np.prod(ct_data.shape) * 100)
        }
    }
    
    with open(output_path / 'detailed_metrics.json', 'w') as f:
        json.dump(metrics_with_info, f, indent=4)
    
    print(f"Visualizations and metrics saved to {output_path}")

def main():
    try:
        # Find input files
        preprocessed_dir = Path("data/preprocessed")
        segmentation_dir = Path("data/bone_segmentation")
        output_dir = segmentation_dir / "visualizations"
        
        nifti_files = list(preprocessed_dir.glob("*.nii.gz"))
        
        for nifti_file in nifti_files:
            seg_file = segmentation_dir / f"{nifti_file.stem}_bone_seg.nii.gz"
            metrics_file = segmentation_dir / f"{nifti_file.stem}_metrics.json"
            
            if not all(f.exists() for f in [nifti_file, seg_file, metrics_file]):
                print(f"Missing files for {nifti_file.name}")
                continue
            
            create_visualizations(
                str(nifti_file),
                str(seg_file),
                str(metrics_file),
                str(output_dir)
            )
    
    except Exception as e:
        print(f"Error creating visualizations: {str(e)}")
        raise

if __name__ == "__main__":
    main() 