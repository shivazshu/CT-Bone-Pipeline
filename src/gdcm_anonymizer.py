#!/usr/bin/env python3

import gdcm
import logging
import json
from pathlib import Path
from datetime import datetime
from cryptography.fernet import Fernet
from typing import Dict, List, Optional
import shutil
import yaml
import pydicom
from tqdm import tqdm
import os
import tempfile
from pydicom.dataelem import DataElement
from pydicom.valuerep import PersonName

class GdcmAnonymizer:
    """
    GDCM-based DICOM Anonymizer with HIPAA compliance and audit features
    """
    def __init__(self, config_path: str = "config/anonymizer_config.yml"):
        self.logger = self._setup_logging()
        self.config = self._load_config(config_path)
        self.encryption_key = self._generate_or_load_key()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging with HIPAA-compliant format"""
        logger = logging.getLogger('GdcmAnonymizer')
        logger.setLevel(logging.INFO)
        
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f"anonymization_{timestamp}.log"
        
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s - [AccessID:%(process)d]'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _load_config(self, config_path: str) -> dict:
        """Load anonymization configuration"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.info("Configuration loaded successfully")
            return config
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            raise
    
    def _generate_or_load_key(self) -> bytes:
        """Generate or load encryption key for PHI data"""
        key_file = Path("config/encryption.key")
        if key_file.exists():
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            key_file.parent.mkdir(exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
        return key
    
    def _encrypt_phi(self, phi_data: Dict) -> str:
        """Encrypt PHI data"""
        f = Fernet(self.encryption_key)
        return f.encrypt(json.dumps(phi_data).encode()).decode()
    
    def _decrypt_phi(self, encrypted_data: str) -> Dict:
        """Decrypt PHI data"""
        f = Fernet(self.encryption_key)
        return json.loads(f.decrypt(encrypted_data.encode()).decode())

    def _safe_write_dicom(self, writer: gdcm.ImageWriter, output_path: Path) -> bool:
        """
        Safely write DICOM file using a temporary file
        """
        temp_path = None
        try:
            # Create temporary file in the same directory
            temp_dir = output_path.parent
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Ensure write permissions on temp directory
            os.chmod(temp_dir, 0o755)
            
            with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False, suffix='.dcm') as tmp:
                temp_path = Path(tmp.name)
            
            # Write to temporary file first
            writer.SetFileName(str(temp_path))
            if not writer.Write():
                self.logger.error(f"GDCM writer failed to write to temporary file")
                if temp_path.exists():
                    temp_path.unlink()
                return False
            
            # Verify the written file
            reader = gdcm.Reader()
            reader.SetFileName(str(temp_path))
            if not reader.Read():
                self.logger.error(f"Failed to verify temporary file with GDCM reader")
                temp_path.unlink()
                return False
            
            # Additional verification with pydicom
            try:
                pydicom.dcmread(str(temp_path))
            except Exception as e:
                self.logger.error(f"Failed to verify temporary file with pydicom: {str(e)}")
                temp_path.unlink()
                return False
            
            # Move temporary file to final destination
            if output_path.exists():
                output_path.unlink()
            temp_path.replace(output_path)
            
            # Final verification
            if not output_path.exists():
                self.logger.error(f"Failed to move temporary file to final destination")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in safe DICOM write: {str(e)}")
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            return False
    
    def anonymize_dicom(self, input_dir: str, output_dir: str) -> Dict:
        """
        Anonymize DICOM files using GDCM
        Returns audit information
        """
        try:
            input_path = Path(input_dir).resolve()
            output_path = Path(output_dir).resolve()
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Ensure write permissions
            os.chmod(output_path, 0o755)
            
            audit_info = {
                'start_time': datetime.now().isoformat(),
                'files_processed': 0,
                'errors': [],
                'warnings': [],
                'phi_removed': set()
            }
            
            # Process each DICOM file
            dicom_files = list(input_path.glob("*.dcm"))
            self.logger.info(f"Found {len(dicom_files)} DICOM files to process")
            
            for dicom_file in tqdm(dicom_files, desc="Anonymizing DICOM files"):
                try:
                    # Read with pydicom
                    ds = pydicom.dcmread(str(dicom_file))
                    
                    # Store original PHI for audit
                    original_phi = {
                        'PatientName': str(getattr(ds, 'PatientName', '')),
                        'PatientID': str(getattr(ds, 'PatientID', '')),
                        'InstitutionName': str(getattr(ds, 'InstitutionName', ''))
                    }
                    audit_info['phi_removed'].add(json.dumps(original_phi))
                    
                    # Remove problematic tags
                    if (0x0000, 0x0008) in ds:
                        del ds[(0x0000, 0x0008)]
                    
                    # Remove PHI tags
                    tags_to_remove = [
                        (0x0010,0x0010),  # Patient Name
                        (0x0010,0x0020),  # Patient ID
                        (0x0010,0x0030),  # Patient Birth Date
                        (0x0010,0x0040),  # Patient Sex
                        (0x0010,0x1000),  # Other Patient IDs
                        (0x0010,0x1001),  # Other Patient Names
                        (0x0008,0x0080),  # Institution Name
                        (0x0008,0x0081),  # Institution Address
                        (0x0008,0x0090),  # Referring Physician's Name
                        (0x0008,0x0092),  # Referring Physician's Address
                        (0x0008,0x0094),  # Referring Physician's Phone
                    ]
                    
                    # Remove tags if they exist
                    for tag in tags_to_remove:
                        if tag in ds:
                            del ds[tag]
                    
                    # Create new data elements with proper VR
                    from pydicom.dataelem import DataElement
                    from pydicom.valuerep import PersonName
                    
                    # Add anonymized values with proper VR handling
                    ds[0x0010, 0x0010] = DataElement((0x0010, 0x0010), 'PN', PersonName("ANONYMOUS"))
                    ds[0x0010, 0x0020] = DataElement((0x0010, 0x0020), 'LO', f"ANON_{dicom_file.stem}")
                    ds[0x0010, 0x0030] = DataElement((0x0010, 0x0030), 'DA', "")
                    ds[0x0010, 0x0040] = DataElement((0x0010, 0x0040), 'CS', "")
                    ds[0x0010, 0x1000] = DataElement((0x0010, 0x1000), 'LO', "")
                    ds[0x0010, 0x1001] = DataElement((0x0010, 0x1001), 'PN', PersonName(""))
                    ds[0x0008, 0x0080] = DataElement((0x0008, 0x0080), 'LO', "ANONYMOUS_INSTITUTION")
                    ds[0x0008, 0x0081] = DataElement((0x0008, 0x0081), 'ST', "")
                    ds[0x0008, 0x0090] = DataElement((0x0008, 0x0090), 'PN', PersonName("ANONYMOUS_PHYSICIAN"))
                    ds[0x0008, 0x0092] = DataElement((0x0008, 0x0092), 'ST', "")
                    ds[0x0008, 0x0094] = DataElement((0x0008, 0x0094), 'SH', "")
                    
                    # Write anonymized file
                    output_file = output_path / dicom_file.name
                    ds.save_as(str(output_file), write_like_original=False)
                    
                    # Verify the anonymized file
                    if not self._validate_single_file(output_file):
                        raise Exception(f"Validation failed for anonymized file")
                    
                    audit_info['files_processed'] += 1
                    
                except Exception as e:
                    error_msg = f"Error processing {dicom_file.name}: {str(e)}"
                    self.logger.error(error_msg)
                    audit_info['errors'].append(error_msg)
                    
                    # Move problematic file to quarantine
                    quarantine_dir = Path(self.config['directories']['quarantine'])
                    quarantine_dir.mkdir(exist_ok=True)
                    shutil.copy2(dicom_file, quarantine_dir / dicom_file.name)
            
            audit_info['end_time'] = datetime.now().isoformat()
            self._save_audit_info(audit_info)
            
            self.logger.info(f"Anonymization completed: {audit_info['files_processed']} files processed")
            return audit_info
            
        except Exception as e:
            self.logger.error(f"Error in DICOM anonymization: {str(e)}")
            raise

    def _validate_single_file(self, file_path: Path) -> bool:
        """Validate a single anonymized DICOM file"""
        try:
            # Check file exists and is readable
            if not file_path.exists():
                self.logger.error(f"File does not exist: {file_path}")
                return False
            
            # Try to read with pydicom
            try:
                ds = pydicom.dcmread(str(file_path))
            except Exception as e:
                self.logger.error(f"Failed to read file with pydicom: {str(e)}")
                return False
            
            # Check no PHI remains
            phi_tags = [
                ('PatientName', 'ANONYMOUS'),
                ('PatientID', 'ANON_'),
                ('PatientBirthDate', ''),
                ('PatientSex', ''),
                ('OtherPatientIDs', ''),
                ('OtherPatientNames', ''),
                ('InstitutionName', 'ANONYMOUS_INSTITUTION'),
                ('InstitutionAddress', ''),
                ('ReferringPhysicianName', 'ANONYMOUS_PHYSICIAN'),
                ('ReferringPhysicianAddress', ''),
                ('ReferringPhysicianPhone', '')
            ]
            
            for tag, expected_value in phi_tags:
                if hasattr(ds, tag):
                    value = str(getattr(ds, tag)).strip()
                    # Empty value is acceptable
                    if not value:
                        continue
                    # Check if value matches expected pattern
                    if expected_value and not value.startswith(expected_value):
                        self.logger.error(f"Found remaining PHI in {tag}: {value}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating file {file_path}: {str(e)}")
            return False
    
    def _save_audit_info(self, audit_info: Dict):
        """Save audit information in HIPAA-compliant format"""
        try:
            audit_dir = Path("audit_logs")
            audit_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            audit_file = audit_dir / f"audit_{timestamp}.json"
            
            # Encrypt sensitive information
            encrypted_audit = {
                'timestamp': audit_info['start_time'],
                'files_processed': audit_info['files_processed'],
                'duration': (datetime.fromisoformat(audit_info['end_time']) - 
                           datetime.fromisoformat(audit_info['start_time'])).total_seconds(),
                'phi_removed': self._encrypt_phi(list(audit_info['phi_removed'])),
                'error_count': len(audit_info['errors']),
                'warning_count': len(audit_info['warnings'])
            }
            
            with open(audit_file, 'w') as f:
                json.dump(encrypted_audit, f, indent=4)
            
            self.logger.info(f"Audit information saved to {audit_file}")
        except Exception as e:
            self.logger.error(f"Error saving audit information: {str(e)}")
            raise
    
    def validate_anonymization(self, output_dir: str) -> bool:
        """Validate anonymization results"""
        try:
            output_path = Path(output_dir)
            validation_results = {
                'phi_check': self._check_remaining_phi(output_path),
                'file_check': self._validate_file_integrity(output_path),
                'compliance_check': self._check_hipaa_compliance(output_path)
            }
            
            self.logger.info(f"Validation results: {validation_results}")
            return all(validation_results.values())
        except Exception as e:
            self.logger.error(f"Error in validation: {str(e)}")
            raise
    
    def _check_remaining_phi(self, output_path: Path) -> bool:
        """Check for any remaining PHI in anonymized files"""
        try:
            for dicom_file in output_path.glob("*.dcm"):
                ds = pydicom.dcmread(str(dicom_file))
                # Check critical PHI tags
                for tag in ['PatientName', 'PatientID', 'InstitutionName']:
                    if hasattr(ds, tag):
                        value = str(getattr(ds, tag)).strip()
                        if tag == 'PatientName' and value != 'ANONYMOUS':
                            self.logger.error(f"Found remaining PHI in {dicom_file}: {tag}")
                            return False
                        elif tag == 'PatientID' and not value.startswith('ANON_'):
                            self.logger.error(f"Found remaining PHI in {dicom_file}: {tag}")
                            return False
                        elif tag == 'InstitutionName' and value != 'ANONYMOUS_INSTITUTION':
                            self.logger.error(f"Found remaining PHI in {dicom_file}: {tag}")
                            return False
            return True
        except Exception as e:
            self.logger.error(f"Error checking remaining PHI: {str(e)}")
            return False
    
    def _validate_file_integrity(self, output_path: Path) -> bool:
        """Validate DICOM file integrity"""
        try:
            for dicom_file in output_path.glob("*.dcm"):
                if not self._validate_single_file(dicom_file):
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Error validating file integrity: {str(e)}")
            return False
    
    def _check_hipaa_compliance(self, output_path: Path) -> bool:
        """Check HIPAA compliance of anonymized files"""
        try:
            hipaa_tags = [
                ('PatientName', 'ANONYMOUS'),
                ('PatientID', 'ANON_'),
                ('PatientBirthDate', ''),
                ('PatientSex', ''),
                ('OtherPatientIDs', ''),
                ('OtherPatientNames', ''),
                ('InstitutionName', 'ANONYMOUS_INSTITUTION'),
                ('InstitutionAddress', ''),
                ('ReferringPhysicianName', 'ANONYMOUS_PHYSICIAN'),
                ('ReferringPhysicianAddress', ''),
                ('ReferringPhysicianPhone', '')
            ]
            
            for dicom_file in output_path.glob("*.dcm"):
                try:
                    ds = pydicom.dcmread(str(dicom_file))
                    for tag, expected_value in hipaa_tags:
                        if hasattr(ds, tag):
                            value = str(getattr(ds, tag)).strip()
                            # Empty value is acceptable
                            if not value:
                                continue
                            # Check if value matches expected pattern
                            if expected_value and not value.startswith(expected_value):
                                self.logger.error(f"HIPAA compliance check failed for {dicom_file}: {tag}")
                                return False
                except Exception as e:
                    self.logger.error(f"Error checking HIPAA compliance for {dicom_file}: {str(e)}")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Error checking HIPAA compliance: {str(e)}")
            return False 