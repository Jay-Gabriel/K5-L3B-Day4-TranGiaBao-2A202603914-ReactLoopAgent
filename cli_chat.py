#!/usr/bin/env python3
"""Interactive Terminal CLI Chat for Status Investigation Agent (ReAct Loop)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'evals'))

# Load environment variables from .env
env_file = ROOT / '.env'
if env_file.exists():
    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line.startswith('export '):
            line = line[7:].strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            k, v = k.strip(), v.strip().strip("'\"")
            if k and not os.environ.get(k):
                os.environ[k] = v

from agent import run_agent
from providers import Provider
from status_tools import StatusTools
from bonus.tools import BonusTools

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def main():
    print(f"{BOLD}{CYAN}================================================================={RESET}")
    print(f"{BOLD}{CYAN}🤖 STATUS INVESTIGATION AGENT · TERMINAL CHAT DEMO{RESET}")
    print(f"Học viên: {BOLD}Trần Gia Bảo{RESET} - MSSV: {BOLD}2A202603914{RESET} (K5-L3B)")
    print(f"Model: {YELLOW}{os.environ.get('MODEL', 'gemini-flash-lite-latest')}{RESET} | Provider: {YELLOW}{os.environ.get('PROVIDER', 'gemini')}{RESET}")
    print(f"{BOLD}{CYAN}================================================================={RESET}")
    print(f"{DIM}Gõ câu hỏi để trò chuyện với Agent (hoặc gõ 'exit' / 'quit' để thoát).{RESET}")
    print(f"{DIM}Ví dụ câu hỏi:{RESET}")
    print(f"  • Kiểm tra sự cố GitHub gần đây liên quan đến Actions")
    print(f"  • Incident xr3myzj7ms51 của GitHub có nguyên nhân là gì?")
    print(f"  • Cloudflare có sự cố nào trong ngày 02/11/2026 không?")
    print(f"{BOLD}{CYAN}-----------------------------------------------------------------{RESET}\n")

    provider = Provider()
    # Mặc định dùng snapshot của bài chính (an toàn, ổn định)
    tools = StatusTools(live=False)

    while True:
        try:
            query = input(f"{BOLD}{GREEN}👤 Bạn:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{YELLOW}Tạm biệt! Hẹn gặp lại.{RESET}")
            break

        if not query:
            continue
        if query.lower() in ('exit', 'quit', 'q'):
            print(f"{YELLOW}Đã thoát phiên chat.{RESET}")
            break

        if query.lower() == '/mode bonus':
            tools = BonusTools(live=False)
            print(f"{MAGENTA}[Hệ thống] Đã chuyển sang chế độ Bonus Tools (5 nền tảng).{RESET}\n")
            continue
        elif query.lower() == '/mode main':
            tools = StatusTools(live=False)
            print(f"{MAGENTA}[Hệ thống] Đã chuyển sang chế độ Main Tools (GitHub, Cloudflare).{RESET}\n")
            continue
        elif query.lower() == '/mode live':
            tools = StatusTools(live=True)
            print(f"{MAGENTA}[Hệ thống] Đã chuyển sang chế độ Live (Gọi API thật).{RESET}\n")
            continue
        elif query.lower() == '/mode snapshot':
            tools = StatusTools(live=False)
            print(f"{MAGENTA}[Hệ thống] Đã chuyển sang chế độ Snapshot dữ liệu.{RESET}\n")
            continue

        print(f"\n{DIM}⏳ Agent đang khởi động ReAct Loop...{RESET}")
        result = run_agent(query, provider, tools, max_steps=6)

        # In các bước ReAct trace
        trace = result.get('trace', [])
        tool_call_count = 0
        print(f"\n{BOLD}{MAGENTA}🔍 Quá trình ReAct Loop ({len(trace)} sự kiện):{RESET}")
        for evt in trace:
            event_type = evt.get('event')
            step = evt.get('step', '?')
            if event_type == 'call_tool':
                tool_call_count += 1
                name = evt.get('tool')
                args = evt.get('arguments', {})
                print(f"  {CYAN}[Bước {step}] Gọi Tool:{RESET} {BOLD}{name}{RESET}({args})")
            elif event_type == 'observation':
                obs_summary = evt.get('summary', '')
                obs_str = str(evt.get('observation', ''))
                if len(obs_str) > 120:
                    obs_str = obs_str[:120] + '...'
                print(f"  {DIM}[Bước {step}] Quan sát:{RESET} {obs_summary or obs_str}")
            elif event_type == 'validation_missing_source':
                print(f"  {YELLOW}[Bước {step}] Source Gate: Chưa có link URL nguồn, yêu cầu bổ sung.{RESET}")
            elif event_type == 'error':
                print(f"  \033[91m[Bước {step}] Lỗi:{RESET} {evt.get('error')}")

        # In câu trả lời cuối cùng
        answer = result.get('answer', '(Không có câu trả lời)')
        status = result.get('status')
        status_color = GREEN if status == 'completed' else YELLOW
        print(f"\n{BOLD}{CYAN}🤖 Agent ({status_color}{status}{CYAN}):{RESET}\n{answer}\n")
        print(f"{DIM}{'-' * 65}{RESET}\n")


if __name__ == '__main__':
    main()
