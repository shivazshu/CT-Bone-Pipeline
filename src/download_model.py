#!/usr/bin/env python3

import os
from pathlib import Path
from monai.bundle import download
import shutil

def download_model():
    """
    Download the pre-trained MONAI whole body segmentation model from MONAI model zoo
    """
    model_dir = Path("model/wholeBody_ct_segmentation")
    model_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Download model bundle
        print("Downloading model bundle...")
        download(
            name="wholebody_ct_segmentation",
            version="0.1.0",
            bundle_dir=str(model_dir)
        )
        
        print("\nModel files downloaded successfully!")
        return True
        
    except Exception as e:
        print(f"Error downloading model: {str(e)}")
        return False

if __name__ == "__main__":
    download_model() 