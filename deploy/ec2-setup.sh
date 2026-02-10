#!/bin/bash
# =============================================================
# EC2 Setup Script for ExamShuffling
# Run this script on a fresh Ubuntu 22.04/24.04 EC2 instance
# Usage: chmod +x deploy/ec2-setup.sh && sudo ./deploy/ec2-setup.sh
# =============================================================

set -e

echo "========================================="
echo "  🚀 ExamShuffling EC2 Setup"
echo "========================================="

# --- 1. UPDATE SYSTEM ---
echo ""
echo "📦 Step 1/5: Updating system packages..."
apt-get update -y
apt-get upgrade -y

# --- 2. INSTALL DOCKER ---
echo ""
echo "🐳 Step 2/5: Installing Docker..."
apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable Docker for current user
usermod -aG docker ubuntu
systemctl enable docker
systemctl start docker

echo "✅ Docker installed: $(docker --version)"

# --- 3. INSTALL GIT ---
echo ""
echo "📁 Step 3/5: Installing Git..."
apt-get install -y git

# --- 4. CLONE REPOSITORY ---
echo ""
echo "📂 Step 4/5: Setting up project..."
cd /home/ubuntu

if [ -d "PythonProject1" ]; then
    echo "  Project already exists, pulling latest..."
    cd PythonProject1
    git pull
else
    echo "  Cloning repository..."
    echo "  ⚠️  You need to clone your repository manually:"
    echo "  git clone <YOUR_REPO_URL> PythonProject1"
    echo "  Or upload your project files via SCP/SFTP"
    mkdir -p PythonProject1
    cd PythonProject1
fi

# --- 5. CREATE DIRECTORIES ---
echo ""
echo "📁 Step 5/5: Creating required directories..."
mkdir -p nginx/conf.d
mkdir -p certbot/conf
mkdir -p certbot/www

echo ""
echo "========================================="
echo "  ✅ EC2 Setup Complete!"
echo "========================================="
echo ""
echo "📋 Next Steps:"
echo ""
echo "  1. Upload your project files to /home/ubuntu/PythonProject1/"
echo "     scp -i your-key.pem -r ./* ubuntu@<EC2_IP>:/home/ubuntu/PythonProject1/"
echo ""
echo "  2. Create .env.prod file for frontend build args:"
echo "     cp deploy/.env.prod.example .env.prod"
echo "     nano .env.prod  # Fill in your AWS keys"
echo ""
echo "  3. Start WITHOUT SSL first (to get certificates):"
echo "     docker compose -f docker-compose.init.yml up -d"
echo ""
echo "  4. Get SSL certificate:"
echo "     docker compose run --rm certbot certonly --webroot -w /var/www/certbot \\"
echo "       -d trondeonline.me -d www.trondeonline.me -d api.trondeonline.me \\"
echo "       --email YOUR_EMAIL --agree-tos --no-eff-email"
echo ""
echo "  5. Start the full production stack:"
echo "     docker compose -f docker-compose.prod.yml up -d --build"
echo ""
