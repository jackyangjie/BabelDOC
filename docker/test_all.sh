#!/bin/bash
# BabelDOC 容器内测试脚本
# 遍历 /testdata 下所有 PDF/DOCX/PPT(X) 文件进行翻译测试

set -euo pipefail

OPENAI_MODEL="${OPENAI_MODEL:-trs-m5}"
OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://192.168.5.82:23000/api/v1}"
OPENAI_API_KEY="${OPENAI_API_KEY:?环境变量 OPENAI_API_KEY 未设置}"
OUTDIR="${OUTDIR:-/testdata}"

PASS=0
FAIL=0
FAILED_FILES=()

log_info()  { printf "\e[34m[INFO]\e[0m  %s\n" "$*"; }
log_pass() { printf "\e[32m[PASS]\e[0m  %s\n" "$*"; }
log_fail() { printf "\e[31m[FAIL]\e[0m  %s\n" "$*"; }

run_test() {
    local file="$1"
    local ext="${file##*.}"
    local basename
    basename="$(basename "$file")"

    log_info "Testing: $basename"

    # 对 .ppt 文件设置较长时间，因为需 LibreOffice 转换
    local timeout_sec=300
    case "$ext" in
        ppt)    timeout_sec=600 ;;
        pptx)   timeout_sec=300 ;;
        pdf)    timeout_sec=600 ;;
        docx)   timeout_sec=300 ;;
        doc)    timeout_sec=300 ;;
    esac

    if timeout "$timeout_sec" babeldoc \
        --files "$file" \
        --output "$OUTDIR" \
        --openai \
        --openai-model "$OPENAI_MODEL" \
        --openai-base-url "$OPENAI_BASE_URL" \
        --openai-api-key "$OPENAI_API_KEY" \
        2>&1; then
        log_pass "$basename"
        PASS=$((PASS + 1))
    else
        log_fail "$basename (exit code $?)"
        FAIL=$((FAIL + 1))
        FAILED_FILES+=("$basename")
    fi
}

main() {
    log_info "=========================================="
    log_info "BabelDOC 容器内测试"
    log_info "Model: $OPENAI_MODEL"
    log_info "Base:  $OPENAI_BASE_URL"
    log_info "Files: $(ls /testdata/*.pdf /testdata/*.docx /testdata/*.ppt /testdata/*.pptx 2>/dev/null | wc -l)"
    log_info "=========================================="
    echo

    # 遍历所有支持的文件
    for file in /testdata/*.pdf /testdata/*.docx /testdata/*.doc /testdata/*.ppt /testdata/*.pptx; do
        [ -f "$file" ] || continue
        run_test "$file"
        echo
    done

    echo
    log_info "=========================================="
    log_info "结果汇总: $PASS 通过, $FAIL 失败"
    if [ "$FAIL" -gt 0 ]; then
        log_info "失败文件:"
        for f in "${FAILED_FILES[@]}"; do
            log_fail "  - $f"
        done
    fi
    log_info "=========================================="

    # 列出所有输出文件
    echo
    log_info "输出文件:"
    ls -lh "$OUTDIR"/*.mono.* "$OUTDIR"/*.dual.* "$OUTDIR"/*_translated.* "$OUTDIR"/*_dual.* 2>/dev/null || echo "(none yet)"

    return "$FAIL"
}

main
