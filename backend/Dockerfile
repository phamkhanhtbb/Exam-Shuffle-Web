# Dockerfile for FastAPI Backend

FROM python:3.9-slim

WORKDIR /app

# Install system dependencies (e.g., for python-docx or other libs if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Command to run the application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5000"]
