import os
import numpy as np
from pathlib import Path
import SimpleITK as sitk
import nibabel as nib
from tqdm import tqdm
import json
import requests

model_url = 'https://github.com/Project-MONAI/MONAI-extra-test-data/releases/download/0.8.1/wholeBody_ct_segmentation_v0.1.9.zip'  # MONAI Zoo whole body CT segmentation model URL
save_path = 'model/'  # Define the save path for the model directory

def download_model(model_url, save_path):
    response = requests.get(model_url)
    with open(save_path, 'wb') as f:
        f.write(response.content)

def segment_bones(input_file: str, output_file: str, metrics_file: str):
    """
    Segment bones using CT intensity thresholding
    """
    try:
        print(f"Processing {input_file}")
        
        # Load NIfTI file
        nifti_img = nib.load(input_file)
        image_data = nifti_img.get_fdata()
        
        # Get spacing information
        spacing = nifti_img.header.get_zooms()
        
        # Threshold for bone (HU values)
        bone_min = 250  # HU
        bone_max = 1800  # HU
        
        # Create bone mask
        bone_mask = np.logical_and(image_data >= bone_min, image_data <= bone_max)
        bone_mask = bone_mask.astype(np.uint8)
        
        # Calculate metrics
        metrics = calculate_metrics(bone_mask, image_data, spacing)
        
        # Save bone mask
        bone_mask_img = nib.Nifti1Image(bone_mask, nifti_img.affine, nifti_img.header)
        nib.save(bone_mask_img, output_file)
        
        # Save metrics
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=4)
        
        print(f"Saved segmentation to {output_file}")
        print(f"Saved metrics to {metrics_file}")
        print(f"Metrics: {metrics}")
        
        return True
        
    except Exception as e:
        print(f"Error in bone segmentation: {str(e)}")
        return False

def calculate_metrics(bone_mask, image_data, spacing):
    """Calculate bone-specific metrics"""
    try:
        # Calculate voxel volume in mm³
        voxel_volume = np.prod(spacing)
        
        # Calculate bone volume
        bone_voxels = np.sum(bone_mask)
        bone_volume = bone_voxels * voxel_volume
        
        # Calculate bone density statistics
        bone_values = image_data[bone_mask > 0]
        density_stats = {
            'mean': float(np.mean(bone_values)),
            'min': float(np.min(bone_values)),
            'max': float(np.max(bone_values))
        }
        
        # Calculate surface area using gradient
        gradient = np.gradient(bone_mask)
        surface_voxels = np.sqrt(gradient[0]**2 + gradient[1]**2 + gradient[2]**2) > 0
        surface_area = np.sum(surface_voxels) * (voxel_volume**(2/3))
        
        metrics = {
            'bone_volume_mm3': float(bone_volume),
            'bone_surface_area_mm2': float(surface_area),
            'bone_density_hu': density_stats
        }
        
        return metrics
        
    except Exception as e:
        print(f"Error calculating metrics: {str(e)}")
        return {
            'bone_volume_mm3': 0.0,
            'bone_surface_area_mm2': 0.0,
            'bone_density_hu': {
                'mean': 0.0,
                'min': 0.0,
                'max': 0.0
            }
        }

def main():
    print("Starting bone segmentation using CT intensity thresholding...")
    
    try:
        # Prepare directories
        input_dir = Path("data/preprocessed")
        output_dir = Path("data/bone_segmentation")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory {input_dir} does not exist")
        
        # Process each NIfTI file
        input_files = list(input_dir.glob("*.nii.gz"))
        if not input_files:
            raise FileNotFoundError(f"No .nii.gz files found in {input_dir}")
        
        print(f"Found {len(input_files)} files to process")
        
        for input_file in input_files:
            try:
                output_file = output_dir / f"{input_file.stem}_bone_seg.nii.gz"
                metrics_file = output_dir / f"{input_file.stem}_metrics.json"
                
                if not segment_bones(str(input_file), str(output_file), str(metrics_file)):
                    print(f"Failed to process {input_file}")
                    continue
                
            except Exception as e:
                print(f"Error processing {input_file}: {str(e)}")
                continue
        
        print("\nSegmentation completed successfully!")
        
    except Exception as e:
        print(f"Error in main process: {str(e)}")
        raise

if __name__ == "__main__":
    main()

# Example usage
download_model(model_url, save_path)