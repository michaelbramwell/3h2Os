"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
// Global state initialization
window.activityStore = {};
// Helper: Format Pace (min/km)
function formatPace(secondsPerKm) {
    if (!secondsPerKm || isNaN(secondsPerKm) || secondsPerKm === Infinity)
        return '--:--';
    let mins = Math.floor(secondsPerKm / 60);
    let secs = Math.round(secondsPerKm % 60);
    if (secs === 60) {
        mins++;
        secs = 0;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}
// Helper: Format Zones HTML
function formatZonesHTML(zones, type) {
    if (!zones || zones.length === 0)
        return '';
    const active = zones.filter(z => (z.secsInZone || 0) > 10);
    if (active.length === 0)
        return '';
    return active.map(z => {
        const mins = Math.floor(z.secsInZone / 60);
        const secs = Math.round(z.secsInZone % 60);
        const timeStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
        let valStr = '';
        if (type === 'pace' && z.avgValue > 0) {
            valStr = formatPace(1000 / z.avgValue);
        }
        else if (z.avgValue > 0) {
            valStr = Math.round(z.avgValue) + (type === 'hr' ? 'bpm' : (type === 'power' ? 'W' : ''));
        }
        return `
            <div class="grid grid-cols-3 gap-2 border-b border-slate-50 py-1 last:border-0 items-center">
                <div class="text-[10px] font-black italic text-slate-400">Z${z.zoneNumber}</div>
                <div class="text-xs font-bold text-slate-700 font-mono">${valStr}</div>
                <div class="text-[10px] text-slate-500 text-right">${timeStr}</div>
            </div>
        `;
    }).join('');
}
// Helper: Get Training Effect Data
function getTEData(score) {
    if (score < 1.0)
        return { label: 'None', color: 'text-slate-500 bg-slate-200 ring-slate-300' };
    if (score < 2.0)
        return { label: 'Minor', color: 'text-blue-600 bg-blue-50 ring-blue-200' };
    if (score < 3.0)
        return { label: 'Main', color: 'text-emerald-600 bg-emerald-50 ring-emerald-200' };
    if (score < 4.0)
        return { label: 'Impr', color: 'text-amber-600 bg-amber-50 ring-amber-200' };
    if (score < 5.0)
        return { label: 'High', color: 'text-orange-600 bg-orange-50 ring-orange-200' };
    return { label: 'Over', color: 'text-red-600 bg-red-50 ring-red-200' };
}
// UI: Highlight Current Week
function highlightCurrentWeek() {
    const rows = document.querySelectorAll('#plan-body tr');
    const today = new Date();
    rows.forEach(row => {
        if (!row.dataset.start)
            return;
        const weekStart = new Date(row.dataset.start);
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekStart.getDate() + 7);
        if (today >= weekStart && today < weekEnd) {
            row.classList.add('current-week');
            row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    });
}
// UI: Render Weight Chart
function renderWeightChart(weightData) {
    const canvas = document.getElementById('weightChart');
    if (!canvas)
        return;
    const ctx = canvas.getContext('2d');
    const history = weightData.history || [];
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: history.map(h => new Date(h.date).toLocaleDateString('en-AU', { month: 'short', day: 'numeric' })),
            datasets: [{
                    label: 'Weight (kg)',
                    data: history.map(h => h.weight),
                    borderColor: '#f97316',
                    backgroundColor: 'rgba(249, 115, 22, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3
                }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: { display: false },
                    ticks: { font: { size: 10 } }
                },
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 10 } }
                }
            }
        }
    });
}
// UI: Update Sidebar Stats
function updateSidebar(data) {
    if (!data || !data.project || !data.runner || !data.status)
        return;
    // Update Goal
    const goalEl = document.querySelector('.lg\\:col-span-1 > div:nth-child(1) p:nth-child(2)');
    const dateEl = document.querySelector('.lg\\:col-span-1 > div:nth-child(1) p:nth-child(3)');
    if (goalEl)
        goalEl.innerText = data.project.goal;
    if (dateEl)
        dateEl.innerText = `${data.project.event} • ${new Date(data.project.eventDate).toLocaleDateString('en-AU', { month: 'long', day: 'numeric', year: 'numeric' })}`;
    // Update Phase
    const phaseEl = document.querySelector('.lg\\:col-span-1 > div:nth-child(2) p:nth-child(2)');
    const nextActionEl = document.querySelector('.lg\\:col-span-1 > div:nth-child(2) p:nth-child(3)');
    if (phaseEl)
        phaseEl.innerText = data.status.phase;
    if (nextActionEl)
        nextActionEl.innerText = data.status.nextAction;
    // Update Weight Tracker Card
    const weight = data.runner.weight_kg || { current: 0, target: 0, history: [] };
    const current = weight.current;
    const target = weight.target;
    const history = weight.history || [];
    const start = history.length > 0 ? history[0].weight : current;
    const totalToLose = start - target;
    const lostSoFar = start - current;
    const progressPercent = totalToLose > 0 ? Math.max(0, Math.min(100, (lostSoFar / totalToLose) * 100)) : 0;
    const wCurr = document.getElementById('current-weight');
    const wTarg = document.getElementById('target-weight');
    const wBar = document.getElementById('weight-progress-bar');
    const wMeta = document.getElementById('weight-meta');
    if (wCurr)
        wCurr.textContent = `${current}kg`;
    if (wTarg)
        wTarg.textContent = `/ ${target}kg target`;
    if (wBar)
        wBar.style.width = `${progressPercent}%`;
    if (wMeta)
        wMeta.textContent = `${(current - target).toFixed(1)}kg to lose (${progressPercent.toFixed(0)}% progress)`;
    // Update Context Area
    const contextArea = document.getElementById('context-area');
    if (data.philosophy && contextArea) {
        contextArea.innerHTML = `
            <h2 class="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Strategy</h2>
            <div class="space-y-4">
                <div>
                    <h3 class="font-bold text-slate-900 text-xs uppercase">Cramp Prevention</h3>
                    <ul class="list-disc pl-4 mt-1 text-slate-600">
                        <li>${data.philosophy.crampPrevention.mechanical}</li>
                        <li>${data.philosophy.crampPrevention.metabolic}</li>
                        <li>${data.philosophy.crampPrevention.fueling}</li>
                    </ul>
                </div>
                <div>
                    <h3 class="font-bold text-slate-900 text-xs uppercase">Weekly Structure</h3>
                    <ul class="list-disc pl-4 mt-1 text-slate-600">
                        <li><strong>Wed:</strong> ${data.philosophy.weeklyStructure.Wednesday}</li>
                        <li><strong>Thu:</strong> ${data.philosophy.weeklyStructure.Thursday}</li>
                        <li><strong>Sun:</strong> ${data.philosophy.weeklyStructure.Sunday}</li>
                    </ul>
                </div>
            </div>
        `;
    }
    // Update Zones List
    const zonesList = document.getElementById('zones-list');
    if (data.runner && data.runner.trainingZones && data.runner.trainingZones.pace && zonesList) {
        const zones = data.runner.trainingZones.pace;
        zonesList.innerHTML = zones.map((z, idx) => {
            const lowPace = formatPace(1000 / z.lowBoundary_m_s);
            const nextBoundary = zones[idx + 1] ? zones[idx + 1].lowBoundary_m_s : null;
            const highPace = nextBoundary ? formatPace(1000 / nextBoundary) : '...';
            return `
                <div class="flex justify-between text-[11px]">
                    <span class="font-bold text-slate-500 italic">Z${z.zone}</span>
                    <span class="text-slate-400 font-mono">${lowPace} - ${highPace}/k</span>
                </div>
            `;
        }).join('');
    }
}
function renderRecentActivities(actuals) {
    const list = document.getElementById('activities-list');
    if (!list)
        return;
    if (!actuals || actuals.length === 0) {
        list.innerHTML = '<p class="text-xs text-slate-400 italic">No recent activities found.</p>';
        return;
    }
    list.innerHTML = actuals.slice(0, 5).map(act => {
        const distKm = (act.distance_m / 1000).toFixed(1);
        const paceMinKm = act.average_pace_m_s > 0 ?
            formatPace(1000 / act.average_pace_m_s) : '--:--';
        const date = new Date(act.date).toLocaleDateString('en-AU', { month: 'short', day: 'numeric' });
        const pZones = formatZonesHTML(act.pace_zones, 'pace');
        let impact = [];
        if (act.training_load)
            impact.push(`L:${Math.round(act.training_load)}`);
        const impactStr = impact.length > 0 ? ` (${impact.join(' ')})` : '';
        return `
            <div class="border-b border-slate-50 pb-2 last:border-0">
                <div class="flex justify-between items-start">
                    <div>
                        <p class="text-xs font-bold text-slate-900">${act.name}</p>
                        <p class="text-[10px] text-slate-500">${date} • ${act.type}${impactStr}</p>
                    </div>
                    <div class="text-right">
                        <p class="text-xs font-bold text-green-600">${distKm}k</p>
                        <p class="text-[10px] text-slate-400">${paceMinKm}/k</p>
                    </div>
                </div>
                ${pZones ? `<p class="text-[9px] text-slate-400 mt-1 truncate">P: ${pZones}</p>` : ''}
            </div>
        `;
    }).join('');
}
function renderPlan(weeks, actuals) {
    const tbody = document.getElementById('plan-body');
    if (!tbody)
        return;
    tbody.innerHTML = '';
    if (!Array.isArray(weeks)) {
        console.error('Plan data is not an array:', weeks);
        return;
    }
    // Get AWST today for comparison (UTC+8)
    const awstNow = new Date(new Date().getTime() + (8 * 60 * 60 * 1000));
    const todayStr = awstNow.toISOString().split('T')[0];
    // Group actuals by date
    const actualsByDate = (Array.isArray(actuals) ? actuals : []).reduce((acc, act) => {
        if (!acc[act.date])
            acc[act.date] = [];
        acc[act.date].push(act);
        return acc;
    }, {});
    weeks.forEach((week, index) => {
        const row = document.createElement('tr');
        let rowClass = 'border-b border-slate-100 transition-colors ';
        const status = (week.status || 'normal').toLowerCase();
        let badgeHtml = '';
        if (status === 'taper') {
            rowClass += 'bg-emerald-100 hover:bg-emerald-200 border-l-4 border-emerald-400';
            badgeHtml = '<div class="mt-2 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-200/50 text-[10px] font-bold uppercase text-emerald-800 tracking-wider"><span>📉</span> Taper</div>';
        }
        else if (status === 'rest' || status === 'recovery') {
            rowClass += 'bg-slate-100 hover:bg-slate-200 border-l-4 border-slate-400';
            badgeHtml = '<div class="mt-2 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-200/50 text-[10px] font-bold uppercase text-slate-700 tracking-wider"><span>🧘</span> Recovery</div>';
        }
        else if (status === 'race') {
            rowClass += 'bg-orange-100 hover:bg-orange-200 border-l-4 border-orange-500';
            badgeHtml = '<div class="mt-2 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-orange-200/50 text-[10px] font-bold uppercase text-orange-800 tracking-wider"><span>🏁</span> Race Week</div>';
        }
        else if (status === 'marathon') {
            rowClass += 'bg-yellow-100 hover:bg-yellow-200 border-l-4 border-yellow-600';
            badgeHtml = '<div class="mt-2 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-yellow-400/30 text-[10px] font-black uppercase text-yellow-900 tracking-wider ring-1 ring-yellow-500/20"><span>🏆</span> MARATHON</div>';
        }
        else {
            rowClass += 'hover:bg-slate-50 border-l-4 border-transparent';
        }
        row.className = rowClass;
        row.dataset.start = week.weekStarting;
        let weekTargetM = 0;
        let weekActualM = 0;
        let weekRemainingM = 0;
        // Week Starting Cell
        const date = new Date(week.weekStarting);
        const dateStr = date.toLocaleDateString('en-AU', { month: 'short', day: 'numeric' });
        let html = `
            <td class="p-4 align-top">
                <div class="font-medium text-slate-900">${dateStr}</div>
                <div class="text-[10px] text-slate-400 mt-1 uppercase tracking-wider">Week ${index + 1}</div>
                ${badgeHtml}
                <button onclick='window.printWeek(${index})' class="mt-2 text-[10px] bg-slate-100 hover:bg-slate-200 text-slate-600 px-2 py-1 rounded no-print">
                    Fridge
                </button>
            </td>
        `;
        // Day Cells
        ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].forEach(day => {
            const dayData = week.days[day];
            const dayDate = dayData.date;
            // Planned Workouts
            const plannedHtml = dayData.workouts.map(w => {
                weekTargetM += (w.distance_m || 0);
                if (dayDate > todayStr) {
                    weekRemainingM += (w.distance_m || 0);
                }
                let color = 'text-slate-600';
                if (w.type === 'Intervals')
                    color = 'text-purple-600 font-semibold';
                if (w.type === 'Threshold')
                    color = 'text-red-600 font-semibold';
                if (w.type === 'Steady')
                    color = 'text-blue-600 font-semibold';
                if (w.type === 'Race')
                    color = 'text-orange-600 font-bold';
                return `
                    <div class="mb-1 pb-1 ${dayData.workouts.length > 1 ? 'border-b border-slate-50 last:border-0' : ''}">
                        <div class="text-[9px] uppercase font-black text-slate-400 leading-none mb-0.5">${w.timeOfDay || ''}</div>
                        <div class="${color} leading-tight">${w.name}</div>
                    </div>
                `;
            }).join('');
            // Actual Activities
            const dayActuals = actualsByDate[dayDate] || [];
            const actualHtml = dayActuals.map(act => {
                if (act.type === 'running' || act.type === 'trail_running') {
                    weekActualM += (act.distance_m || 0);
                }
                const distKm = (act.distance_m / 1000).toFixed(1);
                const paceMinKm = act.average_pace_m_s > 0 ?
                    formatPace(1000 / act.average_pace_m_s) : '--:--';
                // Store activity data in a window variable for the modal
                const actId = `act-${act.activityId || Math.random().toString(36).substr(2, 9)}`;
                if (!window.activityStore)
                    window.activityStore = {};
                window.activityStore[actId] = act;
                const typeIcon = act.type === 'cycling' ? '🚲' : act.type === 'swimming' ? '🏊' : '✓';
                const colorClass = act.type === 'running' ? 'text-green-600' : 'text-slate-500';
                return `
                    <div onclick="window.showDetails('${actId}')" class="mt-2 pt-2 border-t border-slate-50 text-[10px] cursor-pointer hover:bg-slate-100 hover:shadow-sm rounded p-1.5 transition-all flex flex-col group relative ring-1 ring-inset ring-transparent hover:ring-slate-200">
                        <div class="flex justify-between items-center text-[9px] mb-0.5">
                            <span class="font-bold uppercase text-slate-400 font-mono tracking-tighter">${act.type}</span>
                        </div>
                        <span class="font-bold ${colorClass} text-[11px]">${typeIcon} ${distKm}k @ ${paceMinKm}</span>
                        <span class="text-slate-900 truncate font-medium">${act.name}</span>
                        <div class="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <svg class="w-3 h-3 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M9 5l7 7-7 7"></path></svg>
                        </div>
                    </div>
                `;
            }).join('');
            html += `
                <td class="p-4 align-top">
                    ${plannedHtml || '<span class="text-slate-300">Rest</span>'}
                    ${actualHtml}
                </td>
            `;
        });
        // Stats Cell
        const targetKm = (weekTargetM / 1000).toFixed(0);
        const actualKm = (weekActualM / 1000).toFixed(1);
        const projectedKm = ((weekActualM + weekRemainingM) / 1000).toFixed(1);
        const diff = (weekActualM + weekRemainingM - weekTargetM) / 1000;
        const diffColor = diff >= 0 ? 'text-green-600' : 'text-red-600';
        const diffSign = diff >= 0 ? '+' : '';
        html += `
            <td class="p-4 align-top text-right bg-slate-50/50">
                <div class="mb-3">
                    <div class="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Target</div>
                    <div class="text-base font-black text-slate-900">${targetKm}k</div>
                </div>
                <div class="mb-3">
                    <div class="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Actual</div>
                    <div class="text-base font-black text-green-600">${actualKm}k</div>
                </div>
                <div>
                    <div class="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Projected</div>
                    <div class="text-base font-black text-blue-600">${projectedKm}k</div>
                    <div class="text-[9px] font-bold ${diffColor}">${diffSign}${diff.toFixed(1)}k vs Target</div>
                </div>
            </td>
        `;
        row.innerHTML = html;
        tbody.appendChild(row);
    });
}
// MAIN ENTRY POINT
function loadDashboard() {
    return __awaiter(this, void 0, void 0, function* () {
        try {
            const fetchJson = (url) => __awaiter(this, void 0, void 0, function* () {
                const r = yield fetch(url);
                if (!r.ok)
                    throw new Error(`Failed to fetch ${url}`);
                return r.json();
            });
            const [planData, contextData, actualsData] = yield Promise.all([
                fetchJson('plan.json').catch(() => []),
                fetchJson('context.json').catch(() => ({})),
                fetchJson('actuals.json').catch(() => [])
            ]);
            window.trainingPlan = planData;
            if (Object.keys(contextData).length === 0) {
                console.error('Context data is empty');
                return;
            }
            updateSidebar(contextData);
            renderPlan(planData, actualsData);
            renderRecentActivities(actualsData);
            if (contextData.runner && contextData.runner.weight_kg) {
                renderWeightChart(contextData.runner.weight_kg);
            }
            highlightCurrentWeek();
            // Update Sync Status
            if (contextData.status) {
                const meta = document.getElementById('sync-meta');
                if (meta)
                    meta.textContent = `Last updated: ${contextData.status.lastUpdated}`;
            }
        }
        catch (error) {
            console.error('Error loading dashboard:', error);
        }
    });
}
// Expose Global Functions for OnClick handlers
window.showDetails = function (actId) {
    const act = window.activityStore[actId];
    if (!act)
        return;
    const title = document.getElementById('modal-title');
    const subtitle = document.getElementById('modal-subtitle');
    const content = document.getElementById('modal-content');
    const backdrop = document.getElementById('modal-backdrop');
    if (title)
        title.textContent = act.name;
    if (subtitle)
        subtitle.textContent = `${new Date(act.date).toLocaleDateString('en-AU', { weekday: 'long', day: 'numeric', month: 'long' })} • ${act.type}`;
    const distKm = (act.distance_m / 1000).toFixed(2);
    const paceMinKm = act.average_pace_m_s > 0 ? formatPace(1000 / act.average_pace_m_s) : '--:--';
    const pZones = formatZonesHTML(act.pace_zones, 'pace');
    const hZones = formatZonesHTML(act.hr_zones, 'hr');
    const wZones = formatZonesHTML(act.power_zones, 'power');
    const aeScore = act.aerobic_te || 0;
    const anScore = act.anaerobic_te || 0;
    const aeData = getTEData(aeScore);
    const anData = getTEData(anScore);
    let html = `
        <div class="grid grid-cols-3 gap-4">
            <div class="bg-slate-50 p-3 rounded-lg">
                <div class="text-[10px] font-bold text-slate-400 uppercase">Distance</div>
                <div class="text-lg font-black text-slate-900">${distKm}k</div>
            </div>
            <div class="bg-slate-50 p-3 rounded-lg">
                <div class="text-[10px] font-bold text-slate-400 uppercase">Avg Pace</div>
                <div class="text-lg font-black text-slate-900">${paceMinKm}/k</div>
            </div>
            <div class="bg-slate-50 p-3 rounded-lg">
                <div class="text-[10px] font-bold text-slate-400 uppercase">Avg HR</div>
                <div class="text-lg font-black text-slate-900">${act.average_hr || '--'} bpm</div>
            </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
            <div class="bg-slate-50 p-3 rounded-lg">
                <div class="text-[10px] font-bold text-slate-400 uppercase">Training Load</div>
                <div class="text-lg font-black text-slate-900">${Math.round(act.training_load || 0)}</div>
            </div>
            <div class="bg-slate-50 p-3 rounded-lg">
                <div class="text-[10px] font-bold text-slate-400 uppercase mb-2">Training Effect</div>
                <div class="grid grid-cols-1 gap-2">
                        <div class="flex items-center justify-between">
                        <div class="flex items-center gap-1.5">
                            <span class="text-xs font-black text-slate-700 w-8">Ae</span>
                            <span class="text-sm font-bold text-slate-900">${aeScore.toFixed(1)}</span>
                        </div>
                        <span class="text-[10px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wide ring-1 ring-inset ${aeData.color}">${aeData.label}</span>
                        </div>
                        <div class="flex items-center justify-between">
                        <div class="flex items-center gap-1.5">
                            <span class="text-xs font-black text-slate-700 w-8">An</span>
                            <span class="text-sm font-bold text-slate-900">${anScore.toFixed(1)}</span>
                        </div>
                        <span class="text-[10px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wide ring-1 ring-inset ${anData.color}">${anData.label}</span>
                        </div>
                </div>
            </div>
        </div>

        <div class="space-y-6">
            ${pZones ? `
                <div>
                    <div class="flex justify-between items-end border-b-2 border-slate-100 pb-1 mb-2">
                        <h4 class="text-[10px] font-black uppercase text-slate-400 tracking-wider">Pace Zones</h4>
                        <span class="text-[9px] text-slate-300 font-bold uppercase">Zone / Avg / Time</span>
                    </div>
                    <div class="space-y-0.5">${pZones}</div>
                </div>
            ` : ''}
            ${hZones ? `
                <div>
                    <div class="flex justify-between items-end border-b-2 border-slate-100 pb-1 mb-2">
                        <h4 class="text-[10px] font-black uppercase text-slate-400 tracking-wider">Heart Rate Zones</h4>
                        <span class="text-[9px] text-slate-300 font-bold uppercase">Zone / Avg / Time</span>
                    </div>
                    <div class="space-y-0.5">${hZones}</div>
                </div>
            ` : ''}
            ${wZones ? `
                <div>
                    <div class="flex justify-between items-end border-b-2 border-slate-100 pb-1 mb-2">
                        <h4 class="text-[10px] font-black uppercase text-slate-400 tracking-wider">Power Zones</h4>
                        <span class="text-[9px] text-slate-300 font-bold uppercase">Zone / Avg / Time</span>
                    </div>
                    <div class="space-y-0.5">${wZones}</div>
                </div>
            ` : ''}
        </div>
    `;
    if (content)
        content.innerHTML = html;
    if (backdrop)
        backdrop.classList.remove('hidden');
};
window.closeModal = function () {
    const backdrop = document.getElementById('modal-backdrop');
    if (backdrop)
        backdrop.classList.add('hidden');
};
window.printWeek = function (index) {
    const week = window.trainingPlan[index];
    const weekNum = index + 1;
    const printSection = document.getElementById('print-section');
    if (!printSection)
        return;
    const dateStr = new Date(week.weekStarting).toLocaleDateString('en-AU', { month: 'long', day: 'numeric', year: 'numeric' });
    let html = `
        <div class="p-6 border-4 border-slate-900 min-h-screen bg-white text-sm">
            <div class="flex justify-between items-baseline mb-6 border-b-4 border-slate-900 pb-3">
                <h1 class="text-3xl font-black uppercase">Week ${weekNum}</h1>
                <p class="text-lg font-bold text-slate-600">Starting ${dateStr}</p>
            </div>

            <div class="space-y-3">
    `;
    ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].forEach(day => {
        const dayData = week.days[day];
        const workouts = dayData.workouts;
        const date = new Date(dayData.date).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' });
        html += `
            <div class="flex items-start gap-6 border-b border-slate-100 pb-2">
                <div class="w-20 flex-shrink-0">
                    <p class="text-lg font-black uppercase leading-none">${day}</p>
                    <p class="text-[11px] font-bold text-slate-400 mt-1">${date}</p>
                </div>
                <div class="flex-grow">
                    ${workouts.length > 0 ? workouts.map((w, idx) => `
                        <div class="flex items-center gap-3 ${idx < workouts.length - 1 ? 'mb-4 pb-4 border-b border-dashed border-slate-200' : 'mb-1'}">
                            <div class="w-6 h-6 border-2 border-slate-900 flex-shrink-0"></div>
                            <div>
                                <p class="text-[11px] font-black uppercase text-slate-400 leading-none mb-1">${w.timeOfDay || 'AM'}</p>
                                <p class="text-lg font-black leading-tight">${w.name}</p>
                            </div>
                        </div>
                    `).join('') : `
                        <div class="flex items-center gap-3">
                            <div class="w-6 h-6 border border-slate-200 flex-shrink-0"></div>
                            <p class="text-base font-bold text-slate-300 uppercase italic">Rest Day</p>
                        </div>
                    `}
                </div>
            </div>
        `;
    });
    html += `
            </div>

            <div class="mt-8 grid grid-cols-2 gap-8 pt-6 border-t-4 border-slate-900">
                <div>
                    <h3 class="text-xs font-black uppercase tracking-widest text-slate-400 mb-2">Paces</h3>
                    <p class="font-bold">Easy: 5:45-6:15 | Steady: 5:10-5:20</p>
                    <p class="font-bold">MP: 5:30-5:40 | <span class="text-red-600">Threshold: 4:40-4:50</span></p>
                </div>
                <div>
                    <h3 class="text-xs font-black uppercase tracking-widest text-slate-400 mb-2">90/900 Rule</h3>
                    <p class="font-bold text-base">90g Carbs + 900mg Sodium / hr</p>
                    <p class="italic text-slate-500 text-xs">Practice on Sunday PLR.</p>
                </div>
            </div>
            
            <div class="mt-6">
                <h3 class="text-xs font-black uppercase tracking-widest text-slate-400 mb-2">Notes / Vitals</h3>
                <div class="h-20 w-full border-2 border-dashed border-slate-200"></div>
            </div>
        </div>
    `;
    printSection.innerHTML = html;
    // Add a small delay for Chrome to render the new content
    setTimeout(() => {
        window.print();
    }, 250);
};
// Initialize
const dateEl = document.getElementById('current-date');
if (dateEl) {
    const now = new Date();
    dateEl.innerText = now.toLocaleDateString('en-AU', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
}
loadDashboard();
