# Task: Hybrid Cloud Architecture

## Overview
Phát triển project theo hướng Hybrid Cloud để:
- Chạy được cả local và cloud (AWS/GCP/Azure)
- Học các kỹ năng Cloud Engineer
- Production-ready deployment

---

## Checklist

### Phase 1: Containerization (Docker)
- [ ] Tạo `Dockerfile` cho Backend (FastAPI + Worker)
- [ ] Tạo `Dockerfile` cho Frontend (React build)
- [ ] Tạo `docker-compose.yml` cho local development
- [ ] Test container build và chạy local

### Phase 2: Cloud Abstraction Layer
- [ ] Abstract storage layer (AWS S3 ↔ MinIO/Local)
- [ ] Abstract queue layer (AWS SQS ↔ Redis/RabbitMQ)
- [ ] Abstract database layer (DynamoDB ↔ Redis/PostgreSQL)
- [ ] Environment-based configuration

### Phase 3: Kubernetes (K8s)
- [ ] Tạo K8s manifests (Deployment, Service, ConfigMap)
- [ ] Tạo Helm chart cho dễ deploy
- [ ] Add Ingress configuration
- [ ] Add HorizontalPodAutoscaler

### Phase 4: Infrastructure as Code (IaC)
- [ ] Terraform cho AWS resources
- [ ] Terraform cho local (optional)
- [ ] CI/CD pipeline với GitHub Actions

### Phase 5: Observability
- [ ] Add health check endpoints
- [ ] Add Prometheus metrics
- [ ] Add structured logging (JSON)
