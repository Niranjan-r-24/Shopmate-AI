/**
 * ShopMate AI - Chat & LangGraph Assistant Engine
 */
const Chat = {
  sessionId: 'session_' + Math.random().toString(36).substring(2, 9),

  init() {
    const form = document.getElementById('chat-form');
    const input = document.getElementById('chat-input');
    const clearBtn = document.getElementById('btn-clear-chat');

    if (form && input) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = input.value.trim();
        if (!query) return;
        this.sendMessage(query);
        input.value = '';
      });

      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          form.dispatchEvent(new Event('submit'));
        }
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', async () => {
        await fetch(`/api/chat/history?session_id=${this.sessionId}`, { method: 'DELETE' });
        document.getElementById('chat-messages').innerHTML = `
          <div id="chat-empty-state" class="custom-empty-state">
            <p style="text-align: center; color: var(--text-muted); font-size: 14px;">No messages yet. Ask me anything about your projects.</p>
          </div>
        `;
        window.App.showToast('Chat history cleared', 'info');
      });
    }

    // Bind theme toggle
    const themeBtn = document.getElementById('btn-theme-toggle');
    const chatContainer = document.getElementById('custom-chatbot-container');
    if (themeBtn && chatContainer) {
      themeBtn.addEventListener('click', () => {
        if (chatContainer.classList.contains('pastel-theme')) {
          chatContainer.classList.remove('pastel-theme');
          chatContainer.classList.add('monochrome-theme');
          window.App.showToast('Switched to Monochrome theme', 'info');
        } else {
          chatContainer.classList.remove('monochrome-theme');
          chatContainer.classList.add('pastel-theme');
          window.App.showToast('Switched to Pastel theme', 'success');
        }
      });
    }

    // Bind prompt suggestion pills
    document.querySelectorAll('.prompt-pill').forEach((pill) => {
      pill.addEventListener('click', () => {
        const query = pill.getAttribute('data-query');
        this.sendMessage(query);
      });
    });

    // Inspector tab switcher (safe fallback if panel exists elsewhere)
    document.querySelectorAll('.inspector-tab-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.inspector-tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.inspector-panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        const target = btn.getAttribute('data-inspect');
        const panel = document.getElementById(`inspect-${target}`);
        if (panel) panel.classList.add('active');
      });
    });
  },

  async sendMessage(query) {
    const container = document.getElementById('chat-messages');
    const sendBtn = document.getElementById('btn-send');

    // 1. Append User Message
    this.appendUserMessage(query);
    sendBtn.disabled = true;

    // 2. Append Loading Assistant Bubble (Sparkle loading animation)
    const loadingId = 'loading-' + Date.now();
    const loadingEl = document.createElement('div');
    loadingEl.id = loadingId;
    loadingEl.className = 'custom-msg assistant loading-state';
    loadingEl.innerHTML = `
      <div class="custom-msg-label">OUR AI <i class="fa-solid fa-sparkle loading-sparkle"></i></div>
      <div class="custom-msg-text"><em>Thinking...</em></div>
    `;
    container.appendChild(loadingEl);
    container.scrollTop = container.scrollHeight;

    try {
      const res = await fetch('/api/chat/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...window.Auth.getAuthHeaders()
        },
        body: JSON.stringify({ query, session_id: this.sessionId })
      });

      if (!res.ok) {
        throw new Error(`Server returned error ${res.status}`);
      }

      const data = await res.json();
      loadingEl.remove();

      // 3. Render Assistant Response
      this.appendAssistantMessage(data);

      // Refresh Memory list if in memory tab
      if (window.MemoryManager) {
        window.MemoryManager.loadPreferences();
      }

    } catch (err) {
      loadingEl.remove();
      this.appendErrorMessage(`Failed to get response: ${err.message}`);
    } finally {
      sendBtn.disabled = false;
    }
  },

  appendUserMessage(text) {
    const container = document.getElementById('chat-messages');
    
    // Hide empty state
    const emptyState = document.getElementById('chat-empty-state');
    if (emptyState) emptyState.style.display = 'none';

    const row = document.createElement('div');
    row.className = 'custom-msg user';
    row.innerHTML = `
      <div class="custom-msg-label">ME</div>
      <div class="custom-msg-text">${this.escapeHtml(text)}</div>
    `;
    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
  },

  appendAssistantMessage(data) {
    const container = document.getElementById('chat-messages');
    
    // Hide empty state
    const emptyState = document.getElementById('chat-empty-state');
    if (emptyState) emptyState.style.display = 'none';

    const row = document.createElement('div');
    row.className = 'custom-msg assistant';

    let html = this.formatMarkdown(data.response || '');

    // Render Product Cards Grid if returned
    if (data.product_cards && data.product_cards.length > 0) {
      html += '<div class="product-cards-carousel">';
      data.product_cards.forEach((p) => {
        const inStock = p.stock_count > 0;
        html += `
          <div class="product-item-card">
            <div class="product-img-box">
              <img src="${p.image_url || 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500'}" alt="${this.escapeHtml(p.name)}">
              <span class="product-badge-stock ${inStock ? 'instock' : 'outstock'}">${inStock ? 'In Stock' : 'Out of Stock'}</span>
            </div>
            <div class="product-card-body">
              <span class="product-card-brand">${this.escapeHtml(p.brand || '')}</span>
              <h4 class="product-card-title">${this.escapeHtml(p.name)}</h4>
              <div class="product-card-price-row">
                <span class="product-price-current">₹${Number(p.price).toFixed(2)}</span>
                ${p.original_price > p.price ? `<span class="product-price-original">₹${Number(p.original_price).toFixed(2)}</span>` : ''}
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-top: auto;">
                <span class="product-rating"><i class="fa-solid fa-star"></i> ${p.rating || 4.5}</span>
                <button class="btn-card-action" onclick="Chat.sendMessage('Check inventory and details for SKU ${p.sku}')">Inspect</button>
              </div>
            </div>
          </div>
        `;
      });
      html += '</div>';
    }

    // Render Citations bar if present
    if (data.citations && data.citations.length > 0) {
      html += '<div style="margin-top: 0.75rem; display: flex; flex-wrap: wrap; gap: 0.4rem; font-size: 0.75rem;">';
      data.citations.forEach((c) => {
        html += `
          <span style="background: rgba(79, 70, 229, 0.08); color: var(--accent-primary); padding: 0.25rem 0.6rem; border-radius: 4px; border: 1px solid rgba(79, 70, 229, 0.2); font-weight: 500;">
            <i class="fa-solid fa-book-bookmark"></i> ${this.escapeHtml(c.title || c.source)}
          </span>
        `;
      });
      html += '</div>';
    }

    // Role-based Footer & Feedback bar
    const currentUser = window.Auth?.getUser();
    const isStaff = currentUser && (currentUser.role === 'admin' || currentUser.role === 'support');
    const footerLabel = isStaff 
      ? `Agent: <strong>${data.active_agent || 'ShopMate'}</strong> | Latency: <strong>${data.metrics?.total_latency_ms || 0} ms</strong>`
      : `<span style="display: inline-flex; align-items: center; gap: 4px; color: var(--text-muted);"><i class="fa-solid fa-wand-magic-sparkles" style="color: var(--accent-primary);"></i> ShopMate AI Concierge</span>`;

    html += `
      <div style="margin-top: 0.75rem; padding-top: 0.5rem; border-top: 1px solid rgba(0,0,0,0.06); display: flex; justify-content: space-between; align-items: center; font-size: 0.72rem; color: var(--text-secondary);">
        <span>${footerLabel}</span>
        <div style="display: flex; gap: 0.4rem;">
          <button class="icon-btn" style="width: 24px; height: 24px; font-size: 0.7rem; border-radius: 4px;" title="Helpful" onclick="Chat.submitFeedback('${data.request_id}', 'thumbs_up', this)">
            <i class="fa-solid fa-thumbs-up"></i>
          </button>
          <button class="icon-btn" style="width: 24px; height: 24px; font-size: 0.7rem; border-radius: 4px;" title="Not helpful" onclick="Chat.submitFeedback('${data.request_id}', 'thumbs_down', this)">
            <i class="fa-solid fa-thumbs-down"></i>
          </button>
        </div>
      </div>
    `;

    row.innerHTML = `
      <div class="custom-msg-label">OUR AI</div>
      <div class="custom-msg-text">${html}</div>
    `;
    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
  },

  appendErrorMessage(text) {
    const container = document.getElementById('chat-messages');
    
    // Hide empty state
    const emptyState = document.getElementById('chat-empty-state');
    if (emptyState) emptyState.style.display = 'none';

    const row = document.createElement('div');
    row.className = 'custom-msg assistant error';
    row.innerHTML = `
      <div class="custom-msg-label" style="color: var(--accent-rose);">OUR AI</div>
      <div class="custom-msg-text" style="color: var(--accent-rose); border-color: rgba(244, 63, 94, 0.2);"><p>${this.escapeHtml(text)}</p></div>
    `;
    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
  },

  renderTimeline(trace) {
    const container = document.getElementById('timeline-container');
    if (!container) return;

    if (!trace || trace.length === 0) {
      container.innerHTML = `<p style="color: var(--text-dim); font-size: 0.8rem;">No trace steps recorded.</p>`;
      return;
    }

    const nodeIcons = {
      router: 'fa-route',
      product_agent: 'fa-box-open',
      policy_agent: 'fa-file-shield',
      inventory_agent: 'fa-warehouse',
      order_agent: 'fa-truck-fast',
      return_agent: 'fa-rotate-left',
      coupon_agent: 'fa-ticket',
      general_chat_agent: 'fa-comment-dots',
      critic_guardrails: 'fa-shield-halved',
      critic: 'fa-shield-halved',
      response_formatter: 'fa-check-double'
    };

    container.innerHTML = trace.map((step) => {
      const icon = nodeIcons[step.node] || 'fa-circle-nodes';
      const isWarn = step.status === 'warning';
      const metaJson = step.details && Object.keys(step.details).length > 0
        ? `<div class="timeline-meta-box">${this.escapeHtml(JSON.stringify(step.details, null, 2))}</div>`
        : '';

      return `
        <div class="timeline-item ${isWarn ? 'warning' : ''}">
          <div class="timeline-node-icon"><i class="fa-solid ${icon}"></i></div>
          <div class="timeline-details">
            <div class="timeline-title-row">
              <span class="timeline-node-name">${step.node.replace('_', ' ')}</span>
              <span class="timeline-duration">${step.duration_ms} ms</span>
            </div>
            <div class="timeline-action">${this.escapeHtml(step.action)}</div>
            ${metaJson}
          </div>
        </div>
      `;
    }).join('');
  },

  renderChunks(chunks, citations) {
    const container = document.getElementById('chunks-container');
    if (!container) return;

    const list = citations && citations.length > 0 ? citations : chunks;
    if (!list || list.length === 0) {
      container.innerHTML = `<p style="color: var(--text-dim); font-size: 0.8rem; text-align: center; padding: 1.5rem 0;">No chunks retrieved for this query.</p>`;
      return;
    }

    container.innerHTML = list.map((item, idx) => {
      const score = item.score || item.rerank_score || item.final_score || 0.85;
      const scorePct = Math.round(score * 100);
      const title = item.title || item.metadata?.title || item.metadata?.name || item.id || `Chunk #${idx+1}`;
      const src = item.source || item.metadata?.source || 'ChromaDB';

      return `
        <div class="chunk-card">
          <div class="chunk-card-header">
            <span class="chunk-badge"><i class="fa-solid fa-database"></i> ${this.escapeHtml(src)}</span>
            <span class="chunk-score">${scorePct}% Match</span>
          </div>
          <div style="font-weight: 600; color: #fff; margin-bottom: 0.35rem; font-size: 0.82rem;">${this.escapeHtml(title)}</div>
          <div class="chunk-content">${this.escapeHtml(item.content || '')}</div>
        </div>
      `;
    }).join('');
  },

  renderTelemetry(data) {
    const tIntent = document.getElementById('telemetry-intent');
    const tAgent = document.getElementById('telemetry-agent');
    const tLatency = document.getElementById('telemetry-latency');
    const tGroundedness = document.getElementById('telemetry-groundedness');
    const tGuardrails = document.getElementById('telemetry-guardrails');

    if (tIntent) tIntent.textContent = data.intent || 'N/A';
    if (tAgent) tAgent.textContent = data.active_agent || 'N/A';
    if (tLatency) tLatency.textContent = `${data.metrics?.total_latency_ms || 0} ms`;
    if (tGroundedness) tGroundedness.textContent = `${data.critic_review?.groundedness_score || 1.0}`;
    if (tGuardrails) {
      const safe = data.guardrail_status?.safe !== false;
      tGuardrails.textContent = safe ? 'Passed (Safe)' : 'Triggered Violation';
      tGuardrails.style.color = safe ? 'var(--accent-emerald)' : 'var(--accent-rose)';
    }
  },

  async submitFeedback(requestId, feedback, btn) {
    try {
      await fetch('/api/chat/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_id: requestId, feedback })
      });
      btn.style.color = feedback === 'thumbs_up' ? 'var(--accent-emerald)' : 'var(--accent-rose)';
      window.App.showToast('Thank you for your feedback!', 'success');
    } catch {
      window.App.showToast('Failed to record feedback', 'error');
    }
  },

  formatMarkdown(text) {
    if (!text) return '';

    // 1. Code blocks (```lang ... ```)
    let processed = text.replace(/```([\s\S]*?)```/g, (match, code) => {
      return `<pre class="chat-code-block"><code>${this.escapeHtml(code.trim())}</code></pre>`;
    });

    // 2. Tables (| col1 | col2 |)
    const lines = processed.split('\n');
    let inTable = false;
    let tableHtml = '';
    let newLines = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (line.startsWith('|') && line.endsWith('|')) {
        const rawCells = line.split('|');
        const cells = rawCells.slice(1, rawCells.length - 1).map(c => c.trim());
        const isSeparator = cells.every(c => /^:?-+:?$/.test(c));
        
        if (!inTable) {
          inTable = true;
          tableHtml = '<div class="chat-table-wrapper"><table class="chat-markdown-table"><thead><tr>';
          cells.forEach(c => { tableHtml += `<th>${this.formatInline(c)}</th>`; });
          tableHtml += '</tr></thead><tbody>';
        } else if (isSeparator) {
          continue;
        } else {
          tableHtml += '<tr>';
          cells.forEach(c => { tableHtml += `<td>${this.formatInline(c)}</td>`; });
          tableHtml += '</tr>';
        }
      } else {
        if (inTable) {
          tableHtml += '</tbody></table></div>';
          newLines.push(tableHtml);
          inTable = false;
          tableHtml = '';
        }
        newLines.push(line);
      }
    }
    if (inTable) {
      tableHtml += '</tbody></table></div>';
      newLines.push(tableHtml);
    }

    // 3. Process remaining lines (Headers, Lists, Blockquotes, Paragraphs)
    let finalHtml = '';
    let inUl = false;
    let inOl = false;

    newLines.forEach(line => {
      if (line.startsWith('<div class="chat-table-wrapper">') || line.startsWith('<pre class="chat-code-block">')) {
        if (inUl) { finalHtml += '</ul>'; inUl = false; }
        if (inOl) { finalHtml += '</ol>'; inOl = false; }
        finalHtml += line;
        return;
      }

      if (/^###\s+(.*)/.test(line)) {
        if (inUl) { finalHtml += '</ul>'; inUl = false; }
        if (inOl) { finalHtml += '</ol>'; inOl = false; }
        const match = line.match(/^###\s+(.*)/);
        finalHtml += `<h4 class="chat-h4">${this.formatInline(match[1])}</h4>`;
      } else if (/^##\s+(.*)/.test(line)) {
        if (inUl) { finalHtml += '</ul>'; inUl = false; }
        if (inOl) { finalHtml += '</ol>'; inOl = false; }
        const match = line.match(/^##\s+(.*)/);
        finalHtml += `<h3 class="chat-h3">${this.formatInline(match[1])}</h3>`;
      } else if (/^#\s+(.*)/.test(line)) {
        if (inUl) { finalHtml += '</ul>'; inUl = false; }
        if (inOl) { finalHtml += '</ol>'; inOl = false; }
        const match = line.match(/^#\s+(.*)/);
        finalHtml += `<h3 class="chat-h3">${this.formatInline(match[1])}</h3>`;
      } else if (/^[-*•]\s+(.*)/.test(line)) {
        if (inOl) { finalHtml += '</ol>'; inOl = false; }
        if (!inUl) { finalHtml += '<ul class="chat-ul">'; inUl = true; }
        const match = line.match(/^[-*•]\s+(.*)/);
        finalHtml += `<li>${this.formatInline(match[1])}</li>`;
      } else if (/^\d+\.\s+(.*)/.test(line)) {
        if (inUl) { finalHtml += '</ul>'; inUl = false; }
        if (!inOl) { finalHtml += '<ol class="chat-ol">'; inOl = true; }
        const match = line.match(/^\d+\.\s+(.*)/);
        finalHtml += `<li>${this.formatInline(match[1])}</li>`;
      } else if (/^>\s+(.*)/.test(line)) {
        if (inUl) { finalHtml += '</ul>'; inUl = false; }
        if (inOl) { finalHtml += '</ol>'; inOl = false; }
        const match = line.match(/^>\s+(.*)/);
        finalHtml += `<blockquote class="chat-blockquote">${this.formatInline(match[1])}</blockquote>`;
      } else if (line.trim() === '') {
        if (inUl) { finalHtml += '</ul>'; inUl = false; }
        if (inOl) { finalHtml += '</ol>'; inOl = false; }
      } else {
        if (inUl) { finalHtml += '</ul>'; inUl = false; }
        if (inOl) { finalHtml += '</ol>'; inOl = false; }
        finalHtml += `<p class="chat-p">${this.formatInline(line)}</p>`;
      }
    });

    if (inUl) finalHtml += '</ul>';
    if (inOl) finalHtml += '</ol>';

    return finalHtml;
  },

  formatInline(text) {
    if (!text) return '';
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code class="chat-inline-code">$1</code>')
      .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" class="chat-link">$1</a>');
  },

  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
};

window.Chat = Chat;
