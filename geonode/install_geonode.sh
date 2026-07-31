#!/bin/bash

# ============================================================
# GeoNode 4.4.2 - SAFE Installation Script
# ============================================================
# SAFE MODE:
# - Does NOT touch your existing Django deployment
# - Does NOT touch your existing PostgreSQL databases
# - Does NOT touch your existing nginx config
# - Does NOT run apt upgrade (won't affect running containers)
# - Does NOT install Docker (already installed)
# - Runs GeoNode on port 8080 in its own isolated environment
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "============================================================"
echo "  GeoNode 4.4.2 - Safe Installation (Port 8080)"
echo "  Your existing Django API will NOT be touched"
echo "============================================================"
echo -e "${NC}"

# -----------------------------------------------------------
# 1. Pre-flight checks
# -----------------------------------------------------------

echo -e "${YELLOW}Running pre-flight checks...${NC}"

# Check Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found. Please install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker found: $(docker --version)${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose plugin not found.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose found: $(docker-compose version)${NC}"

# Check port 8080 is free
if ss -tlnp | grep -q ':8080'; then
    echo -e "${RED}Port 8080 is already in use. Please free it before continuing.${NC}"
    ss -tlnp | grep ':8080'
    exit 1
fi
echo -e "${GREEN}✓ Port 8080 is available${NC}"

# Check disk space (need at least 15GB)
AVAILABLE=$(df /opt --output=avail -BG | tail -1 | tr -d 'G ')
if [ "$AVAILABLE" -lt 15 ]; then
    echo -e "${RED}Not enough disk space. Need 15GB, have ${AVAILABLE}GB free.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Disk space OK: ${AVAILABLE}GB available${NC}"

# Check RAM (need at least 3GB free)
FREE_RAM=$(free -g | awk '/^Mem:/{print $7}')
if [ "$FREE_RAM" -lt 3 ]; then
    echo -e "${YELLOW}⚠ Low free RAM: ${FREE_RAM}GB. GeoNode needs at least 3GB free. Proceeding anyway...${NC}"
else
    echo -e "${GREEN}✓ RAM OK: ${FREE_RAM}GB free${NC}"
fi

echo ""
echo -e "${GREEN}All pre-flight checks passed.${NC}"
echo ""

# -----------------------------------------------------------
# 2. Get user input
# -----------------------------------------------------------

echo -e "${YELLOW}Detecting your public IP...${NC}"
PUBLIC_IP=$(curl -4 -s ifconfig.me)

if [ -z "$PUBLIC_IP" ]; then
    echo -e "${RED}Could not detect public IP automatically.${NC}"
    read -p "Please enter your server's public IP: " PUBLIC_IP
else
    echo -e "${GREEN}Detected public IP: ${PUBLIC_IP}${NC}"
    read -p "Is this correct? (y/n): " CONFIRM_IP
    if [ "$CONFIRM_IP" != "y" ] && [ "$CONFIRM_IP" != "Y" ]; then
        read -p "Enter the correct public IP: " PUBLIC_IP
    fi
fi

read -p "Enter your GeoNode project name (default: rapida_geonode): " PROJECT_NAME
PROJECT_NAME=${PROJECT_NAME:-rapida_geonode}

echo ""
echo -e "${CYAN}--- Set Your Credentials ---${NC}"
echo ""

read -p "GeoNode admin username (default: admin): " ADMIN_USERNAME
ADMIN_USERNAME=${ADMIN_USERNAME:-admin}

read -sp "GeoNode admin password: " ADMIN_PASSWORD
echo ""
while [ -z "$ADMIN_PASSWORD" ]; do
    echo -e "${RED}Password cannot be empty.${NC}"
    read -sp "GeoNode admin password: " ADMIN_PASSWORD
    echo ""
done

read -p "GeoNode admin email (default: admin@example.com): " ADMIN_EMAIL
ADMIN_EMAIL=${ADMIN_EMAIL:-admin@example.com}

read -sp "GeoNode PostgreSQL password (for GeoNode's OWN databases only): " DB_PASSWORD
echo ""
while [ -z "$DB_PASSWORD" ]; do
    echo -e "${RED}Password cannot be empty.${NC}"
    read -sp "GeoNode PostgreSQL password: " DB_PASSWORD
    echo ""
done

read -sp "GeoServer admin password: " GEOSERVER_PASSWORD
echo ""
while [ -z "$GEOSERVER_PASSWORD" ]; do
    echo -e "${RED}Password cannot be empty.${NC}"
    read -sp "GeoServer admin password: " GEOSERVER_PASSWORD
    echo ""
done

echo ""
echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}  Installation Summary${NC}"
echo -e "${CYAN}============================================================${NC}"
echo -e "  Public IP:             ${GREEN}${PUBLIC_IP}${NC}"
echo -e "  Project Name:          ${GREEN}${PROJECT_NAME}${NC}"
echo -e "  Install Dir:           ${GREEN}/opt/${PROJECT_NAME}${NC}"
echo -e "  GeoNode URL:           ${GREEN}http://${PUBLIC_IP}:8080/geonode/${NC}"
echo -e "  GeoServer URL:         ${GREEN}http://${PUBLIC_IP}:8080/geoserver/${NC}"
echo -e "  Internal Port:         ${GREEN}8080${NC}"
echo -e "  GeoNode Admin:         ${GREEN}${ADMIN_USERNAME}${NC}"
echo -e "  GeoNode Admin Email:   ${GREEN}${ADMIN_EMAIL}${NC}"
echo -e "  GeoServer Admin:       ${GREEN}admin${NC}"
echo ""
echo -e "${YELLOW}  ✓ Your existing Django API at port 80 will NOT be touched${NC}"
echo -e "${YELLOW}  ✓ Your existing PostgreSQL databases will NOT be touched${NC}"
echo -e "${YELLOW}  ✓ GeoNode will use its own separate PostgreSQL container${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""
read -p "Proceed with installation? (y/n): " PROCEED
if [ "$PROCEED" != "y" ] && [ "$PROCEED" != "Y" ]; then
    echo "Installation cancelled."
    exit 0
fi

# -----------------------------------------------------------
# 3. Install only missing dependencies (git, python3)
# -----------------------------------------------------------

echo ""
echo -e "${YELLOW}[1/7] Checking required packages (git, python3)...${NC}"

# Only install what's missing — do NOT run apt upgrade
for pkg in git python3 python3-pip; do
    if ! dpkg -l | grep -q "^ii  $pkg "; then
        echo "Installing missing package: $pkg"
        apt install -y "$pkg"
    else
        echo -e "${GREEN}✓ $pkg already installed${NC}"
    fi
done

echo -e "${GREEN}[1/7] Dependencies ready.${NC}"

# -----------------------------------------------------------
# 4. Clone GeoNode project
# -----------------------------------------------------------

echo ""
echo -e "${YELLOW}[2/7] Setting up GeoNode project...${NC}"

cd /opt

if [ -d "geonode-project" ]; then
    echo "Removing existing geonode-project clone..."
    rm -rf geonode-project
fi

if [ -d "$PROJECT_NAME" ]; then
    echo -e "${RED}Directory /opt/${PROJECT_NAME} already exists.${NC}"
    read -p "Remove it and start fresh? (y/n): " REMOVE_EXISTING
    if [ "$REMOVE_EXISTING" == "y" ] || [ "$REMOVE_EXISTING" == "Y" ]; then
        cd "$PROJECT_NAME"
        docker-compose down -v 2>/dev/null || true
        cd /opt
        rm -rf "$PROJECT_NAME"
    else
        echo "Installation cancelled."
        exit 1
    fi
fi

git clone https://github.com/GeoNode/geonode-project.git -b 4.4.x

pip install Django==4.2.* --break-system-packages 2>/dev/null || pip install Django==4.2.*

django-admin startproject \
    --template=./geonode-project \
    -e py,sh,md,rst,json,yml,ini,env,sample,properties \
    -n monitoring-cron \
    -n Dockerfile \
    "$PROJECT_NAME"

echo -e "${GREEN}[2/7] GeoNode project created at /opt/${PROJECT_NAME}${NC}"

# -----------------------------------------------------------
# 5. Generate .env file
# -----------------------------------------------------------

echo ""
echo -e "${YELLOW}[3/7] Generating environment file...${NC}"

cd /opt/"$PROJECT_NAME"

if [ -f "create-envfile.py" ]; then
    python3 create-envfile.py
elif [ -f ".env.sample" ]; then
    cp .env.sample .env
elif [ -f ".env.example" ]; then
    cp .env.example .env
fi

if [ ! -f ".env" ]; then
    echo -e "${RED}ERROR: .env file was not created.${NC}"
    exit 1
fi

echo -e "${GREEN}[3/7] Environment file generated.${NC}"

# -----------------------------------------------------------
# 6. Configure environment variables
# -----------------------------------------------------------

echo ""
echo -e "${YELLOW}[4/7] Configuring environment variables...${NC}"

# SITEURL — subpath so it can later be proxied under /geonode/
sed -i '/^SITEURL=/d' .env
echo "SITEURL=http://${PUBLIC_IP}:8080/geonode/" >> .env

# HTTP_HOST
if grep -q "^HTTP_HOST=" .env; then
    sed -i "s|^HTTP_HOST=.*|HTTP_HOST=${PUBLIC_IP}|" .env
else
    echo "HTTP_HOST=${PUBLIC_IP}" >> .env
fi

# NGINX_BASE_URL
if grep -q "^NGINX_BASE_URL=" .env; then
    sed -i "s|^NGINX_BASE_URL=.*|NGINX_BASE_URL=http://${PUBLIC_IP}:8080/geonode|" .env
else
    echo "NGINX_BASE_URL=http://${PUBLIC_IP}:8080/geonode" >> .env
fi

# GeoServer URLs
if grep -q "^GEOSERVER_WEB_UI_LOCATION=" .env; then
    sed -i "s|^GEOSERVER_WEB_UI_LOCATION=.*|GEOSERVER_WEB_UI_LOCATION=http://${PUBLIC_IP}:8080/geoserver/|" .env
else
    echo "GEOSERVER_WEB_UI_LOCATION=http://${PUBLIC_IP}:8080/geoserver/" >> .env
fi

if grep -q "^GEOSERVER_PUBLIC_LOCATION=" .env; then
    sed -i "s|^GEOSERVER_PUBLIC_LOCATION=.*|GEOSERVER_PUBLIC_LOCATION=http://${PUBLIC_IP}:8080/geoserver/|" .env
else
    echo "GEOSERVER_PUBLIC_LOCATION=http://${PUBLIC_IP}:8080/geoserver/" >> .env
fi

# ALLOWED_HOSTS
if grep -q "^ALLOWED_HOSTS=" .env; then
    sed -i "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=\"['django', '${PUBLIC_IP}', 'localhost', '*']\"|" .env
fi

# Internal load balancer port
if grep -q "^GEONODE_LB_HOST_IP=" .env; then
    sed -i "s|^GEONODE_LB_HOST_IP=.*|GEONODE_LB_HOST_IP=${PUBLIC_IP}|" .env
else
    echo "GEONODE_LB_HOST_IP=${PUBLIC_IP}" >> .env
fi

if grep -q "^GEONODE_LB_PORT=" .env; then
    sed -i "s|^GEONODE_LB_PORT=.*|GEONODE_LB_PORT=8080|" .env
else
    echo "GEONODE_LB_PORT=8080" >> .env
fi

# Database credentials — GeoNode's OWN db container, NOT your existing postgres
sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${DB_PASSWORD}|" .env

sed -i "s|^GEONODE_DATABASE_PASSWORD=.*|GEONODE_DATABASE_PASSWORD=${DB_PASSWORD}|" .env
sed -i "s|^DATABASE_URL=.*|DATABASE_URL=postgis://${PROJECT_NAME}:${DB_PASSWORD}@db:5432/${PROJECT_NAME}|" .env

sed -i "s|^GEONODE_GEODATABASE_PASSWORD=.*|GEONODE_GEODATABASE_PASSWORD=${DB_PASSWORD}|" .env
sed -i "s|^GEODATABASE_URL=.*|GEODATABASE_URL=postgis://${PROJECT_NAME}_data:${DB_PASSWORD}@db:5432/${PROJECT_NAME}_data|" .env

# Admin credentials
if grep -q "^ADMIN_USERNAME=" .env; then
    sed -i "s|^ADMIN_USERNAME=.*|ADMIN_USERNAME=${ADMIN_USERNAME}|" .env
else
    echo "ADMIN_USERNAME=${ADMIN_USERNAME}" >> .env
fi

if grep -q "^ADMIN_PASSWORD=" .env; then
    sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=${ADMIN_PASSWORD}|" .env
else
    echo "ADMIN_PASSWORD=${ADMIN_PASSWORD}" >> .env
fi

if grep -q "^ADMIN_EMAIL=" .env; then
    sed -i "s|^ADMIN_EMAIL=.*|ADMIN_EMAIL=${ADMIN_EMAIL}|" .env
else
    echo "ADMIN_EMAIL=${ADMIN_EMAIL}" >> .env
fi

if grep -q "^GEOSERVER_ADMIN_PASSWORD=" .env; then
    sed -i "s|^GEOSERVER_ADMIN_PASSWORD=.*|GEOSERVER_ADMIN_PASSWORD=${GEOSERVER_PASSWORD}|" .env
else
    echo "GEOSERVER_ADMIN_PASSWORD=${GEOSERVER_PASSWORD}" >> .env
fi

echo -e "${GREEN}[4/7] Environment configured.${NC}"

echo ""
echo -e "${CYAN}--- URL Configuration ---${NC}"
grep -E "^SITEURL=|^HTTP_HOST=|^NGINX_BASE_URL=|^GEOSERVER_WEB_UI_LOCATION=|^GEOSERVER_PUBLIC_LOCATION=|^GEONODE_LB_PORT=" .env

echo ""
echo -e "${CYAN}--- Database (GeoNode's own container) ---${NC}"
grep -E "^POSTGRES_PASSWORD=|^DATABASE_URL=|^GEODATABASE_URL=" .env

# -----------------------------------------------------------
# 7. Build Docker images
# -----------------------------------------------------------

echo ""
echo -e "${YELLOW}[5/7] Building Docker images (this may take 10-20 minutes)...${NC}"
echo -e "${YELLOW}      Your existing containers will keep running during this.${NC}"

docker-compose build

echo -e "${GREEN}[5/7] Docker images built.${NC}"

# -----------------------------------------------------------
# 8. Start GeoNode containers
# -----------------------------------------------------------

echo ""
echo -e "${YELLOW}[6/7] Starting GeoNode containers...${NC}"

docker-compose up -d

echo -e "${GREEN}[6/7] GeoNode containers started.${NC}"

# -----------------------------------------------------------
# 9. Wait for Django to become healthy
# -----------------------------------------------------------

echo ""
echo -e "${YELLOW}[7/7] Waiting for GeoNode to become healthy (2-5 minutes)...${NC}"

MAX_WAIT=300
ELAPSED=0
INTERVAL=10

while [ $ELAPSED -lt $MAX_WAIT ]; do
    STATUS=$(docker ps --filter "name=django4${PROJECT_NAME}" --format "{{.Status}}" 2>/dev/null)
    if echo "$STATUS" | grep -q "(healthy)"; then
        echo -e "${GREEN}GeoNode Django is healthy!${NC}"
        break
    fi
    echo "  Still starting... (${ELAPSED}s elapsed)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "${YELLOW}GeoNode hasn't reported healthy yet — may still be starting.${NC}"
    echo "Check with: docker ps | grep django"
fi

docker-compose up -d

# -----------------------------------------------------------
# 10. Verify existing deployment is still running
# -----------------------------------------------------------

echo ""
echo -e "${CYAN}--- Verifying your existing deployment is still running ---${NC}"
docker ps --filter "name=rapida_backend" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# -----------------------------------------------------------
# Final summary
# -----------------------------------------------------------

echo ""
echo -e "${CYAN}============================================================${NC}"
echo -e "${GREEN}  GeoNode Installation Complete!${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""
echo -e "  ${CYAN}Your existing API (unchanged):${NC}"
echo -e "    http://${PUBLIC_IP}/              ${GREEN}✓ still running${NC}"
echo ""
echo -e "  ${CYAN}GeoNode (new):${NC}"
echo -e "    GeoNode URL:    ${GREEN}http://${PUBLIC_IP}:8080/geonode/${NC}"
echo -e "    GeoServer URL:  ${GREEN}http://${PUBLIC_IP}:8080/geoserver/${NC}"
echo ""
echo -e "  ${CYAN}Credentials:${NC}"
echo -e "    GeoNode:    ${GREEN}${ADMIN_USERNAME} / [your password]${NC}"
echo -e "    GeoServer:  ${GREEN}admin / [your password]${NC}"
echo ""
echo -e "  ${CYAN}Project directory:  /opt/${PROJECT_NAME}${NC}"
echo ""
echo -e "${CYAN}  To proxy GeoNode through your existing nginx (optional):${NC}"
echo "  Add this to your nginx server block:"
echo ""
echo "    location /geonode/ {"
echo "        proxy_pass http://127.0.0.1:8080/geonode/;"
echo "        proxy_set_header Host \$host;"
echo "        proxy_set_header X-Real-IP \$remote_addr;"
echo "        client_max_body_size 100M;"
echo "    }"
echo "    location /geoserver/ {"
echo "        proxy_pass http://127.0.0.1:8080/geoserver/;"
echo "        proxy_set_header Host \$host;"
echo "        proxy_set_header X-Real-IP \$remote_addr;"
echo "        client_max_body_size 100M;"
echo "    }"
echo ""
echo -e "${CYAN}  Useful GeoNode commands:${NC}"
echo "    cd /opt/${PROJECT_NAME}"
echo "    docker-compose ps                    # GeoNode container status"
echo "    docker-compose logs -f django        # GeoNode Django logs"
echo "    docker-compose logs -f geoserver     # GeoServer logs"
echo "    docker-compose down                  # Stop GeoNode only"
echo "    docker-compose up -d                 # Start GeoNode only"
echo ""
echo -e "${CYAN}============================================================${NC}"
