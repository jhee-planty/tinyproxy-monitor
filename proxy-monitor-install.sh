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
APP_USER="tinyproxy-monitor"
APP_GROUP="tinyproxy-monitor"
BASE_DIR="/opt/${APP_NAME}"
BACKEND_DIR="${BASE_DIR}/backend"
VENV_DIR="${BACKEND_DIR}/venv"
FRONTEND_DIR="/usr/share/nginx/html/${APP_NAME}"
LOG_DIR="/var/log/${APP_NAME}"
RUN_DIR="/var/run/${APP_NAME}"
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
    
    # Nginx 확인
    if ! command -v nginx &> /dev/null; then
        log_warn "Nginx is not installed. Installing from RPM packages if available..."
        INSTALL_NGINX=true
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
install_nginx_if_needed() {
    if [ "${INSTALL_NGINX}" = "true" ]; then
        log_info "Installing Nginx from RPM packages..."
        
        if [ -d "${EXTRACT_DIR}/rpms" ]; then
            cd "${EXTRACT_DIR}/rpms"
            
            # 의존성 순서대로 설치
            for rpm in pcre2-*.rpm openssl-libs-*.rpm nginx-filesystem-*.rpm nginx-*.rpm; do
                if ls $rpm 1> /dev/null 2>&1; then
                    rpm -ivh $rpm --nodeps 2>/dev/null || true
                fi
            done
            
            if command -v nginx &> /dev/null; then
                log_info "Nginx installed successfully"
            else
                log_error "Failed to install Nginx"
                exit 1
            fi
        else
            log_error "RPM packages not found in package"
            exit 1
        fi
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
# 7. 환경 설정 파일 생성
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
    
    # 관리자 정보 저장
    cat > "${CONFIG_DIR}/admin.info" << EOF
========================================
Tinyproxy Monitor Admin Credentials
========================================
URL: http://$(hostname -I | awk '{print $1}')/
Username: admin
Password: ${ADMIN_PASSWORD}
========================================
Generated: $(date)
========================================
EOF
    
    chmod 600 "${CONFIG_DIR}/admin.info"
    
    log_warn "Admin credentials saved to: ${CONFIG_DIR}/admin.info"
}

# ============================================
# 8. backend 로그 설정 파일 생성
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
# 9. Systemd 서비스 생성
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
ReadWritePaths=${LOG_DIR} ${RUN_DIR} ${BACKEND_DIR} /var/log/tinyproxy /var/run/tinyproxy

[Install]
WantedBy=multi-user.target

EOF
    
    systemctl daemon-reload
    systemctl enable "${APP_NAME}.service"
    
    log_info "Systemd service created and enabled"
}

# ============================================
# 10. Nginx 설정
# ============================================
configure_nginx() {
    log_info "Configuring Nginx..."
    
    # 기존 default 설정 백업
    if [ -f /etc/nginx/conf.d/default.conf ]; then
        mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak
    fi
    
    # Tinyproxy Monitor Nginx 설정
    cat > "/etc/nginx/conf.d/${APP_NAME}.conf" << 'EOF'
# Tinyproxy Monitor Nginx Configuration

upstream tinyproxy_monitor_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80 default_server;
    listen [::]:80 default_server;
    
    # server_name 지시자를 생략하거나 빈 문자열 사용
    # 이렇게 하면 모든 요청을 받지만 충돌 경고는 없음
    server_name "";
    
    # Frontend 루트 디렉토리
    root /usr/share/nginx/html/tinyproxy-monitor;
    index index.html;
    
    # 보안 헤더
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Frontend (SPA 라우팅)
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Backend API reverse proxy
    location /api {
        proxy_pass http://tinyproxy_monitor_backend;
        proxy_http_version 1.1;
        
        # 헤더 설정
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 연결 유지
        proxy_set_header Connection "";
        
        # 타임아웃 설정
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 버퍼 설정
        proxy_buffering off;
        proxy_request_buffering off;
    }
    
    # WebSocket reverse proxy
    location /ws {
        proxy_pass http://tinyproxy_monitor_backend;
        proxy_http_version 1.1;
        
        # WebSocket 업그레이드
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 헤더 설정
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 타임아웃 설정 (WebSocket용으로 길게)
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
    
    # 헬스체크 엔드포인트
    location /health {
        proxy_pass http://tinyproxy_monitor_backend/health;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        access_log off;
    }
    
    # 정적 자산 캐싱
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
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
    
    log_info "Nginx configured and restarted"
}

# ============================================
# 11. SELinux 설정 (RHEL/Rocky Linux)
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
# 12. 로그 로테이션 설정
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
# 13. Tinyproxy 로그 접근 권한 설정
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
# 14. 서비스 시작
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
# 15. 설치 검증
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
    
    # Frontend 접근 테스트 (Nginx)
    if curl -fs http://localhost/ > /dev/null 2>&1; then
        log_info "✓ Frontend is accessible via Nginx"
    else
        log_error "✗ Frontend is not accessible"
    fi
    
    # API reverse proxy 테스트
    if curl -fs http://localhost/api/health > /dev/null 2>&1; then
        log_info "✓ API reverse proxy is working"
    else
        log_error "✗ API reverse proxy is not working"
    fi
    
    # 외부 접근 차단 확인 (실제로는 연결되지 않아야 함)
    if timeout 2 curl -fs http://${SERVER_IP}:8000/health > /dev/null 2>&1; then
        log_warn "⚠ Backend is accessible externally! Please check firewall settings."
    else
        log_info "✓ Backend is not accessible externally (good)"
    fi
}

# ============================================
# 16. 설치 완료 메시지
# ============================================
print_completion_message() {
    local SERVER_IP=$(hostname -I | awk '{print $1}')
    
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
    log_info "  URL: http://${SERVER_IP}/"
    log_info "  Credentials: cat ${CONFIG_DIR}/admin.info"
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
# 17. 정리 작업
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
    install_nginx_if_needed
    create_user_and_directories
    install_backend
    install_frontend
    create_configuration
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