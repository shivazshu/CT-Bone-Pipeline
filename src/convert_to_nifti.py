#!/usr/bin/env python3

import os
import pydicom
import numpy as np
import nibabel as nib
from pathlib import Path
from tqdm import tqdm
import SimpleITK as sitk

def convert_dicom_to_nifti(input_dir: str, output_dir: str):
    """
    Convert DICOM files to NIfTI format
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get all DICOM files
    dicom_files = sorted(list(input_path.glob("*.dcm")))
    if not dicom_files:
        raise FileNotFoundError(f"No DICOM files found in {input_dir}")
    
    print(f"Found {len(dicom_files)} DICOM files")
    
    # Group DICOM files by series
    series_dict = {}
    for dicom_file in tqdm(dicom_files, desc="Grouping DICOM files"):
        try:
            ds = pydicom.dcmread(str(dicom_file))
            series_id = str(ds.SeriesInstanceUID)
            if series_id not in series_dict:
                series_dict[series_id] = []
            series_dict[series_id].append(dicom_file)
        except Exception as e:
            print(f"Error reading {dicom_file}: {str(e)}")
            continue
    
    print(f"Found {len(series_dict)} unique series")
    
    # Convert each series to NIfTI
    for series_id, files in series_dict.items():
        try:
            print(f"\nProcessing series {series_id} with {len(files)} files")
            
            # Read series using SimpleITK
            reader = sitk.ImageSeriesReader()
            reader.SetFileNames([str(f) for f in files])
            image = reader.Execute()
            
            # Get original spacing and direction
            spacing = image.GetSpacing()
            direction = image.GetDirection()
            origin = image.GetOrigin()
            
            # Convert to numpy array
            array = sitk.GetArrayFromImage(image)
            
            # Create NIfTI image
            nifti_img = nib.Nifti1Image(array, np.eye(4))
            
            # Set header information
            header = nifti_img.header
            header.set_xyzt_units(xyz='mm')
            header['pixdim'][1:4] = spacing[::-1]  # Reverse order for NIfTI
            
            # Save NIfTI file
            output_file = output_path / f"series_{len(series_dict)}.nii.gz"
            nib.save(nifti_img, str(output_file))
            print(f"Saved {output_file}")
            
        except Exception as e:
            print(f"Error converting series {series_id}: {str(e)}")
            continue

def main():
    input_dir = "data/anonymized"
    output_dir = "data/preprocessed"
    
    try:
        convert_dicom_to_nifti(input_dir, output_dir)
        print("\nConversion completed successfully!")
    except Exception as e:
        print(f"Error in conversion: {str(e)}")
        raise

if __name__ == "__main__":
    main() 