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

    # run_server 함수 추가 (console script용)
    if ! grep -q "def run_server" app/main.py; then
        echo "" >> app/main.py
        cat >> app/main.py << 'EOF'

def run_server():
    """Entry point for console script"""
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )

if __name__ == "__main__":
    run_server()
EOF
    fi
    
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
# 6. 설치 가이드 생성
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


## Frontend 설치

### Nginx 사용 시
```bash
# Frontend 파일 압축 해제
mkdir -p /usr/share/nginx/html/tinyproxy-monitor
tar xzf frontend-dist.tar.gz -C /usr/share/nginx/html/tinyproxy-monitor/

# Nginx 설정 추가
cat > /etc/nginx/conf.d/tinyproxy-monitor.conf << 'END'
server {
    listen 80;
    server_name _;
    
    root /usr/share/nginx/html/tinyproxy-monitor;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
END

# Nginx 재시작
systemctl restart nginx
```

### 또는 Backend에서 직접 서빙
Backend의 main.py에 다음 코드 추가:
```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Frontend 정적 파일 서빙
frontend_path = Path("/opt/tinyproxy-monitor/frontend")
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="static")
```

## 테스트
- Backend API: http://localhost:8000/health
- Frontend: http://localhost/ (Nginx) 또는 http://localhost:8000/ (Backend 서빙)

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
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --permanent --add-service=http
firewall-cmd --reload
```
EOF
    
    log_info "Installation guide created: INSTALL.md"
}

# ============================================
# 7. 설치 스크립트 복사
# ============================================
copy_install_script() {
    log_info "Copying installation script..."
    
    cp "${PROJECT_DIR}/proxy-monitor-install.sh" "${OUTPUT_DIR}/"
    chmod +x "${OUTPUT_DIR}/proxy-monitor-install.sh"
    
    log_info "Installation script copied: proxy-monitor-install.sh"
}

# ============================================
# 8. 최종 패키지 생성
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
    log_info "This package uses modern Python packaging standards:"
    log_info "  - PEP 639 compliant (SPDX license expression)"
    log_info "  - No deprecated License:: classifiers"
    log_info "  - pyproject.toml with proper license metadata"
    log_info "  - python -m build for wheel generation"
    log_info "========================================="
}

# 실행
main "$@"
