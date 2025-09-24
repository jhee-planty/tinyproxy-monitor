#!/bin/bash
# ============================================
# Tinyproxy Monitor 오프라인 설치 스크립트
# Backend: systemd 서비스 (localhost only)
# Frontend: Nginx 서빙
# ============================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 로그 함수
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_prompt() { echo -e "${BLUE}[INPUT]${NC} $1"; }

# ============================================
# 설정 변수
# ============================================
APP_NAME="tinyproxy-monitor"
APP_USER="root"
APP_GROUP="root"
BASE_DIR="/opt/${APP_NAME}"
BACKEND_DIR="${BASE_DIR}/backend"
VENV_DIR="${BACKEND_DIR}/venv"
FRONTEND_DIR="/usr/share/nginx/html/${APP_NAME}"
LOG_DIR="/var/log/${APP_NAME}"
RUN_DIR="/var/run"
CONFIG_DIR="/etc/${APP_NAME}"

# 패키지 파일
PACKAGE_FILE="tinyproxy-monitor-offline-*.tar.gz"
EXTRACT_DIR="/tmp/${APP_NAME}-install"

# ============================================
# 1. 사전 확인
# ============================================
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Root 권한 확인
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
    
    # Python 버전 확인
    if ! python3 --version | grep -E "3\.(9|1[0-9])" > /dev/null; then
        log_error "Python 3.9+ is required"
        exit 1
    fi
    
    log_info "Prerequisites check completed"
}

# ============================================
# 2. 패키지 압축 해제
# ============================================
extract_package() {
    log_info "Extracting package..."
    
    # 임시 디렉토리 생성
    rm -rf "${EXTRACT_DIR}"
    mkdir -p "${EXTRACT_DIR}"
    
    # 압축 해제
    PACKAGE_PATH=$(ls ${PACKAGE_FILE} | head -n 1)
    tar xzf "${PACKAGE_PATH}" -C "${EXTRACT_DIR}" --strip-components=1
    
    if [ ! -d "${EXTRACT_DIR}" ]; then
        log_error "Invalid package structure"
        exit 1
    fi
    
    log_info "Package extracted to ${EXTRACT_DIR}"
}

# ============================================
# 3. Nginx 설치 (필요시)
# ============================================
install_rpms_if_needed() {  # 함수명 변경
    log_info "Installing required RPM packages..."
    
    if [ -d "${EXTRACT_DIR}/rpms" ]; then
        cd "${EXTRACT_DIR}/rpms"
        
        # 모든 RPM 설치 시도
        for rpm in *.rpm; do
            if [ -f "$rpm" ]; then
                log_info "Installing $rpm..."
                rpm -ivh "$rpm" --nodeps 2>/dev/null || true
            fi
        done
        
        # 필수 패키지 확인
        if command -v nginx &> /dev/null; then
            log_info "Nginx is available"
        else
            log_error "Nginx installation failed"
            exit 1
        fi
        
        if command -v python3.11 &> /dev/null || python3 --version | grep -E "3\.(9|1[0-9])" > /dev/null; then
            log_info "Python 3.9+ is available"
        else
            log_warn "Python 3.11 RPM installation may have failed, using system Python"
        fi
    else
        log_error "RPM packages directory not found"
        exit 1
    fi
}

# ============================================
# 4. 사용자 및 디렉토리 생성
# ============================================
create_user_and_directories() {
    log_info "Creating user and directories..."
    
    # 사용자 생성
    if ! id "${APP_USER}" &>/dev/null; then
        useradd -r -s /bin/bash -m -d "/home/${APP_USER}" "${APP_USER}"
        log_info "User ${APP_USER} created"
    fi
    
    # 디렉토리 생성
    mkdir -p "${BASE_DIR}"
    mkdir -p "${BACKEND_DIR}"
    mkdir -p "${FRONTEND_DIR}"
    mkdir -p "${LOG_DIR}"
    mkdir -p "${RUN_DIR}"
    mkdir -p "${CONFIG_DIR}"
    
    # 권한 설정
    chown -R "${APP_USER}:${APP_GROUP}" "${BASE_DIR}"
    chown -R "${APP_USER}:${APP_GROUP}" "${LOG_DIR}"
    chown -R "${APP_USER}:${APP_GROUP}" "${RUN_DIR}"
    chown -R root:root "${CONFIG_DIR}"
    chmod 755 "${CONFIG_DIR}"
    
    log_info "Directories created"
}

# ============================================
# 5. Backend 설치
# ============================================
install_backend() {
    log_info "Installing backend..."
    
    cd "${EXTRACT_DIR}"
    
    # Python 가상환경 생성
    log_info "Creating Python virtual environment..."
    sudo -u "${APP_USER}" python3 -m venv "${VENV_DIR}"
    
    # 의존성 압축 해제
    tar xzf python-deps.tar.gz
    
    # pip 업그레이드
    log_info "Upgrading pip and build tools..."
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install \
        --no-index \
        --find-links python-deps/ \
        pip setuptools wheel build
    
    # 의존성 설치
    log_info "Installing Python dependencies..."
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install \
        --no-index \
        --find-links python-deps/ \
        fastapi uvicorn[standard] psutil python-dotenv \
        websockets aiofiles httpx numpy beautifulsoup4 \
        watchdog python-jose[cryptography] python-multipart \
        passlib[bcrypt] python-pam gunicorn
    
    # Backend 패키지 설치
    log_info "Installing backend package..."
    WHEEL_FILE=$(ls tinyproxy_monitor-*.whl | head -n 1)
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install \
        --no-index \
        --find-links . \
        "${WHEEL_FILE}"
    
    # app 디렉토리 복사 (wheel에 포함되지 않은 경우를 위해)
    if [ ! -d "${BACKEND_DIR}/app" ]; then
        # wheel에서 설치된 위치 찾기
        SITE_PACKAGES="${VENV_DIR}/lib/python*/site-packages"
        if [ -d ${SITE_PACKAGES}/app ]; then
            cp -r ${SITE_PACKAGES}/app "${BACKEND_DIR}/"
            chown -R "${APP_USER}:${APP_GROUP}" "${BACKEND_DIR}/app"
        fi
    fi
    
    log_info "Backend installed"
}

# ============================================
# 6. Frontend 설치
# ============================================
install_frontend() {
    log_info "Installing frontend..."
    
    cd "${EXTRACT_DIR}"
    
    # Frontend 파일 압축 해제
    tar xzf frontend-dist.tar.gz -C "${FRONTEND_DIR}/"
    
    # 권한 설정
    chown -R root:root "${FRONTEND_DIR}"
    chmod -R 755 "${FRONTEND_DIR}"
    
    log_info "Frontend installed to ${FRONTEND_DIR}"
}

# ============================================
# 7. SSL 인증서 자동 생성
# ============================================
generate_ssl_certificate() {
    log_info "Generating SSL certificate for HTTPS..."
    
    # generate-ssl-cert.sh 스크립트 확인
    if [ -f "${EXTRACT_DIR}/generate-ssl-cert.sh" ]; then
        # 스크립트 실행 권한 부여
        chmod +x "${EXTRACT_DIR}/generate-ssl-cert.sh"
        
        # SSL 인증서 자동 생성
        if "${EXTRACT_DIR}/generate-ssl-cert.sh"; then
            log_info "SSL certificate generated successfully"
        else
            log_error "SSL certificate generation failed"
            exit 1
        fi
    else
        log_error "SSL certificate generation script not found"
        exit 1
    fi
    
    # 인증서 파일 확인
    SSL_DIR="/etc/tinyproxy-monitor/ssl"
    if [ -f "${SSL_DIR}/server.crt" ] && [ -f "${SSL_DIR}/server.key" ]; then
        log_info "SSL certificates verified at ${SSL_DIR}"
    else
        log_error "SSL certificates not found at ${SSL_DIR}"
        exit 1
    fi
}

# ============================================
# 8. 환경 설정 파일 생성
# ============================================
create_configuration() {
    log_info "Creating configuration files..."
    
    # 비밀번호 생성
    ADMIN_PASSWORD=$(openssl rand -base64 12)
    SECRET_KEY=$(openssl rand -hex 32)
    
    # Backend .env 파일 생성
    cat > "${BACKEND_DIR}/.env" << EOF
# Tinyproxy Monitor Configuration
# Generated: $(date)

# Tinyproxy 경로
PROXY_LOG_PATH=/var/log/tinyproxy/tinyproxy.log
PROXY_PID_PATH=/var/run/tinyproxy.pid
PROXY_STATS_HOST=localhost:3128
PROXY_STATS_HOSTNAME=tinyproxy.stats
PROXY_SERVICE_NAME=tinyproxy

# API 서버 설정 (localhost only)
API_HOST=127.0.0.1
API_PORT=8000

# CORS 설정 (Nginx reverse proxy)
CORS_ORIGINS=http://localhost,http://127.0.0.1

# 인증 설정
DISABLE_AUTH=false
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=720
BLOCKED_USERS=root

# 관리자 계정
ADMIN_USERNAME=admin
ADMIN_PASSWORD=${ADMIN_PASSWORD}

# WebSocket 설정
WS_MAX_MEMORY_PERCENT=5.0
WS_DEFAULT_BATCH_SIZE=100
WS_CONNECTION_TIMEOUT=30

# 로그 설정
LOG_AVG_LINE_SIZE=200
LOG_MAX_TAIL_LINES=1000
LOG_LEVEL=info
EOF
    
    chown "${APP_USER}:${APP_GROUP}" "${BACKEND_DIR}/.env"
    chmod 600 "${BACKEND_DIR}/.env"
    
}

# ============================================
# 9. backend 로그 설정 파일 생성
# ============================================
create_backend_log_info() {
    log_info "Creating backend log info file..."

    cat > "${BACKEND_DIR}/app/logging_config.ini" << EOF
[loggers]
keys=root

[handlers]
keys=console,timedFile

[formatters]
keys=generic

[logger_root]
level=INFO
handlers=console,timedFile

[handler_console]
class=StreamHandler
level=INFO
formatter=generic
args=(sys.stderr,)

[handler_timedFile]
class=logging.handlers.TimedRotatingFileHandler
level=INFO
formatter=generic
args=('${LOG_DIR}/backend.log', 'midnight', 1, 365, 'utf-8')

[formatter_generic]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s

EOF

}

# ============================================
# 10. Systemd 서비스 생성
# ============================================
create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > "/lib/systemd/system/${APP_NAME}.service" << EOF
[Unit]
Description=Tinyproxy Monitor Backend API
After=network.target tinyproxy.service
Wants=network-online.target

[Service]
Type=exec
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${BACKEND_DIR}

# 환경 변수
Environment="PATH=${VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=${BACKEND_DIR}"
EnvironmentFile=-${BACKEND_DIR}/.env

# 실행 명령 (localhost only binding)
ExecStart=${VENV_DIR}/bin/uvicorn app.main:app \\
    --host 127.0.0.1 \\
    --port 8000 \\
    --workers 1 \\
    --log-level info \\
    --access-log \\
    --log-config ${BACKEND_DIR}/app/logging_config.ini

# 재시작 정책
Restart=always
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

# 로깅
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${APP_NAME}

# 리소스 제한
LimitNOFILE=65536
LimitNPROC=4096

# 보안 설정
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true

# 네트워크 격리 (localhost only)
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
IPAddressAllow=127.0.0.1/8 ::1/128
IPAddressDeny=any

# 쓰기 가능 경로
ReadWritePaths=${LOG_DIR} ${RUN_DIR} ${BACKEND_DIR} /var/log/tinyproxy

[Install]
WantedBy=multi-user.target

EOF
    
    systemctl daemon-reload
    systemctl enable "${APP_NAME}.service"
    
    log_info "Systemd service created and enabled"
}

# ============================================
# 11. Nginx 설정 (HTTPS 전용)
# ============================================
configure_nginx() {
    log_info "Configuring Nginx for HTTPS..."
    
    # 기존 default 설정 백업
    if [ -f /etc/nginx/conf.d/default.conf ]; then
        mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak
    fi
    
    # Tinyproxy Monitor Nginx 설정 (HTTPS 전용)
    cat > "/etc/nginx/conf.d/${APP_NAME}.conf" << 'EOF'
# Tinyproxy Monitor Nginx Configuration (HTTPS-Only)

upstream tinyproxy_monitor_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# HTTP 서버 (80 포트) - HTTPS로 강제 리다이렉트
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    
    # 모든 HTTP 요청을 HTTPS로 강제 리다이렉트
    return 301 https://$host$request_uri;
}

# HTTPS 서버 (443 포트)
server {
    listen 443 ssl http2 default_server;
    listen [::]:443 ssl http2 default_server;
    server_name _;
    
    # SSL 인증서 경로
    ssl_certificate /etc/tinyproxy-monitor/ssl/server.crt;
    ssl_certificate_key /etc/tinyproxy-monitor/ssl/server.key;
    
    # SSL 설정 (보안 강화)
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;
    
    # DH 파라미터 (있는 경우)
    ssl_dhparam /etc/tinyproxy-monitor/ssl/dhparam.pem;
    
    # 프로토콜 및 암호화 스위트
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # HSTS (HTTPS 전용 사용 강제)
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    
    # 보안 헤더
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Frontend 루트 디렉토리
    root /usr/share/nginx/html/tinyproxy-monitor;
    index index.html;
    
    # 헬스체크 엔드포인트 (먼저 정의)
    location = /health {
        proxy_pass http://tinyproxy_monitor_backend/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Connection "";
        access_log off;
    }
    
    location = /api/health {
        proxy_pass http://tinyproxy_monitor_backend/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Connection "";
        access_log off;
    }
    
    # Backend API reverse proxy
    location /api/ {
        proxy_pass http://tinyproxy_monitor_backend/api/;
        proxy_http_version 1.1;
        
        # 헤더 설정
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port 443;
        
        # 연결 유지
        proxy_set_header Connection "";
        
        # 타임아웃 설정
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 버퍼 설정
        proxy_buffering off;
        proxy_request_buffering off;
        
        # 리다이렉트 처리
        proxy_redirect http://127.0.0.1:8000/ https://$host/;
    }
    
    # WebSocket reverse proxy
    location /ws {
        proxy_pass http://tinyproxy_monitor_backend/ws;
        proxy_http_version 1.1;
        
        # WebSocket 업그레이드
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 헤더 설정
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        
        # 타임아웃 설정 (WebSocket용으로 길게)
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
    
    # 정적 자산 캐싱
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Frontend (SPA 라우팅) - 가장 마지막에 정의
    location / {
        try_files $uri $uri/ /index.html;
        
        # SPA를 위한 캐시 제어
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }
    
    # 로그 설정
    access_log /var/log/nginx/tinyproxy-monitor-access.log;
    error_log /var/log/nginx/tinyproxy-monitor-error.log;
}
EOF
    
    # Nginx 설정 테스트
    nginx -t
    
    # Nginx 서비스 활성화 및 재시작
    systemctl enable nginx
    systemctl restart nginx
    
    log_info "Nginx configured for HTTPS and restarted"
}

# ============================================
# 12. SELinux 설정 (RHEL/Rocky Linux)
# ============================================
configure_selinux() {
    if command -v getenforce &> /dev/null && [ "$(getenforce)" != "Disabled" ]; then
        log_info "Configuring SELinux..."
        
        # httpd_can_network_connect 활성화 (Nginx가 Backend와 통신)
        setsebool -P httpd_can_network_connect 1
        
        # Frontend 디렉토리 컨텍스트 설정
        semanage fcontext -a -t httpd_sys_content_t "${FRONTEND_DIR}(/.*)?" 2>/dev/null || true
        restorecon -Rv "${FRONTEND_DIR}"
        
        # 로그 디렉토리 컨텍스트
        semanage fcontext -a -t httpd_log_t "${LOG_DIR}(/.*)?" 2>/dev/null || true
        restorecon -Rv "${LOG_DIR}"
        
        log_info "SELinux configured"
    fi
}

# ============================================
# 13. 로그 로테이션 설정
# ============================================
configure_log_rotation() {
    log_info "Configuring log rotation..."
    
    cat > "/etc/logrotate.d/${APP_NAME}" << EOF
${LOG_DIR}/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 ${APP_USER} ${APP_GROUP}
    sharedscripts
    postrotate
        systemctl restart ${APP_NAME} >/dev/null 2>&1 || true
    endscript
}

/var/log/nginx/tinyproxy-monitor-*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 nginx nginx
    sharedscripts
    postrotate
        nginx -s reload >/dev/null 2>&1 || true
    endscript
}
EOF
    
    log_info "Log rotation configured"
}

# ============================================
# 14. Tinyproxy 로그 접근 권한 설정
# ============================================
configure_tinyproxy_access() {
    log_info "Configuring Tinyproxy log access..."
    
    # ACL 설정으로 읽기 권한 부여
    if [ -f /var/log/tinyproxy/tinyproxy.log ]; then
        setfacl -m u:${APP_USER}:r /var/log/tinyproxy/tinyproxy.log
        setfacl -d -m u:${APP_USER}:r /var/log/tinyproxy/
    else
        log_warn "Tinyproxy log file not found. Please ensure Tinyproxy is installed and configured."
    fi
    
    # PID 파일 읽기 권한
    if [ -f /var/run/tinyproxy/tinyproxy.pid ]; then
        setfacl -m u:${APP_USER}:r /var/run/tinyproxy/tinyproxy.pid
    fi
}

# ============================================
# 15. 서비스 시작
# ============================================
start_services() {
    log_info "Starting services..."
    
    # Backend 서비스 시작
    systemctl start "${APP_NAME}.service"
    sleep 3
    
    if systemctl is-active --quiet "${APP_NAME}.service"; then
        log_info "Backend service started successfully"
    else
        log_error "Backend service failed to start"
        journalctl -u "${APP_NAME}.service" -n 50 --no-pager
        exit 1
    fi
    
    # Nginx 상태 확인
    if systemctl is-active --quiet nginx; then
        log_info "Nginx is running"
    else
        log_error "Nginx is not running"
        systemctl status nginx --no-pager
        exit 1
    fi
}

# ============================================
# 16. 설치 검증
# ============================================
verify_installation() {
    log_info "Verifying installation..."
    
    local SERVER_IP=$(hostname -I | awk '{print $1}')
    
    # Backend 헬스체크 (localhost)
    if curl -fs http://127.0.0.1:8000/health > /dev/null 2>&1; then
        log_info "✓ Backend API is responding"
    else
        log_error "✗ Backend API is not responding"
    fi
    
    # HTTPS 접근 테스트 (자체 서명 인증서 무시)
    if curl -kfs https://localhost/ > /dev/null 2>&1; then
        log_info "✓ Frontend is accessible via HTTPS"
    else
        log_error "✗ Frontend is not accessible via HTTPS"
    fi
    
    # HTTP에서 HTTPS로 리다이렉트 테스트
    REDIRECT_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/)
    if [ "$REDIRECT_CODE" = "301" ]; then
        log_info "✓ HTTP to HTTPS redirect is working"
    else
        log_warn "⚠ HTTP to HTTPS redirect may not be working (code: $REDIRECT_CODE)"
    fi
    
    # API reverse proxy 테스트 (HTTPS)
    if curl -kfs https://localhost/api/health > /dev/null 2>&1; then
        log_info "✓ API reverse proxy is working over HTTPS"
    else
        log_error "✗ API reverse proxy is not working over HTTPS"
    fi
    
    # 외부 접근 차단 확인 (실제로는 연결되지 않아야 함)
    if timeout 2 curl -fs http://${SERVER_IP}:8000/health > /dev/null 2>&1; then
        log_warn "⚠ Backend is accessible externally! Please check firewall settings."
    else
        log_info "✓ Backend is not accessible externally (good)"
    fi
}

# ============================================
# 17. 설치 완료 메시지
# ============================================
print_completion_message() {
    local SERVER_IP=$(hostname -I | awk '{print $1}')
    
    # 관리자 정보 저장
    cat > "${CONFIG_DIR}/admin.info" << EOF
========================================
Tinyproxy Monitor Admin Credentials
========================================
URL (HTTPS): https://${SERVER_IP}/
Username: admin
Password: ${ADMIN_PASSWORD}
========================================
SSL Certificate: Self-signed (RSA 2048)
Certificate Location: /etc/tinyproxy-monitor/ssl/
========================================
EOF
    
    chmod 600 "${CONFIG_DIR}/admin.info"
    
    echo ""
    log_info "========================================="
    log_info "Installation Complete!"
    log_info "========================================="
    log_info ""
    log_info "Service Status:"
    log_info "  Backend: systemctl status ${APP_NAME}"
    log_info "  Frontend: systemctl status nginx"
    log_info ""
    log_info "Access Information:"
    log_info "  URL: https://${SERVER_IP}/ (HTTPS Only)"
    log_info "  Credentials: cat ${CONFIG_DIR}/admin.info"
    log_info ""
    log_warn "Note: Using self-signed certificate."
    log_warn "Browser will show security warning on first access."
    log_info ""
    log_info "SSL Certificate Location:"
    log_info "  /etc/tinyproxy-monitor/ssl/server.crt"
    log_info "  /etc/tinyproxy-monitor/ssl/server.key"
    log_info ""
    log_info "Log Files:"
    log_info "  Backend: journalctl -u ${APP_NAME} -f"
    log_info "  Nginx Access: tail -f /var/log/nginx/tinyproxy-monitor-access.log"
    log_info "  Nginx Error: tail -f /var/log/nginx/tinyproxy-monitor-error.log"
    log_info ""
    log_info "Configuration Files:"
    log_info "  Backend: ${BACKEND_DIR}/.env"
    log_info "  Nginx: /etc/nginx/conf.d/${APP_NAME}.conf"
    log_info ""
    log_info "Service Management:"
    log_info "  Restart Backend: systemctl restart ${APP_NAME}"
    log_info "  Restart Nginx: systemctl restart nginx"
    log_info "  View Logs: journalctl -u ${APP_NAME} -f"
    log_info "========================================="
}

# ============================================
# 18. 정리 작업
# ============================================
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "${EXTRACT_DIR}"
    log_info "Cleanup completed"
}

# ============================================
# 메인 실행
# ============================================
main() {
    log_info "========================================="
    log_info "Tinyproxy Monitor Offline Installation"
    log_info "========================================="
    
    # 설치 단계 실행
    check_prerequisites
    extract_package
    install_rpms_if_needed
    create_user_and_directories
    install_backend
    install_frontend
    generate_ssl_certificate  # SSL 인증서 자동 생성
    create_configuration
    create_backend_log_info
    create_systemd_service
    configure_nginx
    #configure_selinux
    configure_log_rotation
    configure_tinyproxy_access
    start_services
    verify_installation
    print_completion_message
    cleanup
    
    log_info "Installation script completed successfully!"
}

# 트랩 설정 (에러 발생 시 정리)
trap 'log_error "Installation failed!"; cleanup; exit 1' ERR

# 스크립트 실행
main "$@"