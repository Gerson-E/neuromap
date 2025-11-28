# NeuroChron - Brain Age Analysis Platform

A complete end-to-end system for predicting biological brain age from T1-weighted MRI scans using deep learning.

## Overview

NeuroChron analyzes MRI brain scans to predict biological brain age and calculate the "brain age gap" - the difference between your brain's biological age and your chronological age. The system uses FreeSurfer for preprocessing and a 3D CNN model for age prediction.

## Features

- **Full Pipeline**: Automated DICOM upload → FreeSurfer preprocessing → Brain age prediction → Results delivery
- **Web Interface**: User-friendly Shiny frontend for uploading scans and viewing results
- **REST API**: FastAPI backend with comprehensive documentation
- **Docker Integration**: FreeSurfer runs in Docker for consistent preprocessing
- **Saliency Maps**: Visual explanations showing which brain regions influenced the prediction
- **Email Notifications**: Optional SendGrid integration for result delivery
- **Real-time Monitoring**: Track job status and progress through the pipeline

## Tech Stack

- **Frontend**: Python Shiny
- **Backend**: FastAPI (Python)
- **Preprocessing**: FreeSurfer 7.4.1 (Docker)
- **Model**: TensorFlow 3D CNN
- **Database**: SQLite
- **Email**: SendGrid (optional)

## Quick Start

See **[QUICKSTART.md](QUICKSTART.md)** for a 5-minute setup guide.

For detailed documentation, see **[TEAMMATE_SETUP.md](TEAMMATE_SETUP.md)**.

### Minimal Setup

```bash
# 1. Install dependencies
pip install -r neuromap/requirements.txt
pip install -r neuromap/backend/api/requirements.txt

# 2. Set up environment (email is optional)
cp .env.example .env

# 3. Get FreeSurfer license (free)
# Register at: https://surfer.nmr.mgh.harvard.edu/registration.html
# Save to: neuromap/backend/license/license.txt

# 4. Start backend API
cd neuromap/backend/api
python3 -m uvicorn app:app --reload

# 5. Start frontend (in new terminal)
cd neuromap
shiny run app.py --port 8080

# 6. Open http://localhost:8080
```

## Usage

### Web Interface
1. Navigate to http://localhost:8080
2. Enter patient age (must be > 21) and email
3. Upload DICOM MRI file
4. Monitor processing status
5. View results (~3.5 hours for full pipeline)

### API
```bash
# Upload scan
curl -X POST http://localhost:8000/api/upload \
  -F "file=@scan.dcm" \
  -F "chronological_age=45" \
  -F "email=user@example.com"

# Check status
curl http://localhost:8000/api/jobs/{job_id}/status

# Get results
curl http://localhost:8000/api/jobs/{job_id}/results

# View saliency map
curl http://localhost:8000/api/jobs/{job_id}/saliency
```

API documentation: http://localhost:8000/docs

### Quick Test (No Docker)
```bash
cd neuromap
python3 test_quick.py
```

Uses pre-processed data to test prediction in ~5 seconds.

## Architecture

```
┌─────────────────┐
│  Web Browser    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Shiny Frontend  │  (Port 8080)
│   (app.py)      │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  FastAPI API    │  (Port 8000)
│   (app.py)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Background      │
│   Worker        │
└────────┬────────┘
         │
    ┌────┴────┬────────────┬──────────┐
    ▼         ▼            ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ DICOM  │ │FreeSur-│ │Brain   │ │ Email  │
│ Convert│ │fer     │ │Age CNN │ │SendGrid│
└────────┘ └────────┘ └────────┘ └────────┘
              Docker     TensorFlow
```

## Project Structure

```
neuromap/
├── README.md                    # This file
├── QUICKSTART.md               # Quick setup guide
├── TEAMMATE_SETUP.md           # Detailed documentation
├── app.py                      # Shiny frontend
├── test_quick.py               # Quick test script
├── test_full_pipeline.py       # Full pipeline test
├── .env.example                # Environment template
└── neuromap/
    ├── api_client.py           # API client for frontend
    ├── config.py               # Configuration
    ├── requirements.txt        # Python dependencies
    ├── tasks/
    │   └── notify.py          # Email notifications
    ├── notifications/
    │   └── send.py            # SendGrid integration
    └── backend/
        ├── docker-compose.yml  # Docker setup
        ├── license/
        │   └── license.txt    # FreeSurfer license (you provide)
        └── api/
            ├── app.py         # FastAPI application
            ├── worker.py      # Pipeline orchestrator
            ├── database.py    # SQLite models
            ├── models.py      # API schemas
            ├── freesurfer_runner.py
            ├── brain_age_predictor.py
            ├── file_processor.py
            └── data/
                └── model/     # 3D CNN weights
```

## Requirements

- **Python**: 3.11+
- **Docker Desktop**: For FreeSurfer preprocessing
- **FreeSurfer License**: Free registration required
- **Memory**: 4-6GB RAM for FreeSurfer
- **Disk**: ~10GB for Docker image + processing space

## Model Information

- **Architecture**: 3D Convolutional Neural Network
- **Input**: T1-weighted MRI (preprocessed by FreeSurfer)
- **Output**: Predicted brain age in years
- **Valid Age Range**: > 21 years
- **Processing Time**: ~3.5 hours (FreeSurfer) + 5-10 seconds (prediction)

## Data Privacy

- All processing happens locally on your machine
- No data is sent to external servers (except SendGrid for optional emails)
- Patient data stored in local SQLite database
- DICOM files and results stored locally

## Troubleshooting

**Port already in use:**
```bash
lsof -ti:8000 | xargs kill -9
```

**Docker not running:**
```bash
open -a Docker
```

**Email errors:**
Email is optional. Set dummy values in `.env` if you don't have SendGrid:
```env
SENDGRID_API_KEY=dummy_key_for_development
```

See [TEAMMATE_SETUP.md](TEAMMATE_SETUP.md) for more troubleshooting.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Citation

If you use this software in your research, please cite:

```bibtex
@software{neurochron2025,
  title={NeuroChron: Brain Age Analysis Platform},
  year={2025},
  url={https://github.com/yourusername/neuromap}
}
```

## Acknowledgments

- FreeSurfer: https://surfer.nmr.mgh.harvard.edu/
- Brain age model based on 3D CNN architecture
- Built with FastAPI and Shiny for Python

## Support

- **Documentation**: See TEAMMATE_SETUP.md
- **API Docs**: http://localhost:8000/docs
- **Issues**: Open an issue on GitHub
- **Health Check**: http://localhost:8000/health
