# Implementation Plan: Hybrid Cloud Architecture

## Goal
Xây dựng kiến trúc Hybrid Cloud cho phép:
- **Local Dev**: Chạy 100% offline với Docker Compose
- **AWS Cloud**: Deploy production lên AWS
- **Portable**: Dễ dàng migrate sang GCP/Azure

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     HYBRID CLOUD LAYER                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│   │  Storage    │    │   Queue     │    │  Database   │    │
│   │  Adapter    │    │   Adapter   │    │   Adapter   │    │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    │
│          │                  │                  │            │
│   ┌──────┴──────┐    ┌──────┴──────┐    ┌──────┴──────┐    │
│   │ AWS S3     │    │ AWS SQS    │    │ DynamoDB   │    │
│   │ MinIO      │    │ Redis      │    │ Redis      │    │
│   │ LocalFS    │    │ RabbitMQ   │    │ PostgreSQL │    │
│   └─────────────┘    └─────────────┘    └─────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Docker Containerization

### [NEW] Dockerfile.backend
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
EXPOSE 5000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5000"]
```

### [NEW] Dockerfile.frontend
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
EXPOSE 80
```

### [NEW] docker-compose.yml
```yaml
services:
  # Local alternatives to AWS
  minio:        # S3-compatible storage
  redis:        # Queue + Cache
  
  # Application
  api:          # FastAPI server
  worker:       # Background processor
  frontend:     # React app
```

---

## Phase 2: Cloud Abstraction

### [NEW] backend/adapters/storage.py
```python
class StorageAdapter(ABC):
    @abstractmethod
    def upload(self, key: str, data: bytes) -> str: ...
    @abstractmethod
    def download(self, key: str) -> bytes: ...
    @abstractmethod
    def get_presigned_url(self, key: str) -> str: ...

class S3Storage(StorageAdapter): ...
class MinIOStorage(StorageAdapter): ...
class LocalStorage(StorageAdapter): ...
```

### [NEW] backend/adapters/queue.py
```python
class QueueAdapter(ABC):
    @abstractmethod
    def send_message(self, body: dict) -> None: ...
    @abstractmethod
    def receive_message(self) -> Optional[dict]: ...

class SQSQueue(QueueAdapter): ...
class RedisQueue(QueueAdapter): ...
```

### Config Selection
```python
# config.py
CLOUD_PROVIDER = os.getenv("CLOUD_PROVIDER", "local")  # local | aws | gcp

def get_storage() -> StorageAdapter:
    if CLOUD_PROVIDER == "aws":
        return S3Storage()
    return MinIOStorage()  # Local development
```

---

## Phase 3: Kubernetes

### [NEW] k8s/deployment.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: examshuffling-api
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: api
        image: examshuffling/api:latest
        envFrom:
        - configMapRef:
            name: app-config
        - secretRef:
            name: aws-credentials
```

### [NEW] k8s/hpa.yaml (Auto-scaling)
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      targetAverageUtilization: 70
```

---

## Phase 4: Terraform (IaC)

### [NEW] terraform/aws/main.tf
```hcl
# S3 Buckets
resource "aws_s3_bucket" "input" { ... }
resource "aws_s3_bucket" "output" { ... }

# SQS Queue
resource "aws_sqs_queue" "jobs" { ... }

# DynamoDB
resource "aws_dynamodb_table" "jobs" { ... }

# ECS/EKS for containers
resource "aws_ecs_cluster" "main" { ... }
```

---

## Verification Plan

```bash
# 1. Test Docker locally
docker-compose up -d
curl http://localhost:5000/docs

# 2. Test K8s locally (minikube)
minikube start
kubectl apply -f k8s/
kubectl get pods

# 3. Deploy to AWS
terraform apply
```

---

## Learning Outcomes

Sau khi hoàn thành, bạn sẽ có kinh nghiệm với:
- ✅ Docker & Docker Compose
- ✅ Kubernetes (Deployments, Services, ConfigMaps, HPA)
- ✅ Terraform (Infrastructure as Code)
- ✅ Cloud Abstraction Patterns
- ✅ CI/CD với GitHub Actions
- ✅ Multi-cloud architecture design
