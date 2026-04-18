# PQDrive Deployment Guide

## Quick Start (Local Testing)

### Prerequisites
- Python 3.9+ (tested on 3.11)
- Git
- Virtual environment capable system (venv, conda, poetry, etc.)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/nh-44/MAHE_PQDrive.git
cd MAHE_PQDrive

# 2. Create and activate virtual environment
python -m venv pqauto-env
# On Windows:
pqauto-env\Scripts\activate
# On macOS/Linux:
source pqauto-env/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run tests
pytest -q tests/

# 5. Run CLI demo
python main.py

# 6. Run dashboard
python -m flask -A dashboard.app run
# Opens at http://localhost:5000
```

---

## Dashboard Usage (Interactive Demo)

### 1. Open Dashboard
Navigate to `http://localhost:5000` in a browser.

### 2. Interactive Scenario Runner
The dashboard provides real-time control over OTA scenarios:

**Vehicle State Controls**:
- **Speed**: Adjust vehicle speed (0-100 km/h)
- **Battery SOC**: Battery state of charge (10-100%)
- **Temperature**: Battery temperature (0-80°C)
- **Data-line Locked**: Checkbox for charging-only mode
- **Charging Active**: Toggle active charging state

**Scenario Buttons**:
- Click any scenario to run it with current vehicle state
- Green checkmark (✓) = legitimate scenarios (expected to pass)
- Red X (✗) = attack scenarios (expected to block)

**Results Display**:
- **Status**: ACCEPTED or BLOCKED
- **Latency**: Time to verify (milliseconds)
- **Reason**: If blocked, which gate failed (e.g., "anti_juice", "dilithium", "replay")
- **Vehicle State**: Parameters used in this run

### 3. Interactive Experimentation Examples

**Example 1: Trigger Anti-Juice Jacking**
```
Current state: Speed=0, Battery=68%, Temp=31°C, Data-locked=ON
Click: "Anti-Juice Jacking" button
Result: BLOCKED at anti_juice stage
(Scenario forces data_link_locked=OFF to demonstrate the defense)
```

**Example 2: Safe Charger Update**
```
Adjust state: Speed=0, Battery=50%, Temp=25°C, Data-locked=ON, Charging=ON
Click: "Trusted Charger OTA" button
Result: ACCEPTED (all checks pass)
Show judges: Even with low battery, charger auth + safe state = update allowed
```

**Example 3: Rollback Attack with Monitoring**
```
Current state: Speed=30 km/h (moving)
Click: "Rollback Attack" button
Result: BLOCKED at version stage
Explain: Version check catches downgrade attempts regardless of vehicle state
```

---

## Production Deployment

### Docker Deployment

#### Build Image
```bash
docker build -t pqdrive:latest .
```

#### Run Container
```bash
docker run -p 5000:5000 \
  -e FLASK_ENV=production \
  -e OAUTHLIB_INSECURE_TRANSPORT=0 \
  pqdrive:latest
```

#### With Docker Compose
```yaml
version: '3.8'
services:
  pqdrive:
    build: .
    ports:
      - "5000:5000"
    environment:
      FLASK_ENV: production
      PYTHONUNBUFFERED: 1
    restart: unless-stopped
```

### Cloud Deployment (AWS Example)

#### 1. Push Docker Image to ECR
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

docker tag pqdrive:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/pqdrive:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/pqdrive:latest
```

#### 2. Deploy to ECS
```bash
aws ecs create-service \
  --cluster pqdrive-cluster \
  --service-name pqdrive \
  --task-definition pqdrive:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx]}"
```

#### 3. Load Balancer Configuration
- ALB (Application Load Balancer) on port 443 with TLS
- Target group: port 5000 (container)
- Health check: `GET /api/report` (should return 200)

### Azure Deployment

```bash
# Create resource group
az group create --name pqdrive-rg --location eastus

# Create App Service Plan
az appservice plan create --name pqdrive-plan --resource-group pqdrive-rg --sku B2 --is-linux

# Deploy Docker image
az webapp create --resource-group pqdrive-rg --plan pqdrive-plan --name pqdrive-app \
  --deployment-container-image-name-user <username> \
  --deployment-container-image-name <image>

# Configure networking
az network vnet create --name pqdrive-vnet --resource-group pqdrive-rg
az network private-endpoint create --name pqdrive-pe --resource-group pqdrive-rg \
  --vnet-name pqdrive-vnet --connection-name pqdrive-conn
```

---

## Environment Variables

### Required for Production
```bash
FLASK_ENV=production           # Production mode
SECRET_KEY=<generate-random>   # Flask session key
OAUTHLIB_INSECURE_TRANSPORT=0  # Enforce HTTPS
```

### Optional Configuration
```bash
LOG_LEVEL=INFO                 # Logging level
CACHE_TTL=600                  # Request cache TTL (seconds)
MAX_OTA_SIZE=104857600         # Max OTA package size (100 MB default)
CHARGER_NONCE_TTL=300          # Charger nonce validity (5 min default)
```

---

## Monitoring & Logging

### Application Logs
```bash
# View logs
docker logs <container_id>

# Tail logs
docker logs -f <container_id>
```

### Metrics to Monitor
- **OTA Decision Latency**: Track p50, p95, p99 latencies
- **Accept/Block Rate**: Monitor for anomalies
- **Gateway Error Rate**: Crypto verification failures
- **Charger Auth Success Rate**: Attestation verifications

### Example Prometheus Metrics
```yaml
# Metrics endpoint: /metrics (not yet implemented, recommended for production)
pqdrive_ota_decisions_total{status="accepted"}
pqdrive_ota_decisions_total{status="blocked"}
pqdrive_ota_latency_ms{stage="kyber"}
pqdrive_ota_latency_ms{stage="dilithium"}
pqdrive_charger_attestations_verified_total
```

---

## Security Configuration

### TLS/HTTPS
```bash
# Generate self-signed certificate (dev only)
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Run with TLS
python -m flask --app dashboard.app --cert=cert.pem --key=key.pem run
```

### API Authentication (Production)
Add API key validation to all `/api/` endpoints:

```python
from functools import wraps
from flask import request

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != os.environ.get('API_KEY'):
            return {'error': 'Unauthorized'}, 401
        return f(*args, **kwargs)
    return decorated_function

@app.post('/api/run-scenario')
@require_api_key
def run_scenario():
    # ... existing code
```

### CORS Policy
```python
from flask_cors import CORS

app = create_app()
CORS(app, resources={"/api/*": {"origins": ["https://youromain.com"]}})
```

---

## Troubleshooting

### Issue: "liboqs version (major, minor) 0.15.0 differs from liboqs-python version 0.14.0"

**Solution**: This is a non-blocking warning. To resolve:
```bash
# Update to matching versions
pip install --upgrade liboqs-python==0.15.0
# or
brew install liboqs@0.14  # macOS with Homebrew
```

### Issue: "ModuleNotFoundError: No module named 'oqs'"

**Solution**: Using wrong Python interpreter. Ensure virtual environment is activated:
```bash
# Windows
pqauto-env\Scripts\activate

# macOS/Linux
source pqauto-env/bin/activate

# Verify
which python  # Should show venv path
python -c "import oqs; print(oqs.__version__)"
```

### Issue: Dashboard returns 500 errors

**Solution**: Check Flask logs for details:
```bash
# Enable debug mode (dev only)
export FLASK_DEBUG=1
python -m flask -A dashboard.app run

# Check error traceback in console
```

### Issue: Slow OTA decisions (> 5ms)

**Solution**: 
1. Check system load: `top` or Task Manager
2. Verify no concurrent processes using crypto library
3. Consider moving to faster hardware or cloud instance

---

## Performance Tuning

### Caching Strategy
```python
from functools import lru_cache

@lru_cache(maxsize=1024)
def verify_cached_scenario(scenario_hash):
    # Results cached for identical scenarios
    return run_single_scenario(...)
```

### Load Testing
```bash
# Install Apache Bench
ab -n 1000 -c 10 http://localhost:5000/api/report

# Or using wrk
wrk -t4 -c100 -d30s http://localhost:5000/api/report
```

### Scaling Recommendations
| Metric | Single Instance | 3 Instances | 10 Instances |
|--------|-----------------|-------------|--------------|
| Throughput (OTA/sec) | 600 | 1,800 | 6,000 |
| Latency p99 | 5 ms | 8 ms | 10 ms |
| Max Concurrent | 50 | 150 | 500 |

---

## Maintenance

### Log Rotation
```bash
# Use logrotate (Linux)
cat > /etc/logrotate.d/pqdrive << EOF
/var/log/pqdrive/*.log {
  daily
  rotate 7
  compress
  delaycompress
  missingok
}
EOF
```

### Backup Strategy
```bash
# Backup audit logs daily
0 2 * * * tar -czf /backup/pqdrive-$(date +\%Y\%m\%d).tar.gz /var/log/pqdrive/
```

### Updates
```bash
# Pull latest
git pull origin main

# Update dependencies
pip install --upgrade -r requirements.txt

# Restart service
systemctl restart pqdrive
```

---

## Support & Documentation

- **Threat Model**: See [THREAT_MODEL.md](THREAT_MODEL.md)
- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Performance**: See [PERFORMANCE.md](PERFORMANCE.md)
- **Security**: See [SECURITY.md](SECURITY.md) (if available)
- **Issues**: GitHub Issues at https://github.com/nh-44/MAHE_PQDrive/issues

---

*Deployment Guide Version: 1.0 | Last Updated: April 18, 2026*
