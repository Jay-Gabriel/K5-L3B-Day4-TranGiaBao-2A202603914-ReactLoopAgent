#!/usr/bin/env python3
"""Giao diện Chat AI tương tác: Status Investigation Agent (ReAct Loop).
Giao diện chuẩn phong cách ChatGPT / Gemini / Claude Chat UI hiện đại.
"""
import http.server
import json
import os
from pathlib import Path
import sys
import urllib.parse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'evals'))

# Tự động nạp biến môi trường từ .env nếu chưa có
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

CHAT_HTML = r'''<!DOCTYPE html>
<html lang="vi" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Status Investigation Assistant · AI Chat Agent</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        chatbg: '#0f172a',
                        sidebarbg: '#0b1120',
                        msgbot: '#1e293b',
                        msguser: '#3b82f6',
                        inputbg: '#1e293b',
                        borderbg: '#334155'
                    }
                }
            }
        }
    </script>
    <style>
        .prose pre { background: #0b0f19; border: 1px solid #334155; border-radius: 8px; padding: 12px; margin: 8px 0; }
        .prose a { color: #60a5fa; text-decoration: underline; }
        .prose ul { list-style-type: disc; padding-left: 20px; margin: 6px 0; }
        .prose ol { list-style-type: decimal; padding-left: 20px; margin: 6px 0; }
        .prose p { margin-bottom: 8px; }
        .chat-scroll::-webkit-scrollbar { width: 6px; }
        .chat-scroll::-webkit-scrollbar-track { background: transparent; }
        .chat-scroll::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
    </style>
</head>
<body class="bg-chatbg text-slate-100 min-h-screen flex font-sans overflow-hidden">

    <!-- Sidebar (Left) -->
    <aside class="w-72 bg-sidebarbg border-r border-borderbg flex flex-col justify-between hidden md:flex shrink-0">
        <div class="p-4 space-y-4">
            <!-- App Brand -->
            <div class="flex items-center space-x-3 pb-3 border-b border-borderbg">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
                    <i class="fa-solid fa-shield-halved text-white text-lg"></i>
                </div>
                <div>
                    <h1 class="font-bold text-sm leading-tight text-white">Status Agent</h1>
                    <p class="text-[11px] text-slate-400">ReAct Investigation Bot</p>
                </div>
            </div>

            <!-- New Chat Button -->
            <button onclick="clearChat()" class="w-full py-2.5 px-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-slate-600 rounded-xl text-xs font-semibold text-slate-200 transition flex items-center justify-center gap-2">
                <i class="fa-solid fa-plus text-xs"></i> Đoạn chat mới
            </button>

            <!-- Mode Controls -->
            <div class="bg-slate-900/80 p-3 rounded-xl border border-slate-800 space-y-3">
                <div class="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    <i class="fa-solid fa-sliders text-blue-400"></i> Cấu hình Agent
                </div>
                <div>
                    <label class="text-[11px] text-slate-400 block mb-1">Nguồn dữ liệu:</label>
                    <select id="mode-select" class="w-full bg-slate-800 border border-borderbg rounded-lg px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500">
                        <option value="snapshot" selected>Snapshot (09/11/2026)</option>
                        <option value="live">Live (Gọi Status API thật)</option>
                    </select>
                </div>
                <div>
                    <label class="text-[11px] text-slate-400 block mb-1">Bộ công cụ (Tools):</label>
                    <select id="tools-select" class="w-full bg-slate-800 border border-borderbg rounded-lg px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500">
                        <option value="main" selected>Bài chính (GitHub, Cloudflare)</option>
                        <option value="bonus">Bonus (5 Nền tảng)</option>
                    </select>
                </div>
            </div>

            <!-- Benchmark Link Button -->
            <button onclick="toggleBenchmarkModal(true)" class="w-full py-2 px-3 bg-indigo-950/40 hover:bg-indigo-900/50 border border-indigo-700/50 rounded-xl text-xs font-semibold text-indigo-300 transition flex items-center justify-between">
                <span class="flex items-center gap-2"><i class="fa-solid fa-chart-line text-indigo-400"></i> Bảng điểm Benchmark</span>
                <span class="text-[10px] bg-indigo-500/20 px-1.5 py-0.5 rounded text-indigo-300">93.86đ</span>
            </button>
        </div>

        <!-- Student Info Bottom -->
        <div class="p-4 border-t border-borderbg bg-slate-950/40 text-[11px] text-slate-400 space-y-1">
            <div class="font-semibold text-slate-200">Trần Gia Bảo</div>
            <div>MSSV: 2A202603914</div>
            <div class="text-[10px] text-slate-500">Lớp: K5-L3B · AI Thực Chiến VinUni</div>
        </div>
    </aside>

    <!-- Main Chat Container (Right) -->
    <main class="flex-1 flex flex-col h-screen overflow-hidden bg-chatbg">

        <!-- Top Header for Mobile/Title -->
        <header class="h-14 border-b border-borderbg bg-slate-900/60 backdrop-blur px-4 flex items-center justify-between shrink-0">
            <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                <span class="font-semibold text-sm text-white">Status Investigation Assistant</span>
                <span class="text-[11px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full border border-slate-700 ml-1">ReAct Engine</span>
            </div>
            <button onclick="toggleBenchmarkModal(true)" class="md:hidden text-xs bg-indigo-600 px-2.5 py-1 rounded-lg text-white font-medium">
                Benchmark
            </button>
        </header>

        <!-- Message List Area -->
        <div id="messages-container" class="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 chat-scroll">
            
            <!-- Welcome Greeting Box -->
            <div id="welcome-box" class="max-w-2xl mx-auto my-8 text-center space-y-4">
                <div class="w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 mx-auto flex items-center justify-center shadow-xl shadow-blue-500/20">
                    <i class="fa-solid fa-robot text-white text-2xl"></i>
                </div>
                <h2 class="text-xl font-bold text-white">Xin chào! Em có thể giúp gì cho anh?</h2>
                <p class="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
                    Em là Agent điều tra trạng thái hệ thống bằng mô hình ReAct (tự suy luận, tự gọi công cụ và kiểm chứng nguồn gốc sự cố).
                </p>

                <!-- Quick Prompts Chips -->
                <div class="pt-2 flex flex-wrap gap-2 justify-center max-w-lg mx-auto">
                    <button onclick="sendQuickPrompt(1)" class="text-xs py-1.5 px-3 rounded-full bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition flex items-center gap-1.5">
                        <i class="fa-solid fa-magnifying-glass text-blue-400 text-[10px]"></i> GitHub Actions có bị lỗi không?
                    </button>
                    <button onclick="sendQuickPrompt(2)" class="text-xs py-1.5 px-3 rounded-full bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition flex items-center gap-1.5">
                        <i class="fa-solid fa-link text-indigo-400 text-[10px]"></i> Lần theo link sự cố xr3myzj7ms51 (Multi-step)
                    </button>
                    <button onclick="sendQuickPrompt(3)" class="text-xs py-1.5 px-3 rounded-full bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition flex items-center gap-1.5">
                        <i class="fa-solid fa-shield-virus text-emerald-400 text-[10px]"></i> Cloudflare Cache Purge & FedRAMP
                    </button>
                </div>
            </div>

        </div>

        <!-- Input Box Area (Bottom Sticky) -->
        <div class="p-4 bg-slate-900/80 backdrop-blur border-t border-borderbg shrink-0">
            <div class="max-w-3xl mx-auto">
                <form onsubmit="handleSend(event)" class="relative flex items-center">
                    <textarea id="user-input" rows="1" onkeydown="handleKeyDown(event)" placeholder="Hỏi về trạng thái GitHub, Cloudflare, sự cố gần đây..." class="w-full bg-inputbg text-slate-100 placeholder-slate-500 text-sm rounded-2xl pl-4 pr-12 py-3 border border-borderbg focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none max-h-32 shadow-inner"></textarea>
                    <button type="submit" id="send-btn" class="absolute right-2.5 w-8 h-8 rounded-xl bg-blue-600 hover:bg-blue-500 text-white flex items-center justify-center transition shadow-md shadow-blue-500/30">
                        <i class="fa-solid fa-arrow-up text-xs"></i>
                    </button>
                </form>
                <div class="flex items-center justify-between text-[11px] text-slate-500 mt-2 px-1">
                    <span>Mô hình: <b class="text-slate-400">gemini-flash-lite-latest</b> · ReAct Loop stdlib</span>
                    <span>Nhấn <kbd class="px-1 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400 text-[10px]">Enter</kbd> để gửi</span>
                </div>
            </div>
        </div>

    </main>

    <!-- Modal Benchmark & Evaluation -->
    <div id="benchmark-modal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
        <div class="bg-slate-900 border border-borderbg rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <div class="p-5 border-b border-borderbg flex items-center justify-between">
                <div>
                    <h3 class="font-bold text-white text-base flex items-center gap-2">
                        <i class="fa-solid fa-chart-simple text-blue-400"></i> Bảng điểm Benchmark & Đánh giá Cải tiến
                    </h3>
                    <p class="text-xs text-slate-400 mt-0.5">Kết quả chạy thực tế của bộ 22 case test & 10 case bonus</p>
                </div>
                <button onclick="toggleBenchmarkModal(false)" class="text-slate-400 hover:text-white p-1 rounded-lg">
                    <i class="fa-solid fa-xmark text-lg"></i>
                </button>
            </div>
            
            <div class="p-5 overflow-y-auto space-y-5">
                <div class="grid grid-cols-3 gap-3 text-center">
                    <div class="bg-slate-800/80 p-3 rounded-xl border border-slate-700">
                        <div class="text-[11px] text-slate-400 uppercase font-semibold">Lần 1 (Before)</div>
                        <div class="text-xl font-bold text-amber-400 mt-0.5">89.86 / 100</div>
                    </div>
                    <div class="bg-slate-800/80 p-3 rounded-xl border border-blue-500/40">
                        <div class="text-[11px] text-blue-300 uppercase font-semibold">Lần 2 (After)</div>
                        <div class="text-xl font-bold text-emerald-400 mt-0.5">93.86 / 100</div>
                        <div class="text-[10px] text-emerald-400 mt-0.5 font-medium">▲ Tăng +4.00đ</div>
                    </div>
                    <div class="bg-slate-800/80 p-3 rounded-xl border border-slate-700">
                        <div class="text-[11px] text-slate-400 uppercase font-semibold">Bonus (+15đ)</div>
                        <div class="text-xl font-bold text-purple-400 mt-0.5">+13.50 / 15đ</div>
                        <div class="text-[10px] text-purple-300 mt-0.5">90.0/100 điểm</div>
                    </div>
                </div>

                <div class="bg-slate-950/60 p-4 rounded-xl border border-slate-800 space-y-2 text-xs">
                    <div class="font-bold text-indigo-300">Đột phá ở các ca khó:</div>
                    <ul class="space-y-1.5 list-disc pl-4 text-slate-300">
                        <li><b>Case H6 (Dữ liệu dài & 40 tin rác):</b> Tăng từ <b>55 ➔ 100 điểm</b> sau khi cải tiến prompt và cơ chế Source Gate nhắc model trả lời đầy đủ nguyên nhân vs ảnh hưởng.</li>
                        <li><b>Case A5 (Mốc thời gian snapshot & giới hạn 50 tin):</b> Tăng từ <b>70 ➔ 100 điểm</b> sau khi định hướng chuẩn mốc năm 2026.</li>
                        <li><b>20 trên 22 test case</b> đạt điểm tuyệt đối 100/100!</li>
                    </ul>
                </div>
            </div>

            <div class="p-4 border-t border-borderbg bg-slate-950/40 text-right">
                <button onclick="toggleBenchmarkModal(false)" class="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-xl text-xs font-semibold text-white">Đóng</button>
            </div>
        </div>
    </div>

    <script>
        const QUICK_PROMPTS = {
            1: "GitHub Actions hiện có sự cố không? Hãy kiểm tra incident gần đây.",
            2: "Xem status GitHub Actions, tìm incident h02n9572mx9y và theo liên kết của nó. Incident gộp có nêu nguyên nhân hay chỉ mô tả ảnh hưởng?",
            3: "Cloudflare cache purge báo degraded. CLB là khách hàng không thuộc FedRAMP. Incident wp49bp8bqo6c có chứng minh CLB bị sự cố này ảnh hưởng không? Hãy chỉ ra thông báo cụ thể, trạng thái và nguồn."
        };

        function sendQuickPrompt(id) {
            document.getElementById('user-input').value = QUICK_PROMPTS[id];
            handleSend(new Event('submit'));
        }

        function handleKeyDown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend(e);
            }
        }

        function clearChat() {
            const container = document.getElementById('messages-container');
            container.innerHTML = `
                <div id="welcome-box" class="max-w-2xl mx-auto my-8 text-center space-y-4">
                    <div class="w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 mx-auto flex items-center justify-center shadow-xl shadow-blue-500/20">
                        <i class="fa-solid fa-robot text-white text-2xl"></i>
                    </div>
                    <h2 class="text-xl font-bold text-white">Bắt đầu phiên hội thoại mới</h2>
                    <p class="text-xs text-slate-400 max-w-md mx-auto">Em đã sẵn sàng! Anh có thể hỏi bất kỳ câu hỏi nào về trạng thái hạ tầng hệ thống.</p>
                </div>
            `;
        }

        function toggleBenchmarkModal(show) {
            const modal = document.getElementById('benchmark-modal');
            if (show) modal.classList.remove('hidden');
            else modal.classList.add('hidden');
        }

        async function handleSend(e) {
            if (e) e.preventDefault();
            const input = document.getElementById('user-input');
            const query = input.value.trim();
            if (!query) return;

            // Remove welcome box if present
            const welcome = document.getElementById('welcome-box');
            if (welcome) welcome.remove();

            // Append User Message
            appendUserMessage(query);
            input.value = '';

            // Append Temporary Loading Bot Message
            const loadingId = 'loading-' + Date.now();
            appendLoadingMessage(loadingId);

            const sendBtn = document.getElementById('send-btn');
            sendBtn.disabled = true;

            try {
                const response = await fetch('/api/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        question: query,
                        mode: document.getElementById('mode-select').value,
                        tools: document.getElementById('tools-select').value
                    })
                });

                const data = await response.json();
                replaceWithBotMessage(loadingId, data);
            } catch (err) {
                replaceWithErrorMessage(loadingId, err.message);
            } finally {
                sendBtn.disabled = false;
            }
        }

        function appendUserMessage(text) {
            const container = document.getElementById('messages-container');
            const msgEl = document.createElement('div');
            msgEl.className = 'flex justify-end';
            msgEl.innerHTML = `
                <div class="max-w-xl bg-blue-600 text-white text-sm py-2.5 px-4 rounded-2xl rounded-tr-none shadow-md leading-relaxed">
                    ${escapeHtml(text)}
                </div>
            `;
            container.appendChild(msgEl);
            container.scrollTop = container.scrollHeight;
        }

        function appendLoadingMessage(id) {
            const container = document.getElementById('messages-container');
            const msgEl = document.createElement('div');
            msgEl.id = id;
            msgEl.className = 'flex items-start gap-3 max-w-2xl';
            msgEl.innerHTML = `
                <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shrink-0 mt-0.5 shadow">
                    <i class="fa-solid fa-robot text-white text-xs"></i>
                </div>
                <div class="bg-msgbot border border-borderbg py-3 px-4 rounded-2xl rounded-tl-none text-xs text-slate-300 flex items-center gap-2">
                    <i class="fa-solid fa-spinner fa-spin text-blue-400"></i>
                    <span>Đang suy luận ReAct loop và điều tra sự cố...</span>
                </div>
            `;
            container.appendChild(msgEl);
            container.scrollTop = container.scrollHeight;
        }

        function replaceWithBotMessage(id, data) {
            const el = document.getElementById(id);
            if (!el) return;

            const toolCalls = (data.trace || []).filter(t => t.event === 'tool');
            const hasSourceGate = (data.trace || []).some(t => t.event === 'validation_missing_source');
            const answerHtml = marked.parse(data.answer || '(Không có nội dung trả về)');

            let toolsAccordionHtml = '';
            if (toolCalls.length > 0) {
                toolsAccordionHtml = `
                    <div class="mt-3 pt-2 border-t border-slate-700/60">
                        <details class="group text-xs">
                            <summary class="cursor-pointer text-[11px] font-semibold text-blue-400 hover:text-blue-300 flex items-center justify-between list-none py-1">
                                <span class="flex items-center gap-1.5">
                                    <i class="fa-solid fa-screwdriver-wrench text-[10px]"></i>
                                    Đã thực thi ${toolCalls.length} công cụ điều tra
                                    ${hasSourceGate ? '<span class="bg-amber-500/20 text-amber-300 px-1.5 py-0.2 rounded text-[10px]">Đã qua Source Gate</span>' : ''}
                                </span>
                                <i class="fa-solid fa-chevron-down text-[10px] transition group-open:rotate-180"></i>
                            </summary>
                            <div class="mt-2 space-y-2 pl-2 border-l-2 border-blue-500/40 py-1">
                                ${toolCalls.map(t => `
                                    <div class="bg-slate-900/80 p-2 rounded-lg border border-slate-800 text-[11px]">
                                        <div class="flex items-center justify-between text-slate-300 font-mono">
                                            <span class="font-bold text-sky-300">Tool: ${t.name}</span>
                                            <span class="text-[10px] text-slate-500">Step ${t.step}</span>
                                        </div>
                                        <div class="text-[10px] text-slate-400 truncate mt-0.5">Tham số: ${JSON.stringify(t.arguments || {})}</div>
                                        ${t.result?.url ? `<div class="text-[10px] text-indigo-300 mt-0.5 truncate">Nguồn: <a href="${t.result.url}" target="_blank" class="underline">${t.result.url}</a></div>` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </details>
                    </div>
                `;
            }

            el.innerHTML = `
                <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shrink-0 mt-0.5 shadow">
                    <i class="fa-solid fa-robot text-white text-xs"></i>
                </div>
                <div class="bg-msgbot border border-borderbg py-3 px-4 rounded-2xl rounded-tl-none text-sm text-slate-200 shadow-md leading-relaxed max-w-2xl w-full">
                    <div class="prose prose-invert prose-sm max-w-none">
                        ${answerHtml}
                    </div>
                    ${toolsAccordionHtml}
                </div>
            `;

            const container = document.getElementById('messages-container');
            container.scrollTop = container.scrollHeight;
        }

        function replaceWithErrorMessage(id, errorText) {
            const el = document.getElementById(id);
            if (!el) return;
            el.innerHTML = `
                <div class="w-8 h-8 rounded-xl bg-rose-600 flex items-center justify-center shrink-0 mt-0.5">
                    <i class="fa-solid fa-exclamation text-white text-xs"></i>
                </div>
                <div class="bg-rose-950/40 border border-rose-500/40 py-3 px-4 rounded-2xl rounded-tl-none text-xs text-rose-300">
                    Lỗi kết nối: ${errorText}
                </div>
            `;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
'''


class ChatDemoHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/' or parsed.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(CHAT_HTML.encode('utf-8'))
        elif parsed.path == '/api/benchmarks':
            before_file = ROOT / 'eval_before.json'
            after_file = ROOT / 'eval_after.json'
            bonus_file = ROOT / 'eval_bonus.json'

            data = {
                'before': json.loads(before_file.read_text(encoding='utf-8')) if before_file.exists() else None,
                'after': json.loads(after_file.read_text(encoding='utf-8')) if after_file.exists() else None,
                'bonus': json.loads(bonus_file.read_text(encoding='utf-8')) if bonus_file.exists() else None
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/run':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            req_data = json.loads(body.decode('utf-8'))

            question = req_data.get('question', '')
            mode = req_data.get('mode', 'snapshot')
            tool_type = req_data.get('tools', 'main')

            provider_name = os.getenv('PROVIDER', 'gemini')
            model_name = os.getenv('MODEL', 'gemini-flash-lite-latest')

            try:
                provider = Provider(provider_name, model_name)
                if tool_type == 'bonus':
                    tools = BonusTools(mode=mode)
                    max_steps = 16
                else:
                    tools = StatusTools(mode=mode)
                    max_steps = 8

                result = run_agent(question, provider, tools, max_steps=max_steps)
            except Exception as exc:
                result = {
                    'status': 'error',
                    'answer': f'Lỗi thực thi Agent: {str(exc)}',
                    'trace': [{'event': 'error', 'step': 1, 'error': str(exc)}],
                    'usage': [],
                    'error': str(exc)
                }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def main():
    ports = [8000, 7860, 5000, 8888, 9000, 8081, 8080]
    if os.getenv('PORT'):
        ports = [int(os.getenv('PORT'))] + ports

    server = None
    active_port = None
    for p in ports:
        try:
            server = http.server.ThreadingHTTPServer(('0.0.0.0', p), ChatDemoHandler)
            active_port = p
            break
        except OSError:
            continue

    if not server:
        print('Không thể mở port nào!')
        return

    print('=' * 65)
    print(f'🚀 GIAO DIỆN CHAT AI ĐANG CHẠY TẠI: http://localhost:{active_port}')
    print(f'👉 Mở trình duyệt truy cập: http://localhost:{active_port}')
    print('   - Provider:', os.getenv('PROVIDER'))
    print('   - Model:', os.getenv('MODEL'))
    print('   - Giao diện: Chuẩn phong cách ChatGPT / Gemini / Claude')
    print('   - Bấm Ctrl+C để dừng server khi hoàn tất.')
    print('=' * 65)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nĐã dừng server demo.')


if __name__ == '__main__':
    main()
