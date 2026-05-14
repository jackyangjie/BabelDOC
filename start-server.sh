#!/usr/bin/env bash
set -euo pipefail

# ============================================
# BabelDOC HTTP API 服务启动脚本
# ============================================

# --- 配置项（按需修改）---
HOST="0.0.0.0"
PORT="7860"
WORKROOT="$(pwd)/workroot"
LOG_FILE="$(pwd)/babeldoc-server.log"
PID_FILE="$(pwd)/babeldoc-server.pid"

# --- 颜色输出 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -d, --daemon     后台运行（守护进程模式）"
    echo "  -s, --stop       停止后台服务"
    echo "  -v, --view       查看后台日志"
    echo "  -h, --help       显示此帮助"
    exit 0
}

# --- 停止服务 ---
stop_service() {
    if [ ! -f "$PID_FILE" ]; then
        log_error "PID 文件不存在，服务未运行？"
        exit 1
    fi
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        log_info "正在停止服务 (PID: $PID) ..."
        kill "$PID" 2>/dev/null || true
        sleep 1
        if kill -0 "$PID" 2>/dev/null; then
            log_warn "服务未响应，强制停止..."
            kill -9 "$PID" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
        log_info "服务已停止"
    else
        log_error "进程 $PID 不存在，可能已经停止"
        rm -f "$PID_FILE"
    fi
    exit 0
}

# --- 查看日志 ---
view_log() {
    if [ ! -f "$LOG_FILE" ]; then
        log_error "日志文件不存在: $LOG_FILE"
        exit 1
    fi
    tail -f "$LOG_FILE"
}

# --- 解析参数 ---
DAEMON=false
case "${1:-}" in
    -d|--daemon)
        DAEMON=true
        ;;
    -s|--stop)
        stop_service
        ;;
    -v|--view)
        view_log
        ;;
    -h|--help)
        usage
        ;;
    "")
        # 前台运行
        ;;
    *)
        log_error "未知参数: $1"
        usage
        ;;
esac

# --- 检查 Python 环境 ---
if ! command -v uv &>/dev/null; then
    log_error "未找到 uv 命令，请先安装: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# --- 创建工作根目录 ---
if [ ! -d "$WORKROOT" ]; then
    mkdir -p "$WORKROOT"
    log_info "创建工作根目录: $WORKROOT"
fi

# --- 创建 .executor-workroot-ready 标记文件 ---
touch "$WORKROOT/.executor-workroot-ready"
chmod 644 "$WORKROOT/.executor-workroot-ready"

# --- 检查示例目录 ---
EXAMPLES_DIR="$WORKROOT/docs"
if [ ! -d "$EXAMPLES_DIR" ]; then
    mkdir -p "$EXAMPLES_DIR"
    log_warn "请将待翻译的 PDF 放入: $EXAMPLES_DIR"
fi

# --- 导出环境变量 ---
export BABELDOC_EXECUTOR_WORKROOT="$WORKROOT"

# --- 显示启动信息 ---
echo ""
log_info "=================================="
log_info " BabelDOC HTTP API 服务"
log_info "=================================="
echo ""
log_info "工作根目录: $WORKROOT"
log_info "监听地址:   $HOST:$PORT"
log_info "日志文件:   $LOG_FILE"
log_info "健康检查:   curl http://$HOST:$PORT/healthz"
log_info "上传 PDF 到: $EXAMPLES_DIR/"
echo ""

RUN_CMD="uv run python -m babeldoc.tools.executor --host $HOST --port $PORT --runner babeldoc"

if [ "$DAEMON" = true ]; then
    # --- 后台运行 ---
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        log_error "服务已在运行 (PID: $(cat "$PID_FILE"))"
        log_info "使用 $0 -s 停止，或 $0 -v 查看日志"
        exit 1
    fi

    nohup $RUN_CMD > "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"

    sleep 1
    if kill -0 "$PID" 2>/dev/null; then
        log_info "服务已后台启动 (PID: $PID)"
        log_info "日志文件: $LOG_FILE"
        log_info "查看日志: $0 -v"
        log_info "停止服务: $0 -s"
    else
        log_error "服务启动失败，请检查日志: $LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
else
    # --- 前台运行 ---
    exec $RUN_CMD 2>&1 | tee "$LOG_FILE"
fi
