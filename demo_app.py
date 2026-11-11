#!/usr/bin/env python3
"""Giao diện Demo trực quan: Status Investigation Agent (ReAct Loop).
Chạy bằng thư viện chuẩn Python (stdlib), không cần cài thêm package.
"""
import http.server
import json
import os
from pathlib import Path
import sys
import threading
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

HTML_PAGE = r'''<!DOCTYPE html>
<html lang="vi" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Status Investigation Agent · ReAct Loop Interactive Demo</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        brand: { 50: '#eef2ff', 500: '#6366f1', 600: '#4f46e5', 700: '#4338ca', 900: '#1e1b4b' },
                        darkbg: '#0f172a',
                        cardbg: '#1e293b',
                        borderbg: '#334155'
                    }
                }
            }
        }
    </script>
    <style>
        select, select option {
            background-color: #0f172a !important;
            color: #f8fafc !important;
        }
        .prose pre { background: #0b0f19; border: 1px solid #334155; border-radius: 8px; padding: 12px; }
        .prose a { color: #818cf8; text-decoration: underline; }
        .prose ul { list-style-type: disc; padding-left: 20px; }
        .prose ol { list-style-type: decimal; padding-left: 20px; }
        .pulse-dot { animation: pulse 1.5s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.9); } }
    </style>
</head>
<body class="bg-darkbg text-slate-100 min-h-screen font-sans flex flex-col">

    <!-- Header Navigation -->
    <header class="border-b border-borderbg bg-slate-900/80 backdrop-blur sticky top-0 z-50 px-6 py-4">
        <div class="max-w-7xl mx-auto flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-400 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                    <i class="fa-solid fa-robot text-white text-lg"></i>
                </div>
                <div>
                    <h1 class="font-bold text-lg leading-tight flex items-center gap-2">
                        Status Investigation Agent
                        <span class="text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-full font-medium">ReAct Loop</span>
                    </h1>
                    <p class="text-xs text-slate-400">Trần Gia Bảo · MSSV: 2A202603914 · Lớp K5-L3B · VinUni AI Thực Chiến</p>
                </div>
            </div>

            <!-- Tabs -->
            <div class="flex items-center space-x-2 bg-slate-800 p-1 rounded-xl border border-borderbg">
                <button onclick="switchTab('live')" id="tab-btn-live" class="px-4 py-1.5 rounded-lg text-sm font-semibold transition bg-brand-600 text-white shadow">
                    <i class="fa-solid fa-play mr-1.5 text-xs"></i> Live Demo
                </button>
                <button onclick="switchTab('benchmark')" id="tab-btn-benchmark" class="px-4 py-1.5 rounded-lg text-sm font-semibold transition text-slate-300 hover:text-white">
                    <i class="fa-solid fa-chart-line mr-1.5 text-xs"></i> Benchmark & Eval
                </button>
            </div>
        </div>
    </header>

    <!-- Main Container -->
    <main class="max-w-7xl mx-auto p-6 flex-1 w-full">

        <!-- TAB 1: LIVE DEMO -->
        <div id="view-live" class="grid grid-cols-1 lg:grid-cols-12 gap-6">

            <!-- Left Form & Presets (5 Cols) -->
            <div class="lg:col-span-5 space-y-5">
                <div class="bg-cardbg rounded-2xl border border-borderbg p-5 shadow-xl">
                    <h2 class="text-base font-bold text-white mb-3 flex items-center gap-2">
                        <i class="fa-solid fa-terminal text-indigo-400"></i> Điều tra sự cố hệ thống
                    </h2>

                    <!-- Presets -->
                    <div class="space-y-2 mb-4">
                        <label class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Kịch bản Demo tiêu biểu:</label>
                        <div class="grid grid-cols-1 gap-2">
                            <button onclick="setPrompt(1)" class="text-left text-xs p-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 hover:border-indigo-500/50 transition">
                                <div class="font-semibold text-indigo-300 flex items-center justify-between">
                                    <span>🌟 Multi-Step Link Redirect (H6)</span>
                                    <span class="text-[10px] bg-indigo-500/20 px-1.5 py-0.5 rounded text-indigo-300">Đề xuất</span>
                                </div>
                                <p class="text-slate-400 text-[11px] mt-0.5 line-clamp-1">Tra cứu incident Actions, theo link gộp xr3myzj7ms51 tìm nguyên nhân gốc.</p>
                            </button>
                            <button onclick="setPrompt(2)" class="text-left text-xs p-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 hover:border-indigo-500/50 transition">
                                <div class="font-semibold text-sky-300">🔍 Phân định Scope FedRAMP vs Public (A2)</div>
                                <p class="text-slate-400 text-[11px] mt-0.5 line-clamp-1">Cloudflare cache purge incident wp49bp8bqo6c có ảnh hưởng CLB non-FedRAMP?</p>
                            </button>
                            <button onclick="setPrompt(3)" class="text-left text-xs p-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 hover:border-indigo-500/50 transition">
                                <div class="font-semibold text-emerald-300">⚡ Thử thách Bonus 5 Nhà cung cấp (B1)</div>
                                <p class="text-slate-400 text-[11px] mt-0.5 line-clamp-1">Tổng hợp trạng thái GitHub, Cloudflare, Vercel, npm và DigitalOcean.</p>
                            </button>
                        </div>
                    </div>

                    <!-- Prompt Input -->
                    <div class="space-y-2">
                        <label for="prompt-input" class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Yêu cầu điều tra:</label>
                        <textarea id="prompt-input" rows="4" class="w-full bg-slate-900 border border-borderbg rounded-xl p-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500" placeholder="Nhập câu hỏi điều tra trạng thái..."></textarea>
                    </div>

                    <!-- AI Smart Auto-Detect Routing Card -->
                    <div class="mt-4 pt-3 border-t border-slate-700/60">
                        <div class="flex items-center justify-between p-3 rounded-xl bg-slate-900/90 border border-slate-800 shadow-inner">
                            <div class="flex items-center gap-2.5">
                                <span class="relative flex h-2.5 w-2.5">
                                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                    <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                                </span>
                                <div>
                                    <div class="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                                        <span>AI Tự Động Định Tuyến</span>
                                        <span class="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-1.5 py-0.5 rounded font-mono">Auto-Detect</span>
                                    </div>
                                    <div class="text-[11px] text-slate-400 mt-0.5">
                                        Tự chọn bộ Tool phù hợp & Nguồn dữ liệu theo nội dung câu hỏi
                                    </div>
                                </div>
                            </div>
                            <!-- Toggle Button for Advanced Options -->
                            <button type="button" onclick="toggleAdvancedSettings()" class="text-[11px] text-slate-300 hover:text-white transition flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700">
                                <i class="fa-solid fa-sliders text-[10px] text-indigo-400"></i>
                                <span>Tùy chỉnh</span>
                            </button>
                        </div>

                        <!-- Collapsible Advanced Settings (Mặc định ẩn) -->
                        <div id="advanced-settings" class="hidden mt-3 p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-3">
                            <div class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                                <span>⚙️ Cấu hình thủ công (Tùy chọn):</span>
                                <span class="text-[10px] text-slate-500 font-normal">Mặc định: Tự động</span>
                            </div>
                            <div class="grid grid-cols-2 gap-3">
                                <div>
                                    <label class="text-[11px] text-slate-300 block mb-1 font-medium">DỮ LIỆU STATUS:</label>
                                    <select id="mode-select" class="w-full bg-[#0f172a] text-slate-100 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs focus:ring-1 focus:ring-indigo-500 focus:outline-none" style="background-color: #0f172a !important; color: #ffffff !important;">
                                        <option value="auto" selected style="background-color: #0f172a; color: #ffffff;">✨ Tự động (Khuyên dùng)</option>
                                        <option value="snapshot" style="background-color: #0f172a; color: #ffffff;">Snapshot (Cố định 2026)</option>
                                        <option value="live" style="background-color: #0f172a; color: #ffffff;">Live (Gọi API thực tế)</option>
                                    </select>
                                </div>
                                <div>
                                    <label class="text-[11px] text-slate-300 block mb-1 font-medium">BỘ CÔNG CỤ (TOOLS):</label>
                                    <select id="tools-select" class="w-full bg-[#0f172a] text-slate-100 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs focus:ring-1 focus:ring-indigo-500 focus:outline-none" style="background-color: #0f172a !important; color: #ffffff !important;">
                                        <option value="auto" selected style="background-color: #0f172a; color: #ffffff;">✨ Tự động (Theo câu hỏi)</option>
                                        <option value="main" style="background-color: #0f172a; color: #ffffff;">Bài chính (GitHub & Cloudflare)</option>
                                        <option value="bonus" style="background-color: #0f172a; color: #ffffff;">Bonus (5 Nền tảng mở rộng)</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Run Button -->
                    <button id="btn-run" onclick="executeInvestigation()" class="w-full mt-4 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-semibold py-2.5 rounded-xl shadow-lg shadow-indigo-500/25 transition flex items-center justify-center space-x-2">
                        <i class="fa-solid fa-magnifying-glass"></i>
                        <span>Bắt đầu Vòng lặp ReAct</span>
                    </button>
                </div>

                <!-- Info Card -->
                <div class="bg-cardbg/60 rounded-2xl border border-borderbg/80 p-4 text-xs space-y-2 text-slate-400">
                    <div class="flex items-center gap-2 text-slate-300 font-semibold">
                        <i class="fa-solid fa-shield-halved text-indigo-400"></i> Cơ chế phòng thủ tự động:
                    </div>
                    <ul class="space-y-1 list-disc pl-4 text-[11px]">
                        <li><b>Source Gate Validation:</b> Tự động ép model trích dẫn URL nguồn incident trước khi cho phép kết thúc.</li>
                        <li><b>Rate-Limit Backoff:</b> Tự động thử lại khi gặp HTTP 429/503 trên free-tier.</li>
                        <li><b>Safety Boundaries:</b> Bỏ qua mọi bẫy Prompt Injection cài cắm trong tool output.</li>
                    </ul>
                </div>
            </div>

            <!-- Right Results & ReAct Trace View (7 Cols) -->
            <div class="lg:col-span-7 space-y-5">

                <!-- Final Answer Card -->
                <div class="bg-cardbg rounded-2xl border border-borderbg p-5 shadow-xl min-h-[220px]">
                    <div class="flex items-center justify-between mb-3 pb-3 border-b border-borderbg">
                        <h3 class="font-bold text-white flex items-center gap-2">
                            <i class="fa-solid fa-comment-dots text-emerald-400"></i>
                            Kết quả Phân tích (Final Answer)
                        </h3>
                        <div id="status-badge" class="text-xs px-2.5 py-1 rounded-full font-medium bg-slate-800 text-slate-400 border border-slate-700">
                            Sẵn sàng
                        </div>
                    </div>
                    <div id="answer-content" class="prose prose-invert prose-sm max-w-none text-slate-300 text-sm leading-relaxed">
                        <p class="text-slate-500 italic">Bấm "Bắt đầu Vòng lặp ReAct" để xem kết quả phân tích sự cố thời gian thực từ Agent...</p>
                    </div>
                </div>

                <!-- ReAct Execution Trace -->
                <div class="bg-cardbg rounded-2xl border border-borderbg p-5 shadow-xl">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="font-bold text-white flex items-center gap-2">
                            <i class="fa-solid fa-diagram-project text-indigo-400"></i>
                            Nhật ký Vòng lặp ReAct (Step-by-Step Trace)
                        </h3>
                        <span id="step-counter" class="text-xs text-slate-400 bg-slate-800 px-2.5 py-1 rounded-lg border border-slate-700">0 steps</span>
                    </div>

                    <div id="trace-container" class="space-y-3 max-h-[460px] overflow-y-auto pr-2">
                        <div class="text-center py-8 text-slate-500 text-xs">Chưa có sự kiện nào được ghi nhận.</div>
                    </div>
                </div>

            </div>
        </div>

        <!-- TAB 2: BENCHMARK & EVALUATION RESULTS -->
        <div id="view-benchmark" class="hidden space-y-6">

            <!-- Summary Stat Cards -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="bg-cardbg p-5 rounded-2xl border border-borderbg shadow-lg">
                    <span class="text-xs text-slate-400 uppercase font-semibold">Điểm Eval Lần 1 (Before)</span>
                    <div class="text-2xl font-black text-amber-400 mt-1">89.86 <span class="text-xs font-normal text-slate-400">/ 100</span></div>
                    <p class="text-[11px] text-slate-400 mt-1">Đủ 22/22 case, phát hiện lỗi H6 (55đ) & A5 (70đ).</p>
                </div>
                <div class="bg-cardbg p-5 rounded-2xl border border-indigo-500/40 shadow-lg shadow-indigo-500/10">
                    <span class="text-xs text-indigo-300 uppercase font-semibold">Điểm Eval Lần 2 (After)</span>
                    <div class="text-2xl font-black text-emerald-400 mt-1">100.00 <span class="text-xs font-normal text-slate-400">/ 100</span></div>
                    <p class="text-[11px] text-emerald-400/90 mt-1 font-medium">▲ Tăng +10.14 điểm (22/22 case đạt 100đ tuyệt đối).</p>
                </div>
                <div class="bg-cardbg p-5 rounded-2xl border border-borderbg shadow-lg">
                    <span class="text-xs text-slate-400 uppercase font-semibold">Cải tiến Case H6</span>
                    <div class="text-2xl font-black text-indigo-400 mt-1">55 ➔ 100</div>
                    <p class="text-[11px] text-slate-400 mt-1">▲ Tăng +45 điểm nhờ sửa Prompt & Source Gate.</p>
                </div>
                <div class="bg-cardbg p-5 rounded-2xl border border-borderbg shadow-lg">
                    <span class="text-xs text-slate-400 uppercase font-semibold">Thử thách BONUS (+15đ)</span>
                    <div class="text-2xl font-black text-purple-400 mt-1">+13.50 <span class="text-xs font-normal text-slate-400">/ 15đ</span></div>
                    <p class="text-[11px] text-purple-300/90 mt-1 font-medium">90.0/100 điểm trên 10 case bonus 5 nhà mạng.</p>
                </div>
            </div>

            <!-- Comparison Table -->
            <div class="bg-cardbg rounded-2xl border border-borderbg p-6 shadow-xl">
                <div class="flex items-center justify-between mb-4 pb-3 border-b border-borderbg">
                    <div>
                        <h3 class="font-bold text-white text-base">Bảng So sánh Trước và Sau Cải tiến (Benchmark Matrix)</h3>
                        <p class="text-xs text-slate-400 mt-0.5">Dữ liệu thực tế được kết xuất từ eval_before.json và eval_after.json</p>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-3 py-1 rounded-full font-medium">
                            <i class="fa-solid fa-check-double mr-1"></i> Đạt chuẩn 100% Rubric
                        </span>
                    </div>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs border-collapse">
                        <thead>
                            <tr class="bg-slate-900/60 text-slate-400 border-b border-slate-700">
                                <th class="py-3 px-3 font-semibold">ID Case</th>
                                <th class="py-3 px-3 font-semibold">Mô tả bài toán / Kỹ năng</th>
                                <th class="py-3 px-3 font-semibold text-center">Trước cải tiến (Lần 1)</th>
                                <th class="py-3 px-3 font-semibold text-center">Sau cải tiến (Lần 2)</th>
                                <th class="py-3 px-3 font-semibold">Đánh giá chuyển biến</th>
                            </tr>
                        </thead>
                        <tbody id="benchmark-table-body" class="divide-y divide-slate-800 text-slate-300">
                            <!-- Injected by JavaScript -->
                        </tbody>
                    </table>
                </div>
            </div>

        </div>

    </main>

    <footer class="border-t border-borderbg py-3 px-6 text-center text-xs text-slate-500 bg-slate-900/50">
        Lab: Xây dựng Status Investigation Agent · ReAct Loop Architecture · Model: gemini-flash-lite-latest
    </footer>

    <script>
        const PRESETS = {
            1: "Xem status GitHub Actions, tìm incident h02n9572mx9y và theo liên kết của nó. Incident gộp có nêu nguyên nhân hay chỉ mô tả ảnh hưởng? Nêu giới hạn dữ liệu và trích nguồn.",
            2: "Cloudflare cache purge báo degraded. CLB là khách hàng không thuộc FedRAMP. Incident wp49bp8bqo6c có chứng minh CLB bị sự cố này ảnh hưởng không? Hãy chỉ ra thông báo cụ thể, trạng thái và nguồn.",
            3: "Tổng hợp trạng thái GitHub, Cloudflare, Vercel, npm và DigitalOcean: mỗi nhà cung cấp đang báo gì trong snapshot, thời điểm dữ liệu, và nguồn? Đừng suy ra nguyên nhân liên quan giữa các bên."
        };

        function toggleAdvancedSettings() {
            const el = document.getElementById('advanced-settings');
            if (el) el.classList.toggle('hidden');
        }

        function setPrompt(id) {
            document.getElementById('prompt-input').value = PRESETS[id];
            const selTools = document.getElementById('tools-select');
            const selMode = document.getElementById('mode-select');
            if (selTools) selTools.value = 'auto';
            if (selMode) selMode.value = 'auto';
        }

        function switchTab(tab) {
            const vLive = document.getElementById('view-live');
            const vBench = document.getElementById('view-benchmark');
            const bLive = document.getElementById('tab-btn-live');
            const bBench = document.getElementById('tab-btn-benchmark');

            if (tab === 'live') {
                vLive.classList.remove('hidden');
                vBench.classList.add('hidden');
                bLive.className = "px-4 py-1.5 rounded-lg text-sm font-semibold transition bg-brand-600 text-white shadow";
                bBench.className = "px-4 py-1.5 rounded-lg text-sm font-semibold transition text-slate-300 hover:text-white";
            } else {
                vLive.classList.add('hidden');
                vBench.classList.remove('hidden');
                bBench.className = "px-4 py-1.5 rounded-lg text-sm font-semibold transition bg-brand-600 text-white shadow";
                bLive.className = "px-4 py-1.5 rounded-lg text-sm font-semibold transition text-slate-300 hover:text-white";
                loadBenchmarkData();
            }
        }

        async function executeInvestigation() {
            const prompt = document.getElementById('prompt-input').value.trim();
            if (!prompt) {
                alert('Vui lòng nhập câu hỏi điều tra!');
                return;
            }

            const btn = document.getElementById('btn-run');
            const badge = document.getElementById('status-badge');
            const ansBox = document.getElementById('answer-content');
            const traceBox = document.getElementById('trace-container');
            const stepCounter = document.getElementById('step-counter');

            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Đang suy luận ReAct Loop...';
            badge.className = "text-xs px-2.5 py-1 rounded-full font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1.5";
            badge.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-amber-400 pulse-dot"></span> Đang chạy vòng lặp...';
            ansBox.innerHTML = '<p class="text-slate-400 italic flex items-center gap-2"><i class="fa-solid fa-circle-notch fa-spin text-indigo-400"></i> Model đang phân tích câu hỏi và điều phối tools...</p>';
            traceBox.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs flex items-center justify-center gap-2"><i class="fa-solid fa-gear fa-spin text-indigo-400 text-base"></i> Đang khởi tạo context và kết nối provider...</div>';

            const modeVal = document.getElementById('mode-select') ? document.getElementById('mode-select').value : 'auto';
            const toolsVal = document.getElementById('tools-select') ? document.getElementById('tools-select').value : 'auto';

            try {
                const response = await fetch('/api/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        question: prompt,
                        mode: modeVal,
                        tools: toolsVal
                    })
                });

                const data = await response.json();

                // Render Badge
                if (data.status === 'completed') {
                    const routingInfo = data.detected_info ? ` (${data.detected_info})` : '';
                    badge.className = "text-xs px-2.5 py-1 rounded-full font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5";
                    badge.innerHTML = `<i class="fa-solid fa-check text-[10px]"></i> Hoàn tất${routingInfo}`;
                    badge.innerHTML = '<i class="fa-solid fa-check text-[10px]"></i> Hoàn tất (Completed)';
                } else {
                    badge.className = "text-xs px-2.5 py-1 rounded-full font-medium bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center gap-1.5";
                    badge.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-[10px]"></i> ${data.status}`;
                }

                // Render Answer
                ansBox.innerHTML = marked.parse(data.answer || '(Không có nội dung trả về)');

                // Render Trace
                renderTrace(data.trace || []);
                stepCounter.innerText = `${(data.trace || []).length} events`;

            } catch (err) {
                ansBox.innerHTML = `<p class="text-rose-400">Lỗi kết nối API: ${err.message}</p>`;
                badge.innerText = 'Lỗi kết nối';
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> <span>Bắt đầu Vòng lặp ReAct</span>';
            }
        }

        function renderTrace(trace) {
            const container = document.getElementById('trace-container');
            if (!trace.length) {
                container.innerHTML = '<div class="text-center py-8 text-slate-500 text-xs">Không có trace.</div>';
                return;
            }

            container.innerHTML = trace.map((t, idx) => {
                if (t.event === 'model') {
                    return `
                        <div class="p-3 bg-slate-900/90 rounded-xl border border-slate-700/80 text-xs space-y-1">
                            <div class="flex items-center justify-between text-indigo-300 font-semibold">
                                <span class="flex items-center gap-1.5"><i class="fa-solid fa-brain text-indigo-400"></i> Step ${t.step}: Model suy luận & ra quyết định</span>
                                <span class="text-[10px] bg-indigo-900/60 text-indigo-300 px-2 py-0.5 rounded border border-indigo-700/50">finish: ${t.finish}</span>
                            </div>
                        </div>
                    `;
                } else if (t.event === 'tool') {
                    const argStr = JSON.stringify(t.arguments || {});
                    const ok = t.result?.ok !== false;
                    return `
                        <div class="p-3 bg-slate-900/90 rounded-xl border ${ok ? 'border-sky-500/30' : 'border-rose-500/40'} text-xs space-y-2">
                            <div class="flex items-center justify-between">
                                <span class="font-bold ${ok ? 'text-sky-300' : 'text-rose-300'} flex items-center gap-1.5">
                                    <i class="fa-solid fa-wrench ${ok ? 'text-sky-400' : 'text-rose-400'}"></i>
                                    Step ${t.step}: Thực thi Tool [${t.name}]
                                </span>
                                <span class="text-[10px] ${ok ? 'bg-sky-900/50 text-sky-300' : 'bg-rose-900/50 text-rose-300'} px-2 py-0.5 rounded font-mono">
                                    ${ok ? 'Success' : 'Error'}
                                </span>
                            </div>
                            <div class="bg-black/40 p-2 rounded-lg font-mono text-[11px] text-slate-300 overflow-x-auto">
                                <span class="text-slate-500">Args:</span> ${argStr}
                            </div>
                            ${t.result?.url ? `<div class="text-[11px] text-indigo-300 flex items-center gap-1"><i class="fa-solid fa-link text-[10px]"></i> URL phát hiện: <a href="${t.result.url}" target="_blank" class="underline hover:text-indigo-200 truncate">${t.result.url}</a></div>` : ''}
                        </div>
                    `;
                } else if (t.event === 'validation_missing_source') {
                    return `
                        <div class="p-3 bg-amber-950/40 rounded-xl border border-amber-500/40 text-xs space-y-1">
                            <div class="flex items-center justify-between text-amber-300 font-bold">
                                <span class="flex items-center gap-1.5"><i class="fa-solid fa-shield text-amber-400"></i> Step ${t.step}: Source Gate Validation kích hoạt</span>
                                <span class="text-[10px] bg-amber-900/60 text-amber-200 px-2 py-0.5 rounded border border-amber-700/50">Thiếu URL nguồn</span>
                            </div>
                            <p class="text-amber-200/80 text-[11px]">Hệ thống phát hiện câu trả lời chưa dẫn URL nguồn từ incident đã tra cứu. Tự động gửi câu nhắc model sửa đổi trong budget step.</p>
                        </div>
                    `;
                } else {
                    return `
                        <div class="p-2.5 bg-slate-800 rounded-lg text-xs font-mono text-slate-300 border border-slate-700">
                            <b>${t.event}</b>: ${JSON.stringify(t)}
                        </div>
                    `;
                }
            }).join('');
        }

        async function loadBenchmarkData() {
            const tbody = document.getElementById('benchmark-table-body');
            tbody.innerHTML = '<tr><td colspan="5" class="text-center py-6 text-slate-400"><i class="fa-solid fa-spinner fa-spin mr-2"></i> Đang tải dữ liệu benchmark...</td></tr>';

            try {
                const res = await fetch('/api/benchmarks');
                const data = await res.json();
                
                const beforeMap = {};
                (data.before?.cases || []).forEach(c => beforeMap[c.id] = c);

                const afterCases = data.after?.cases || [];

                tbody.innerHTML = afterCases.map(after => {
                    const before = beforeMap[after.id] || {};
                    const bScore = before.grade?.score;
                    const aScore = after.grade?.score;
                    
                    let diffBadge = '';
                    if (bScore !== null && aScore !== null) {
                        const diff = aScore - bScore;
                        if (diff > 0) {
                            diffBadge = `<span class="text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded text-[11px]">▲ +${diff}đ (Đột phá)</span>`;
                        } else if (diff === 0) {
                            diffBadge = `<span class="text-slate-400 bg-slate-800 px-2 py-0.5 rounded text-[11px]">Giữ vững 100đ</span>`;
                        } else {
                            diffBadge = `<span class="text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded text-[11px]">▼ ${diff}đ</span>`;
                        }
                    }

                    return `
                        <tr class="hover:bg-slate-800/40 transition">
                            <td class="py-2.5 px-3 font-bold font-mono text-indigo-300">${after.id}</td>
                            <td class="py-2.5 px-3 max-w-md">
                                <div class="font-medium text-slate-200 line-clamp-1">${after.question}</div>
                                <div class="text-[10px] text-slate-400 line-clamp-1 mt-0.5">${after.expected}</div>
                            </td>
                            <td class="py-2.5 px-3 text-center font-bold ${bScore === 100 ? 'text-emerald-400' : (bScore >= 70 ? 'text-amber-400' : 'text-rose-400')}">
                                ${bScore !== null ? bScore : '<span class="text-slate-500 font-normal">unscored</span>'}
                            </td>
                            <td class="py-2.5 px-3 text-center font-bold ${aScore === 100 ? 'text-emerald-400' : (aScore >= 70 ? 'text-amber-400' : 'text-rose-400')}">
                                ${aScore !== null ? aScore : '<span class="text-slate-500 font-normal">unscored</span>'}
                            </td>
                            <td class="py-2.5 px-3">
                                ${diffBadge}
                            </td>
                        </tr>
                    `;
                }).join('');

            } catch (err) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-rose-400">Lỗi nạp benchmark: ${err.message}</td></tr>`;
            }
        }

        // Init default prompt
        setPrompt(1);
    </script>
</body>
</html>
'''


class DemoHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/' or parsed.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
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
            mode = req_data.get('mode', 'auto')
            tool_type = req_data.get('tools', 'auto')

            q_lower = question.lower()
            # Tự động phát hiện chế độ Live nếu câu hỏi có từ khóa thời gian thực / hôm nay
            if mode == 'auto':
                if any(kw in q_lower for kw in ['hôm nay', 'hiện tại', 'bây giờ', 'live', 'realtime', 'thời gian thực', 'ngay lúc này', 'today', 'right now']):
                    mode = 'live'
                else:
                    mode = 'snapshot'

            # Tự động phát hiện bộ công cụ phù hợp
            if tool_type == 'auto':
                if any(p in q_lower for p in ['vercel', 'npm', 'digitalocean', '5 nhà', '5 nền tảng', 'bonus']):
                    tool_type = 'bonus'
                else:
                    tool_type = 'main'

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
                mode_label = 'Live API' if mode == 'live' else 'Snapshot 2026'
                tool_label = 'Bonus 5 nền tảng' if tool_type == 'bonus' else 'Bộ 2 Tools chính'
                result['detected_info'] = f"{mode_label} · {tool_label}"
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
        # Tắt bớt log HTTP để terminal gọn gàng
        return


def main():
    ports = [8000, 7860, 5000, 8888, 9000, 8081, 8080]
    if os.getenv('PORT'):
        ports = [int(os.getenv('PORT'))] + ports

    server = None
    active_port = None
    for p in ports:
        try:
            server = http.server.ThreadingHTTPServer(('0.0.0.0', p), DemoHandler)
            active_port = p
            break
        except OSError:
            continue

    if not server:
        print('Không thể mở port nào!')
        return

    print('=' * 65)
    print(f'🚀 WEB DEMO AGENT ĐANG CHẠY TẠI: http://localhost:{active_port}')
    print(f'👉 Mở trình duyệt truy cập: http://localhost:{active_port}')
    print('   - Provider:', os.getenv('PROVIDER'))
    print('   - Model:', os.getenv('MODEL'))
    print('   - Bấm Ctrl+C để dừng server khi hoàn tất.')
    print('=' * 65)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nĐã dừng server demo.')


if __name__ == '__main__':
    main()
