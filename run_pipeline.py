#!/usr/bin/env python3

import sys
import time
import logging
from pathlib import Path
from src.gdcm_anonymizer import GdcmAnonymizer
import subprocess
import signal
import os
import shutil

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('Pipeline')

def check_prerequisites(logger):
    """Check if all prerequisites are met"""
    logger.info("Checking prerequisites...")
    
    # Check directories
    required_dirs = ['data/raw', 'data/anonymized', 'data/segmented', 'config', 'logs']
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            logger.error(f"Required directory {dir_path} does not exist")
            return False
    
    # Check for DICOM files
    dicom_files = list(Path('data/raw').glob('*.dcm'))
    if not dicom_files:
        logger.error("No DICOM files found in data/raw directory")
        return False
    
    logger.info(f"Found {len(dicom_files)} DICOM files to process")
    return True

def run_anonymization(logger):
    """Run DICOM anonymization"""
    logger.info("Starting DICOM anonymization...")
    try:
        anonymizer = GdcmAnonymizer()
        
        # Start anonymization
        audit_info = anonymizer.anonymize_dicom('data/raw', 'data/anonymized')
        
        # Check if files were anonymized
        anonymized_files = list(Path('data/anonymized').glob('*.dcm'))
        if not anonymized_files:
            logger.error("No anonymized files were produced")
            return False
        
        # Validate anonymization
        is_valid = anonymizer.validate_anonymization('data/anonymized')
        logger.info(f"Anonymization validation: {is_valid}")
        
        return is_valid
    
    except Exception as e:
        logger.error(f"Error in anonymization: {str(e)}")
        return False

def run_conversion(logger):
    """Run DICOM to NIfTI conversion"""
    logger.info("Starting DICOM to NIfTI conversion...")
    try:
        cmd = [
            'python', 'src/convert_to_nifti.py'
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        if process.returncode != 0:
            logger.error(f"Conversion failed: {process.stderr}")
            return False
        
        # Check for output files
        nifti_files = list(Path('data/preprocessed').glob('*.nii.gz'))
        if not nifti_files:
            logger.error("No NIfTI output files were produced")
            return False
        
        logger.info(f"Conversion completed with {len(nifti_files)} output files")
        return True
    
    except Exception as e:
        logger.error(f"Error in conversion: {str(e)}")
        return False

def run_segmentation(logger):
    """Run bone segmentation"""
    logger.info("Starting bone segmentation...")
    try:
        # Check for preprocessed files
        if not list(Path('data/preprocessed').glob('*.nii.gz')):
            logger.error("No preprocessed files found to segment")
            return False
        
        cmd = [
            'python', 'src/segment_bones.py'
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        if process.returncode != 0:
            logger.error(f"Segmentation failed: {process.stderr}")
            return False
        
        # Check for output files
        segmented_files = list(Path('data/bone_segmentation').glob('*.nii.gz'))
        if not segmented_files:
            logger.error("No segmentation output files were produced")
            return False
        
        logger.info(f"Segmentation completed with {len(segmented_files)} output files")
        return True
    
    except Exception as e:
        logger.error(f"Error in segmentation: {str(e)}")
        return False

def run_visualization(logger):
    """Run visualization of segmentation results"""
    logger.info("Creating visualizations...")
    try:
        cmd = [
            'python', 'src/visualize_results.py'
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        if process.returncode != 0:
            logger.error(f"Visualization failed: {process.stderr}")
            return False
        
        # Check for output files
        vis_dir = Path('data/bone_segmentation/visualizations')
        if not vis_dir.exists() or not list(vis_dir.glob('*.png')):
            logger.error("No visualization files were produced")
            return False
        
        logger.info(f"Visualizations created successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error in visualization: {str(e)}")
        return False

def cleanup(logger):
    """Clean up temporary files"""
    logger.info("Cleaning up...")
    try:
        temp_dir = Path('temp_processing')
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        return True
    except Exception as e:
        logger.error(f"Error in cleanup: {str(e)}")
        return False

def main():
    logger = setup_logging()
    logger.info("Starting pipeline...")
    
    try:
        # Register signal handlers
        def signal_handler(signum, frame):
            logger.info("Received interrupt signal. Cleaning up...")
            cleanup(logger)
            sys.exit(1)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Check prerequisites
        if not check_prerequisites(logger):
            logger.error("Prerequisites check failed")
            sys.exit(1)
        
        # Run anonymization
        if not run_anonymization(logger):
            logger.error("Anonymization failed")
            cleanup(logger)
            sys.exit(1)
        
        # Run conversion
        if not run_conversion(logger):
            logger.error("Conversion failed")
            cleanup(logger)
            sys.exit(1)
        
        # Run segmentation
        if not run_segmentation(logger):
            logger.error("Segmentation failed")
            cleanup(logger)
            sys.exit(1)
        
        # Create visualizations
        if not run_visualization(logger):
            logger.error("Visualization failed")
            cleanup(logger)
            sys.exit(1)
        
        logger.info("Pipeline completed successfully!")
        cleanup(logger)
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        cleanup(logger)
        sys.exit(1)

if __name__ == "__main__":
    main() 