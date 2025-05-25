# CT Bone Analysis Pipeline with HIPAA-Compliant Anonymization

A secure and compliant pipeline for CT bone analysis that combines HIPAA-compliant DICOM anonymization with advanced bone segmentation.

## Features

### HIPAA-Compliant DICOM Anonymization
- Secure PHI handling with Fernet encryption
- Comprehensive audit trail generation
- HIPAA-compliant logging with access tracking
- File integrity validation
- Quarantine system for failed anonymizations
- Configurable anonymization rules

### Bone Segmentation
- Automated bone structure segmentation using MONAI
- Support for multiple bone structures
- Segmentation validation and quality checks
- 3D visualization capabilities

## Project Structure
```
.
├── data/                  # Data storage
│   ├── raw/              # Raw DICOM files
│   ├── anonymized/       # Anonymized files
│   ├── segmented/        # Segmentation results
│   └── quarantine/       # Failed anonymization files
├── src/
│   ├── mirc_anonymizer.py # HIPAA-compliant anonymizer
│   └── segment_bones.py   # Bone segmentation script
├── config/               # Configuration files
│   ├── mirc_config.yml   # MIRC CTP configuration
│   └── encryption.key    # PHI encryption key
├── logs/                 # HIPAA-compliant logs
├── audit_logs/           # Anonymization audit trails
└── requirements.txt      # Project dependencies
```

## Prerequisites
- Python 3.8 or higher
- Java JDK 11 or higher (for MIRC CTP)
- Sufficient disk space for medical images

## Setup
1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### 1. DICOM Anonymization
```python
from src.mirc_anonymizer import MircAnonymizer

# Initialize anonymizer
anonymizer = MircAnonymizer()

# Setup MIRC CTP
anonymizer.setup_mirc_ctp()

# Anonymize DICOM files
audit_info = anonymizer.anonymize_dicom(
    input_dir="data/raw",
    output_dir="data/anonymized"
)

# Validate results
is_valid = anonymizer.validate_anonymization("data/anonymized")
```

### 2. Bone Segmentation
```python
python src/segment_bones.py --input data/anonymized --output data/segmented
```

## Running the Pipeline

### Initial Setup
1. Clone the repository:
```bash
git clone https://github.com/shivazshu/CT-Bone-Pipeline.git
```

2. Create and activate the virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create required directories:
```bash
mkdir -p data/{raw,anonymized,segmented,quarantine}
mkdir -p config
mkdir -p logs
mkdir -p audit_logs
```

### Running the Pipeline
1. Place your DICOM files in the `data/raw` directory

2. Create the MIRC CTP configuration file:
```bash
cat > config/mirc_config.yml << EOL
mirc:
  port: 9090
  ctp_path: "lib/CTP-installer.jar"
  config_file: "config/ctp-config.xml"
  script_file: "config/dicom-anonymizer.script"

directories:
  input: "data/raw"
  output: "data/anonymized"
  quarantine: "data/quarantine"
  logs: "logs"
EOL
```

3. Run the anonymization:
```bash
python -c "
from src.mirc_anonymizer import MircAnonymizer
anonymizer = MircAnonymizer()
anonymizer.setup_mirc_ctp()
audit_info = anonymizer.anonymize_dicom('data/raw', 'data/anonymized')
is_valid = anonymizer.validate_anonymization('data/anonymized')
print(f'Anonymization successful: {is_valid}')
"
```

4. Run the bone segmentation:
```bash
python src/segment_bones.py \
  --input data/anonymized \
  --output data/segmented \
  --model_type vertebrae \  # Options: vertebrae, ribs, pelvis, all
  --visualize true
```

### Monitoring and Validation
1. Check the logs for progress and errors:
```bash
tail -f logs/anonymization_*.log
```

2. View audit trails:
```bash
ls -l audit_logs/
```

3. Check segmentation results:
- The segmented bone models will be in `data/segmented/`
- Visualization files (if enabled) will be in `data/segmented/viz/`

### Common Issues and Solutions
1. If MIRC CTP fails to start:
   - Check Java installation: `java -version`
   - Verify port 9090 is available: `lsof -i :9090`
   - Check logs for specific errors

2. If anonymization validation fails:
   - Check quarantine directory for failed files
   - Review audit logs for specific PHI issues
   - Verify DICOM file integrity

3. If segmentation fails:
   - Verify DICOM files are properly anonymized
   - Check GPU memory if using CUDA
   - Review model compatibility with your data

## Security Features

### PHI Protection
- Encryption of all PHI data using Fernet
- Secure key management
- Access logging with unique process IDs
- Comprehensive audit trails

### Validation & Compliance
- Automated HIPAA compliance checking
- PHI removal verification
- File integrity validation
- Detailed error reporting and logging

## Audit & Logging
- HIPAA-compliant logging format
- Detailed audit trails for all operations

## Configuration
The system can be configured via `config/mirc_config.yml`. Key settings include:
- MIRC CTP server configuration
- Directory paths
- Anonymization rules
- Logging preferences

## Error Handling
- Comprehensive error catching and logging
- Quarantine system for problematic files
- Detailed error reporting
- Validation failure handling

## Contributing
Please ensure any contributions maintain HIPAA compliance and security standards. All code changes must pass security review. 