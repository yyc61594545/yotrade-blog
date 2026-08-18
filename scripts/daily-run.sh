#!/bin/bash
# 日更驱动：Claude 优先，Codex 兜底。
#
# 职责只有一件事：让今天的 N 篇文章以一条 */daily-YYYY-MM-DD 分支的形式推到 origin。
# 合并、部署、IndexNow 全部由 .github/workflows/daily-autopublish.yml 在 GitHub 上完成。
#
# 这么切分是因为本地唯一稳定的出网动作是 git push（走 git 自己的 http.proxy 配置）；
# gh / curl 依赖 HTTP_PROXY 环境变量，定时任务里丢过很多次。
#
# 由 ~/Library/LaunchAgents/com.ethan.yotrade-blog-daily.plist 每天 09:00 触发。

set -uo pipefail

REPO="/Users/ethan/Program/yotrade-blog"
POSTS="${POSTS:-5}"                # 可用环境变量覆盖，便于实测
AGENT_TIMEOUT=3600          # 单个 agent 最多跑 1 小时
NOTIFY="/Users/ethan/wuyun-shenghuo/happy-hellman-f65c59/scripts/notify-telegram.py"

# launchd 不继承登录 shell 的环境，代理和 PATH 必须显式给。
# 这台机器直连 DNS 不通（Tailscale DNS 超时），出网全靠 Surge 的本地代理。
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/Users/ethan/.npm-global/bin:/Users/ethan/.local/bin:$PATH"
export HOME="/Users/ethan"
export HTTP_PROXY="http://127.0.0.1:6152"
export HTTPS_PROXY="http://127.0.0.1:6152"
export NO_PROXY="localhost,127.0.0.1,::1,.local"

DATE=$(date +%F)
LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/daily-$DATE.log"
exec >>"$LOG" 2>&1

log() { echo "[$(date '+%H:%M:%S')] $*"; }

notify() {
  [ -x "$NOTIFY" ] || [ -f "$NOTIFY" ] || return 0
  [ -f "$HOME/.config/automation/credentials.env" ] && . "$HOME/.config/automation/credentials.env"
  python3 "$NOTIFY" "$1" >/dev/null 2>&1 || true
}

cd "$REPO" || { log "FATAL: 进不去 $REPO"; exit 1; }

log "===== 日更开始 $DATE ====="

# ---------- 前置同步 ----------
if ! git fetch origin --prune --quiet; then
  log "FATAL: git fetch 失败，网络或代理有问题"
  notify "❌ yotrade-blog 日更 $DATE：git fetch 失败，没开跑"
  exit 1
fi

# ---------- 幂等：今天是否已经发过 / 已经在排队 ----------
# FORCE=1 跳过幂等检查（只在人工实测时用）
if [ "${FORCE:-0}" != "1" ]; then
if git ls-remote --heads origin | grep -q "daily-$DATE\$"; then
  log "origin 上已有 daily-$DATE 分支，Actions 在处理，跳过"
  exit 0
fi
published=$(git grep -c "pubDate: '$DATE'" origin/main -- src/content/blog/ 2>/dev/null | wc -l | tr -d ' ')
if [ "${published:-0}" -ge "$POSTS" ]; then
  log "main 上今天已有 $published 篇，跳过"
  exit 0
fi
else
  log "FORCE=1，跳过幂等检查"
fi

git checkout --quiet main && git pull --quiet --ff-only || {
  log "FATAL: 切回 main / pull 失败"
  notify "❌ yotrade-blog 日更 $DATE：本地 main 同步失败"
  exit 1
}

# ---------- 把已写好的 commit 推上去 ----------
# 不管是 agent 自己推的还是它半途死了，只要有领先 origin/main 的 commit 就抢救出去。
# 返回 0 = 推送成功；1 = 没有可推的 commit；2 = 有稿子但推不上去
ensure_pushed() {
  local prefix="$1" ahead branch
  ahead=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)
  if [ "$ahead" -eq 0 ]; then
    return 1
  fi
  branch=$(git branch --show-current)
  if [ "$branch" = "main" ]; then
    branch="$prefix/daily-$DATE"
    git checkout --quiet -b "$branch" || return 2
    git branch -f main origin/main   # 本地 main 回到干净状态
  fi
  log "分支 $branch 领先 main $ahead 个 commit，推送中"
  for i in 1 2 3; do
    if git push --quiet -u origin "$branch"; then
      log "push 成功：$branch"
      return 0
    fi
    log "push 第 $i 次失败，30s 后重试"
    sleep 30
  done
  log "push 三次都失败"
  return 2
}

# ---------- agent ----------
run_claude() {
  command -v claude >/dev/null || { log "claude CLI 不在 PATH"; return 1; }
  log "尝试 Claude Code"
  timeout "$AGENT_TIMEOUT" claude -p "/daily-post $POSTS" \
    --permission-mode acceptEdits 2>&1 | tail -40
  return "${PIPESTATUS[0]}"
}

run_codex() {
  command -v codex >/dev/null || { log "codex CLI 不在 PATH"; return 1; }
  log "降级到 Codex"
  # --approve-for-me 已隐含 workspace-write，不能再传 --sandbox（会冲突报错）。
  # --cd 让工作根就是仓库，这是历史上 20 天 "Operation not permitted" 的解药。
  timeout "$AGENT_TIMEOUT" codex exec \
    --cd "$REPO" \
    --approve-for-me \
    "按 AGENTS.md 和 .claude/commands/daily-post.md 跑今天（$DATE）的日更，产出 $POSTS 篇。推送分支后即结束，不要开 PR、不要合并、不要部署。" 2>&1 | tail -40
  return "${PIPESTATUS[0]}"
}

for agent in claude codex; do
  if [ "$agent" = "claude" ]; then run_claude; rc=$?; prefix="claude"
  else                             run_codex;  rc=$?; prefix="codex"
  fi
  log "$agent 退出码 $rc"

  ensure_pushed "$prefix"; pushrc=$?
  case "$pushrc" in
    0)
      n=$(git rev-list --count origin/main..HEAD)
      log "===== 完成：$agent 写了 $n 篇，已推送，等 Actions 发布 ====="
      notify "✅ yotrade-blog 日更 $DATE：$agent 写了 $n 篇并推送，Actions 接管发布"
      exit 0
      ;;
    2)
      # 稿子在本地但推不上去。保留现场，不要换 agent 重写一遍。
      log "===== 中止：稿子已写好但推送失败，现场保留在本地分支 ====="
      notify "⚠️ yotrade-blog 日更 $DATE：$agent 写完了但 push 失败，稿子留在本地，需人工处理。日志 $LOG"
      exit 1
      ;;
    *)
      log "$agent 没产出可推送的 commit"
      # 换 agent 前把工作区弄干净，避免半成品干扰下一个
      git reset --quiet --hard origin/main
      git checkout --quiet main 2>/dev/null
      ;;
  esac
done

log "===== 失败：Claude 和 Codex 都没产出 ====="
notify "❌ yotrade-blog 日更 $DATE：Claude 和 Codex 都失败，0 篇。日志 $LOG"
exit 1
