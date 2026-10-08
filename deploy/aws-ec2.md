# AWS EC2 deployment

This is a research prototype deployment pattern with separate containers for:
- React frontend
- FastAPI backend
- PostgreSQL database

## 1. Create an EC2 instance

Use Ubuntu 24.04 LTS. Attach an EBS volume large enough for the database and model artifacts.

Security group:
- 22/TCP from your admin IP only
- 80/TCP from the internet if using HTTP
- 443/TCP from the internet if using HTTPS
- Do NOT expose PostgreSQL 5432 publicly.

For a demonstration, port 3000 can be exposed, but production should put Nginx/ALB in front of the application and use HTTPS.

## 2. Install Docker

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
newgrp docker
```

## 3. Copy project

```bash
git clone YOUR_PRIVATE_REPOSITORY_URL
cd AI_Alzheimer_Prioritization_Project
```

Copy your trained `artifacts/stage1_model.joblib` and metadata files to the server.

Never commit ADNI subject-level data to a public repository.

## 4. Configure secret

Create `.env`:

```env
POSTGRES_PASSWORD=use-a-long-random-secret
MODEL_STAGE=stage1
```

## 5. Start

```bash
docker compose up -d --build
docker compose ps
```

## 6. Verify

```bash
curl http://SERVER_PUBLIC_IP:8000/health
```

Open the frontend:
`http://SERVER_PUBLIC_IP:3000`

## Production hardening

For institutional use:
- HTTPS/TLS
- private database networking
- AWS Secrets Manager or equivalent
- IAM least privilege
- CloudWatch logs/metrics
- encrypted EBS and database backups
- audit logging
- no PHI in frontend logs
- authentication/authorization
- vulnerability scanning
- model versioning
- dataset/version provenance
- clinical validation and governance

Do not describe an EC2 demo as a clinically validated deployment.
