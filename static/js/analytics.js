/**
 * ShopMate AI - Analytics, Telemetry & Automated Benchmark Dashboard
 */
const Analytics = {
  chartLatency: null,
  chartAgents: null,

  init() {
    this.loadOverview();
    this.loadQueryLogs();

    const benchBtn = document.getElementById('btn-run-benchmark');
    if (benchBtn) {
      benchBtn.addEventListener('click', () => this.runBenchmarkSuite());
    }
  },

  async loadOverview() {
    try {
      const res = await fetch('/api/analytics/overview');
      const data = await res.json();

      const elTotal = document.getElementById('stat-total-queries');
      const elLat = document.getElementById('stat-avg-latency');
      const elCritic = document.getElementById('stat-critic-rate');

      if (elTotal) elTotal.textContent = data.total_queries || 0;
      if (elLat) elLat.textContent = `${data.avg_latency_ms || 0} ms`;
      if (elCritic) elCritic.textContent = `${data.critic_pass_rate || 100}%`;

      this.renderCharts(data);
    } catch (e) {
      console.error('Failed loading analytics overview', e);
    }
  },

  renderCharts(data) {
    const ctxLat = document.getElementById('chart-latency');
    const ctxAg = document.getElementById('chart-agents');

    // 1. Latency Breakdown Bar Chart
    if (ctxLat) {
      if (this.chartLatency) this.chartLatency.destroy();
      const latData = data.latency_breakdown || { retrieval_ms: 12, agent_llm_ms: 35, other_ms: 8 };
      
      this.chartLatency = new Chart(ctxLat, {
        type: 'bar',
        data: {
          labels: ['Hybrid Retrieval', 'Agent LLM & Routing', 'Tools & Formatting'],
          datasets: [{
            label: 'Avg Duration (ms)',
            data: [latData.retrieval_ms || 15, latData.agent_llm_ms || 42, latData.other_ms || 9],
            backgroundColor: ['rgba(6, 182, 212, 0.7)', 'rgba(99, 102, 241, 0.7)', 'rgba(168, 85, 247, 0.7)'],
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } },
            x: { ticks: { color: '#9ca3af' } }
          }
        }
      });
    }

    // 2. Agent Distribution Doughnut Chart
    if (ctxAg) {
      if (this.chartAgents) this.chartAgents.destroy();
      const dist = data.agent_distribution || {};
      const labels = Object.keys(dist).length > 0 ? Object.keys(dist) : ['product_agent', 'policy_agent', 'inventory_agent', 'order_agent', 'coupon_agent'];
      const values = Object.keys(dist).length > 0 ? Object.values(dist) : [5, 3, 2, 2, 1];

      this.chartAgents = new Chart(ctxAg, {
        type: 'doughnut',
        data: {
          labels: labels.map(l => l.replace('_', ' ')),
          datasets: [{
            data: values,
            backgroundColor: [
              '#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#a855f7', '#f43f5e'
            ],
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { position: 'bottom', labels: { color: '#d1d5db', boxWidth: 12 } }
          }
        }
      });
    }
  },

  async runBenchmarkSuite() {
    const btn = document.getElementById('btn-run-benchmark');
    const box = document.getElementById('benchmark-results-box');
    if (!box) return;

    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Executing Benchmark Suite...`;
    box.innerHTML = `<div style="text-align: center; padding: 1.5rem 0;"><span class="status-dot"></span> Evaluating Golden Dataset test queries against RAG & Multi-Agent LangGraph...</div>`;

    try {
      const res = await fetch('/api/analytics/benchmark', { method: 'POST' });
      const data = await res.json();

      const pStat = document.getElementById('stat-precision');
      if (pStat) pStat.textContent = `${data.precision_at_k}`;

      let casesHtml = '';
      if (data.details && data.details.test_cases) {
        casesHtml = data.details.test_cases.map((tc) => `
          <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
            <td style="padding: 0.5rem; font-weight: 500;">${tc.query}</td>
            <td style="padding: 0.5rem;"><span style="color: var(--accent-indigo);">${tc.detected_intent}</span></td>
            <td style="padding: 0.5rem;"><span style="color: var(--accent-cyan);">${tc.active_agent}</span></td>
            <td style="padding: 0.5rem;">${tc.routing_correct ? '✅ Pass' : '⚠️ Deviated'}</td>
            <td style="padding: 0.5rem;">${tc.latency_ms} ms</td>
            <td style="padding: 0.5rem; color: var(--accent-emerald);">${Math.round(tc.groundedness * 100)}%</td>
          </tr>
        `).join('');
      }

      box.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.75rem; margin-bottom: 1rem;">
          <div style="background: rgba(255,255,255,0.04); padding: 0.6rem; border-radius: 6px; text-align: center;">
            <div style="font-size: 0.72rem; color: var(--text-muted);">Precision@3</div>
            <div style="font-size: 1.1rem; font-weight: 700; color: var(--accent-emerald);">${(data.precision_at_k * 100).toFixed(1)}%</div>
          </div>
          <div style="background: rgba(255,255,255,0.04); padding: 0.6rem; border-radius: 6px; text-align: center;">
            <div style="font-size: 0.72rem; color: var(--text-muted);">Recall@3</div>
            <div style="font-size: 1.1rem; font-weight: 700; color: var(--accent-cyan);">${(data.recall_at_k * 100).toFixed(1)}%</div>
          </div>
          <div style="background: rgba(255,255,255,0.04); padding: 0.6rem; border-radius: 6px; text-align: center;">
            <div style="font-size: 0.72rem; color: var(--text-muted);">Mean Reciprocal Rank</div>
            <div style="font-size: 1.1rem; font-weight: 700; color: var(--accent-purple);">${data.mrr}</div>
          </div>
          <div style="background: rgba(255,255,255,0.04); padding: 0.6rem; border-radius: 6px; text-align: center;">
            <div style="font-size: 0.72rem; color: var(--text-muted);">Routing Accuracy</div>
            <div style="font-size: 1.1rem; font-weight: 700; color: var(--accent-amber);">${(data.agent_routing_accuracy * 100).toFixed(1)}%</div>
          </div>
          <div style="background: rgba(255,255,255,0.04); padding: 0.6rem; border-radius: 6px; text-align: center;">
            <div style="font-size: 0.72rem; color: var(--text-muted);">Avg Latency</div>
            <div style="font-size: 1.1rem; font-weight: 700; color: #fff;">${data.avg_latency_ms} ms</div>
          </div>
        </div>

        <div style="overflow-x: auto; max-height: 280px;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.78rem;">
            <thead>
              <tr style="color: var(--text-muted); border-bottom: 1px solid var(--border-glass);">
                <th style="padding: 0.4rem; text-align: left;">Test Query</th>
                <th style="padding: 0.4rem; text-align: left;">Intent</th>
                <th style="padding: 0.4rem; text-align: left;">Agent</th>
                <th style="padding: 0.4rem; text-align: left;">Route</th>
                <th style="padding: 0.4rem; text-align: left;">Latency</th>
                <th style="padding: 0.4rem; text-align: left;">Groundedness</th>
              </tr>
            </thead>
            <tbody>${casesHtml}</tbody>
          </table>
        </div>
      `;

      window.App.showToast('Evaluation Benchmark completed!', 'success');
      this.loadOverview();
      this.loadQueryLogs();

    } catch (err) {
      box.innerHTML = `<div style="color: var(--accent-rose);">Benchmark failed: ${err.message}</div>`;
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-play"></i> Run Benchmark Suite`;
    }
  },

  async loadQueryLogs() {
    const tbody = document.getElementById('query-logs-tbody');
    if (!tbody) return;

    try {
      const res = await fetch('/api/analytics/logs?limit=15');
      const data = await res.json();

      if (!data.logs || data.logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="padding: 1.5rem; text-align: center; color: var(--text-dim);">No queries logged yet.</td></tr>`;
        return;
      }

      tbody.innerHTML = data.logs.map((l) => `
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
          <td style="padding: 0.6rem; color: var(--text-dim);">${l.created_at || 'Just now'}</td>
          <td style="padding: 0.6rem; font-weight: 500;">${this.escapeHtml(l.query)}</td>
          <td style="padding: 0.6rem;"><span style="color: var(--accent-indigo);">${l.intent}</span></td>
          <td style="padding: 0.6rem;"><span style="color: var(--accent-cyan);">${l.agent_used}</span></td>
          <td style="padding: 0.6rem;">${l.total_latency_ms} ms</td>
          <td style="padding: 0.6rem;">${l.critic_passed ? '✅ Passed (' + Math.round(l.critic_groundedness * 100) + '%)' : '⚠️ Flagged'}</td>
        </tr>
      `).join('');

    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="6" style="padding: 1rem; color: var(--accent-rose);">Failed to load logs.</td></tr>`;
    }
  },

  escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
};

window.Analytics = Analytics;
