#!/bin/bash
# ============================================
# Tinyproxy Monitor 오프라인 패키지 생성 스크립트
# Backend (.whl) + Frontend (dist.tar.gz) + Python 의존성
# 최신 Python 패키징 표준 사용 (pyproject.toml + build)
# ============================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 로그 함수
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# 변수 설정
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="${PROJECT_DIR}/build"
OUTPUT_DIR="${BUILD_DIR}/packages"
VERSION="1.0.0"

# ============================================
# 1. 환경 확인
# ============================================
check_requirements() {
    log_info "Checking requirements..."
    
    # Python 확인
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 is not installed"
        exit 1
    fi
    
    # Node.js 확인
    if ! command -v node &> /dev/null; then
        log_error "Node.js is not installed"
        exit 1
    fi
    
    # npm 확인
    if ! command -v npm &> /dev/null; then
        log_error "npm is not installed"
        exit 1
    fi
    
    log_info "All requirements met"
}

# ============================================
# 2. 디렉토리 초기화
# ============================================
init_directories() {
    log_info "Initializing build directories..."
    
    # 기존 빌드 디렉토리 삭제
    rm -rf "${BUILD_DIR}"
    
    # 디렉토리 생성
    mkdir -p "${OUTPUT_DIR}"
    
    log_info "Build directories created"
}

# ============================================
# 3. Backend 패키지 생성 (최신 방법 사용)
# ============================================
create_backend_package() {
    log_info "Creating backend wheel package using modern standards..."
    
    cd "${PROJECT_DIR}/backend"
    
    # pyproject.toml 생성 (PEP 639 준수 - SPDX license expression 사용)
    cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "tinyproxy-monitor"
version = "1.0.0"
description = "Web-based monitoring system for Tinyproxy"
readme = "README.md"
requires-python = ">=3.9"
license = "MIT"  # SPDX license expression (simple string)
license-files = ["LICENSE"]  # License file paths
authors = [
    {name = "Tinyproxy Monitor Team", email = "admin@example.com"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: System Administrators",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: System :: Monitoring",
    # License:: classifier 제거 (deprecated)
]
dependencies = [
    "fastapi==0.104.1",
    "uvicorn[standard]==0.24.0",
    "psutil==5.9.6",
    "python-dotenv==1.0.0",
    "websockets==12.0",
    "aiofiles==23.2.1",
    "httpx==0.25.1",
    "numpy==1.24.3",
    "beautifulsoup4==4.12.2",
    "watchdog==3.0.0",
    "python-jose[cryptography]==3.3.0",
    "python-multipart==0.0.6",
    "passlib[bcrypt]==1.7.4",
    "python-pam==2.0.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "black>=22.0",
    "flake8>=5.0",
]

[project.scripts]
tinyproxy-monitor = "app.main:run_server"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]
exclude = ["tests*"]

[tool.setuptools.package-data]
app = ["**/*.html", "**/*.css", "**/*.js", "**/*.json"]
EOF

    # LICENSE 파일 생성 (license-files에서 참조)
    cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2024 Tinyproxy Monitor Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF

    # README.md 생성 (pyproject.toml에서 참조)
    cat > README.md << 'EOF'
# Tinyproxy Monitor Backend

Web-based monitoring system for Tinyproxy proxy server.

## Installation

```bash
pip install tinyproxy-monitor-*.whl
```

## Usage

```bash
# Run with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Or use the console script
tinyproxy-monitor
```

## License

MIT License - see LICENSE file for details.
EOF

    # 가상환경 생성 및 build 도구 설치
    python3 -m venv build_env
    source build_env/bin/activate
    pip install --upgrade pip setuptools wheel build
    
    # 최신 방법으로 wheel 빌드 (python -m build)
    log_info "Building wheel using 'python -m build'..."
    python -m build --wheel --outdir dist/
    
    # wheel 파일 복사
    cp dist/*.whl "${OUTPUT_DIR}/"
    
    # 파일명 확인
    WHEEL_FILE=$(ls dist/*.whl | head -n 1)
    WHEEL_NAME=$(basename "$WHEEL_FILE")
    
    deactivate
    rm -rf build_env build dist *.egg-info
    rm -f pyproject.toml README.md LICENSE
    
    log_info "Backend wheel package created: ${WHEEL_NAME}"
}

# ============================================
# 4. Python 의존성 다운로드
# ============================================
download_python_deps() {
    log_info "Downloading Python dependencies..."
    
    cd "${PROJECT_DIR}/backend"
    
    # 의존성 다운로드 디렉토리
    DEPS_DIR="${OUTPUT_DIR}/python-deps"
    mkdir -p "${DEPS_DIR}"
    
    # 임시 가상환경 생성
    python3 -m venv deps_env
    source deps_env/bin/activate
    pip install --upgrade pip
    
    # 의존성 다운로드
    pip download -r requirements.txt -d "${DEPS_DIR}/"
    
    # build 도구들도 포함 (최신 패키징에 필요)
    pip download pip setuptools wheel build -d "${DEPS_DIR}/"
    
    deactivate
    rm -rf deps_env
    
    # 의존성 압축
    cd "${OUTPUT_DIR}"
    tar czf python-deps.tar.gz python-deps/
    rm -rf python-deps/
    
    log_info "Python dependencies downloaded and packaged: python-deps.tar.gz"
}

# ============================================
# 4.5. RPM 의존성 포함 (Nginx 등)
# ============================================
include_rpm_dependencies() {
    log_info "Including RPM dependencies..."
    
    RPM_SOURCE_DIR="${PROJECT_DIR}/dependencies"
    RPM_DEST_DIR="${OUTPUT_DIR}/rpms"
    
    if [ -d "${RPM_SOURCE_DIR}" ]; then
        mkdir -p "${RPM_DEST_DIR}"
        
        # RPM 파일 복사
        if ls "${RPM_SOURCE_DIR}"/*.rpm 1> /dev/null 2>&1; then
            cp "${RPM_SOURCE_DIR}"/*.rpm "${RPM_DEST_DIR}/"
            
            # RPM 목록 생성
            ls -1 "${RPM_DEST_DIR}"/*.rpm | xargs -n1 basename > "${RPM_DEST_DIR}/rpm-list.txt"
            
            RPM_COUNT=$(ls -1 "${RPM_DEST_DIR}"/*.rpm | wc -l)
            log_info "Included ${RPM_COUNT} RPM packages"
        else
            log_warn "No RPM files found in ${RPM_SOURCE_DIR}"
        fi
    else
        log_warn "RPM source directory not found: ${RPM_SOURCE_DIR}"
    fi
}

# ============================================
# 5. Frontend 빌드
# ============================================
build_frontend() {
    log_info "Building frontend..."
    
    cd "${PROJECT_DIR}/frontend"
    
    # node_modules가 없으면 설치
    if [ ! -d "node_modules" ]; then
        log_info "Installing frontend dependencies..."
        npm install
    fi
    
    # 프로덕션 환경 설정
    cat > .env.production << 'EOF'
VITE_API_URL=/api
VITE_WS_URL=/ws
EOF
    
    # 빌드
    npm run build
    
    # 빌드 결과 압축
    if [ -d "dist" ]; then
        tar czf "${OUTPUT_DIR}/frontend-dist.tar.gz" -C dist .
        log_info "Frontend build completed: frontend-dist.tar.gz"
    else
        log_error "Frontend build failed - dist directory not found"
        exit 1
    fi
    
    rm -f .env.production
}

# ============================================
# 6. SSL 인증서 생성 스크립트 추가
# ============================================
create_ssl_cert_script() {
    log_info "Creating SSL certificate generation script..."
    
    cat > "${OUTPUT_DIR}/generate-ssl-cert.sh" << 'EOF'
#!/bin/bash
# SSL 인증서 자동 생성 스크립트 (HTTPS 전용 설정)

SSL_DIR="/etc/tinyproxy-monitor/ssl"
CERT_DAYS=3650  # 10년
KEY_SIZE=2048   # RSA 2048 고정

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Root 권한 확인
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root"
    exit 1
fi

# SSL 디렉토리 생성
log_info "Creating SSL directory..."
mkdir -p "$SSL_DIR"
chmod 755 "$SSL_DIR"

# 서버 정보 자동 설정
DOMAIN="localhost"
ORG="Tinyproxy Monitor"
COUNTRY="KR"

# 모든 서버 IP 자동 감지
SERVER_IPS=$(hostname -I)
if [ -z "$SERVER_IPS" ]; then
    SERVER_IPS="127.0.0.1"
fi

# 서버 호스트명 감지
SERVER_HOSTNAME=$(hostname -f 2>/dev/null || hostname)

log_info "Generating SSL certificate for:"
log_info "  Domain: $DOMAIN"
log_info "  Hostname: $SERVER_HOSTNAME"
log_info "  Server IPs: $SERVER_IPS"
log_info "  Organization: $ORG"
log_info "  Key Size: RSA $KEY_SIZE"

# OpenSSL 설정 파일 생성
log_info "Creating OpenSSL configuration..."
cat > "$SSL_DIR/openssl.cnf" << EOC
[req]
default_bits = $KEY_SIZE
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=$COUNTRY
ST=Seoul
L=Seoul
O=$ORG
OU=IT Department
CN=$DOMAIN

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = *.$DOMAIN
DNS.3 = localhost
DNS.4 = *.localhost
DNS.5 = $SERVER_HOSTNAME
IP.1 = 127.0.0.1
IP.2 = ::1
EOC

# 모든 서버 IP 주소 추가
IP_INDEX=3
for IP in $SERVER_IPS; do
    echo "IP.$IP_INDEX = $IP" >> "$SSL_DIR/openssl.cnf"
    IP_INDEX=$((IP_INDEX + 1))
done

# 일반적인 내부망 IP 패턴도 추가 (선택적)
# Docker 브리지, Kubernetes 클러스터 IP 등을 위해
if ip addr show | grep -q "172.17"; then
    echo "IP.$IP_INDEX = 172.17.0.1" >> "$SSL_DIR/openssl.cnf"
    IP_INDEX=$((IP_INDEX + 1))
fi
if ip addr show | grep -q "10.0"; then
    echo "IP.$IP_INDEX = 10.0.0.1" >> "$SSL_DIR/openssl.cnf"
    IP_INDEX=$((IP_INDEX + 1))
fi

# 개인키 생성 (RSA 2048)
log_info "Generating RSA $KEY_SIZE private key..."
openssl genrsa -out "$SSL_DIR/server.key" $KEY_SIZE 2>/dev/null

# CSR 생성 (자동)
log_info "Generating certificate signing request..."
openssl req -new -key "$SSL_DIR/server.key" \
    -out "$SSL_DIR/server.csr" \
    -config "$SSL_DIR/openssl.cnf" 2>/dev/null

# 자체 서명 인증서 생성
log_info "Generating self-signed certificate (valid for $CERT_DAYS days)..."
openssl x509 -req -in "$SSL_DIR/server.csr" \
    -signkey "$SSL_DIR/server.key" \
    -out "$SSL_DIR/server.crt" \
    -days $CERT_DAYS \
    -extensions v3_req \
    -extfile "$SSL_DIR/openssl.cnf" 2>/dev/null

# PEM 파일 생성 (일부 애플리케이션용)
cat "$SSL_DIR/server.crt" "$SSL_DIR/server.key" > "$SSL_DIR/server.pem"

# Diffie-Hellman 파라미터 생성 (보안 강화) - 백그라운드에서 생성
log_info "Generating Diffie-Hellman parameters (this may take a while)..."
openssl dhparam -out "$SSL_DIR/dhparam.pem" 2048 2>/dev/null &
DH_PID=$!

# DH 생성 중 다른 작업 수행
# 권한 설정
chmod 600 "$SSL_DIR/server.key"
chmod 644 "$SSL_DIR/server.crt"
chmod 644 "$SSL_DIR/server.pem"

# DH 생성 완료 대기
wait $DH_PID
chmod 644 "$SSL_DIR/dhparam.pem"

# 인증서 정보 확인
log_info "Certificate information:"
log_info "Subject:"
openssl x509 -in "$SSL_DIR/server.crt" -text -noout 2>/dev/null | grep "Subject:" | head -1
log_info "Alternative Names:"
openssl x509 -in "$SSL_DIR/server.crt" -text -noout 2>/dev/null | grep -A 20 "Subject Alternative Name" | grep -E "(DNS:|IP:)"

log_info "========================================="
log_info "SSL certificate generated successfully!"
log_info "========================================="
log_info "Certificate location:"
log_info "  Private Key: $SSL_DIR/server.key"
log_info "  Certificate: $SSL_DIR/server.crt"
log_info "  PEM Bundle: $SSL_DIR/server.pem"
log_info "  DH Params: $SSL_DIR/dhparam.pem"
log_info "========================================="
log_info "Certificate includes:"
log_info "  - All server IP addresses"
log_info "  - Server hostname: $SERVER_HOSTNAME"
log_info "  - localhost and *.localhost"
log_info "  - IPv4 and IPv6 loopback addresses"
log_info "========================================="
log_warn "Note: This is a self-signed certificate."
log_warn "Users will see a security warning in browsers."
log_info "========================================="

# 성공 코드 반환
exit 0
EOF
    
    chmod +x "${OUTPUT_DIR}/generate-ssl-cert.sh"
    log_info "SSL certificate generation script created: generate-ssl-cert.sh"
}

# ============================================
# 7. 설치 가이드 생성 (HTTPS 포함)
# ============================================
create_install_guide() {
    log_info "Creating installation guide..."
    
    cat > "${OUTPUT_DIR}/INSTALL.md" << 'EOF'
# Tinyproxy Monitor 설치 가이드

## 패키지 구성
- `tinyproxy_monitor-*.whl` - Backend Python 패키지
- `python-deps.tar.gz` - Python 의존성 패키지
- `frontend-dist.tar.gz` - Frontend 빌드 파일

## Backend 설치

### 1. Python 가상환경 생성
```bash
python3 -m venv /opt/tinyproxy-monitor/venv
source /opt/tinyproxy-monitor/venv/bin/activate
```

### 2. 의존성 설치 (오프라인)
```bash
# 의존성 압축 해제
tar xzf python-deps.tar.gz

# 최신 build 도구 설치
pip install --no-index --find-links python-deps/ pip setuptools wheel build

# 모든 의존성 설치
pip install --no-index --find-links python-deps/ \
    fastapi uvicorn[standard] psutil python-dotenv \
    websockets aiofiles httpx numpy beautifulsoup4 \
    watchdog python-jose[cryptography] python-multipart \
    passlib[bcrypt] python-pam

# Backend 패키지 설치
pip install --no-index --find-links . tinyproxy_monitor-*.whl
```

### 3. 환경 설정
```bash
# .env 파일 생성
cat > /opt/tinyproxy-monitor/.env << 'END'
PROXY_LOG_PATH=/var/log/tinyproxy/tinyproxy.log
PROXY_PID_PATH=/var/run/tinyproxy/tinyproxy.pid
PROXY_STATS_HOST=localhost:3128
PROXY_STATS_HOSTNAME=tinyproxy.stats
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost,http://127.0.0.1
DISABLE_AUTH=false
SECRET_KEY=$(openssl rand -hex 32)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$(openssl rand -base64 12)
END
```

### 4. 실행
```bash
cd /opt/tinyproxy-monitor

# uvicorn으로 직접 실행
/opt/tinyproxy-monitor/venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 --port 8000

# 또는 설치된 console script 사용
/opt/tinyproxy-monitor/venv/bin/tinyproxy-monitor
```

## 시스템 의존성 설치 (RPM)

```bash
# RPM 패키지 설치 (오프라인)
cd rpms/
rpm -ivh *.rpm
# 또는 의존성 자동 해결
yum localinstall *.rpm --disablerepo=* -y


## SSL 인증서 생성 (필수 - HTTPS 전용)

```bash
# SSL 인증서 생성 스크립트 실행 (필수)
./generate-ssl-cert.sh

# 또는 기존 인증서가 있는 경우
mkdir -p /etc/tinyproxy-monitor/ssl
cp your-cert.crt /etc/tinyproxy-monitor/ssl/server.crt
cp your-cert.key /etc/tinyproxy-monitor/ssl/server.key
chmod 600 /etc/tinyproxy-monitor/ssl/server.key
chmod 644 /etc/tinyproxy-monitor/ssl/server.crt
```

## Frontend 설치

### Nginx 사용 시 (HTTPS 전용)
```bash
# Frontend 파일 압축 해제
mkdir -p /usr/share/nginx/html/tinyproxy-monitor
tar xzf frontend-dist.tar.gz -C /usr/share/nginx/html/tinyproxy-monitor/

# Nginx 설정 추가 (HTTPS 전용)
cat > /etc/nginx/conf.d/tinyproxy-monitor.conf << 'END'
# HTTP 서버 (80 포트) - HTTPS로 강제 리다이렉트
server {
    listen 80;
    listen [::]:80;
    server_name _;
    
    # 모든 HTTP 요청을 HTTPS로 강제 리다이렉트
    return 301 https://$host$request_uri;

# HTTPS 서버 (443 포트)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name _;
    
    # SSL 인증서 경로
    ssl_certificate /etc/tinyproxy-monitor/ssl/server.crt;
    ssl_certificate_key /etc/tinyproxy-monitor/ssl/server.key;
    
    # SSL 설정 (보안 강화)
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;
    
    # DH 파라미터 (있는 경우)
    # ssl_dhparam /etc/tinyproxy-monitor/ssl/dhparam.pem;
    
    # 프로토콜 및 암호화 스위트
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # HSTS (HTTPS 전용 사용 강제)
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    
    # 기타 보안 헤더
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # 웹 루트
    root /usr/share/nginx/html/tinyproxy-monitor;
    index index.html;
    
    # 정적 파일 캐싱
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location / {
        try_files $uri $uri/ /index.html;
        
        # SPA를 위한 보안 헤더
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }
    
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 프록시 타임아웃
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 타임아웃
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
END

# Nginx 설정 테스트
nginx -t

# Nginx 재시작
systemctl restart nginx
```

### Backend에서 직접 서빙 (권장하지 않음)
**보안상 HTTPS 전용 설정을 위해 Nginx 사용을 권장합니다.**

Backend 직접 서빙 시 HTTPS 설정이 복잡하므로, 프로덕션 환경에서는 Nginx를 통한 HTTPS 프록시 구성을 사용하세요.

## 테스트
- Backend API: http://localhost:8000/health (내부 통신용)
- Frontend: https://localhost/ 또는 https://서버IP/ (HTTPS 전용)
- HTTP 리다이렉트 테스트: http://서버IP/ → https://서버IP/로 자동 이동
- WebSocket 테스트: 브라우저 콘솔에서 확인 (wss:// 프로토콜 사용)

## 문제 해결

### 권한 문제
```bash
# Tinyproxy 로그 읽기 권한
setfacl -m u:운영자계정:r /var/log/tinyproxy/tinyproxy.log
```

### SELinux (Rocky Linux)
```bash
# 포트 허용
semanage port -a -t http_port_t -p tcp 8000

# 컨텍스트 설정
semanage fcontext -a -t httpd_sys_content_t "/usr/share/nginx/html/tinyproxy-monitor(/.*)?"
restorecon -Rv /usr/share/nginx/html/tinyproxy-monitor
```

### 방화벽
```bash
# HTTPS 서비스만 추가 (HTTP는 리다이렉트용으로만 사용)
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-service=http  # 리다이렉트를 위해 필요
firewall-cmd --reload

# 또는 포트로 직접 추가
firewall-cmd --permanent --add-port=80/tcp   # 리다이렉트용
firewall-cmd --permanent --add-port=443/tcp  # HTTPS 서비스용
firewall-cmd --reload

# Backend API 포트는 외부 접근 차단 (localhost만 허용)
# firewall-cmd --permanent --remove-port=8000/tcp  # 외부 접근 차단
# firewall-cmd --reload
```

### SSL 인증서 갱신 (자체 서명 인증서)
```bash
# 인증서 만료 확인
openssl x509 -in /etc/tinyproxy-monitor/ssl/server.crt -noout -dates

# 인증서 재생성
./generate-ssl-cert.sh
systemctl reload nginx
```

### 브라우저 인증서 경고 해결
자체 서명 인증서를 사용하면 브라우저에서 경고가 표시됩니다.

#### Chrome/Edge
1. 경고 화면에서 "고급" 클릭
2. "안전하지 않음으로 이동" 클릭

#### Firefox
1. "고급" 클릭
2. "위험을 감수하고 계속" 클릭

#### 영구적 해결 (권장)
```bash
# 인증서를 클라이언트 시스템에 신뢰할 수 있는 인증서로 추가
# Linux:
sudo cp /etc/tinyproxy-monitor/ssl/server.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates

# Windows: 
# server.crt 파일을 다운로드하여 "신뢰할 수 있는 루트 인증 기관"에 설치
```

### HTTPS 강제 적용 확인
```bash
# HTTP 접근 시 HTTPS로 리다이렉트되는지 확인
curl -I http://서버IP/
# 응답: HTTP/1.1 301 Moved Permanently
# Location: https://서버IP/

# HTTPS 직접 접근
curl -k https://서버IP/health
```
EOF
    
    log_info "Installation guide created: INSTALL.md"
}

# ============================================
# 8. 설치 스크립트 복사
# ============================================
copy_install_script() {
    log_info "Copying installation script..."
    
    if [ -f "${PROJECT_DIR}/proxy-monitor-install.sh" ]; then
        cp "${PROJECT_DIR}/proxy-monitor-install.sh" "${BUILD_DIR}/"
        chmod +x "${BUILD_DIR}/proxy-monitor-install.sh"
        log_info "Installation script copied: proxy-monitor-install.sh"
    else
        log_warn "Installation script not found: proxy-monitor-install.sh"
    fi
}

# ============================================
# 9. 최종 패키지 생성
# ============================================
create_final_package() {
    log_info "Creating final package..."
    
    cd "${BUILD_DIR}"
    
    # 전체 패키지 압축
    tar czf tinyproxy-monitor-offline-${VERSION}.tar.gz packages/
    
    PACKAGE_SIZE=$(du -h tinyproxy-monitor-offline-${VERSION}.tar.gz | cut -f1)
    
    log_info "Final package created: tinyproxy-monitor-offline-${VERSION}.tar.gz"
    log_info "Size: ${PACKAGE_SIZE}"
}

# ============================================
# 메인 실행
# ============================================
main() {
    log_info "========================================="
    log_info "Tinyproxy Monitor Package Builder"
    log_info "Version: ${VERSION}"
    log_info "Using modern Python packaging standards (PEP 639 compliant)"
    log_info "========================================="
    
    check_requirements
    init_directories
    create_backend_package
    download_python_deps
    include_rpm_dependencies
    build_frontend
    create_ssl_cert_script
    create_install_guide
    copy_install_script
    create_final_package
    
    log_info "========================================="
    log_info "Build Complete!"
    log_info "========================================="
    log_info ""
    log_info "Generated files in ${OUTPUT_DIR}:"
    ls -lh "${OUTPUT_DIR}/"
    log_info ""
    log_info "Final package: ${BUILD_DIR}/tinyproxy-monitor-offline-${VERSION}.tar.gz"
    log_info ""
    log_info "Package includes:"
    log_info "  - SSL certificate generation script (mandatory)"
    log_info "  - HTTPS-only configuration for Nginx"
    log_info "  - Automatic HTTP to HTTPS redirection"
    log_info "  - Enhanced security headers (HSTS enabled)"
    log_info ""
    log_info "This package uses modern Python packaging standards:"
    log_info "  - PEP 639 compliant (SPDX license expression)"
    log_info "  - No deprecated License:: classifiers"
    log_info "  - pyproject.toml with proper license metadata"
    log_info "  - python -m build for wheel generation"
    log_info "========================================="
}

# 실행
main "$@"
