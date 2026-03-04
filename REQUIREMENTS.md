# Requirements Files

## requirements.txt
**For**: Docker containers (API, Worker, Dashboard)
- Used by Dockerfile
- Used by CI/CD for testing containers
- No Airflow (containers are orchestrated BY Airflow, not running it)

## requirements-airflow.txt
**For**: Airflow scheduler/webserver environment
- Install on Airflow server
- Includes apache-airflow and providers
- Used for DAG execution environment

## Why Split?

**Problem**: Airflow 2.11.1 has dependency conflicts with Streamlit:
- `apache-airflow` requires `packaging>=23.0`
- `streamlit 1.31.0` requires `packaging<24`
- `connexion` (airflow dep) requires `packaging>=25`

**Solution**: 
- Containers don't need Airflow installed (they're triggered by it)
- Airflow server doesn't need Streamlit (it's for dev dashboard)
- This is standard practice in production deployments

## Installation

### Docker Containers
```bash
pip install -r requirements.txt
```

### Airflow Server
```bash
pip install -r requirements-airflow.txt
```

### Local Development (All features)
```bash
# Install container deps
pip install -r requirements.txt

# Separately install Airflow in a different venv if needed
python -m venv airflow-env
source airflow-env/bin/activate
pip install -r requirements-airflow.txt
```
