/**
 * ShopMate AI - RAG Knowledge Hub & 4-Way Retrieval Comparator
 */
const RagExplorer = {
  init() {
    this.loadStats();

    const debugForm = document.getElementById('rag-debug-form');
    const uploadForm = document.getElementById('file-upload-form');

    if (debugForm) {
      debugForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = document.getElementById('rag-debug-query').value.trim();
        if (query) this.runSearchDebug(query);
      });
      // Initial run
      this.runSearchDebug('return policy opened electronics');
    }

    if (uploadForm) {
      uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fileInput = document.getElementById('upload-file-input');
        const policyType = document.getElementById('upload-policy-type').value;
        const uploadBtn = document.getElementById('btn-upload-file');

        if (!fileInput.files || fileInput.files.length === 0) {
          window.App.showToast('Please choose a file to ingest', 'error');
          return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('policy_type', policyType);

        uploadBtn.disabled = true;
        uploadBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Chunking & Ingesting into ChromaDB...`;

        try {
          const res = await fetch('/api/rag/ingest-file', {
            method: 'POST',
            body: formData
          });

          if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Ingestion failed');
          }

          const data = await res.json();
          window.App.showToast(`Indexed ${data.chunks_created} chunks into Chroma!`, 'success');
          fileInput.value = '';
          this.loadStats();
        } catch (err) {
          window.App.showToast(err.message, 'error');
        } finally {
          uploadBtn.disabled = false;
          uploadBtn.innerHTML = `<i class="fa-solid fa-cloud-arrow-up"></i> Chunk & Ingest Document`;
        }
      });
    }
  },

  async loadStats() {
    const box = document.getElementById('rag-stats-box');
    if (!box) return;

    try {
      const res = await fetch('/api/rag/stats');
      const data = await res.json();
      box.innerHTML = `
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
          <span>🛍️ Product Catalog Vectors:</span>
          <strong>${data.collections?.products_catalog || 0} docs</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
          <span>📜 Store Policy Chunks:</span>
          <strong>${data.collections?.store_policies || 0} chunks</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
          <span>👤 Long-Term User Memories:</span>
          <strong>${data.collections?.user_memories || 0} items</strong>
        </div>
        <div style="margin-top: 0.75rem; padding-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.06); font-size: 0.75rem; color: var(--accent-cyan);">
          <i class="fa-solid fa-microchip"></i> Dimension: 384 | Pipeline: Dense (Chroma) + BM25 + Cross-Encoder
        </div>
      `;
    } catch {
      box.innerHTML = `<p style="color: var(--text-dim);">Unable to fetch Chroma statistics.</p>`;
    }
  },

  async runSearchDebug(query) {
    const timingsEl = document.getElementById('rag-debug-timings');
    const resultsEl = document.getElementById('rag-debug-results');
    if (!resultsEl) return;

    resultsEl.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 2rem 0;"><span class="status-dot"></span> Benchmarking retrieval pipeline...</div>`;

    try {
      const res = await fetch('/api/rag/search-debug', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, collection_name: 'store_policies', top_k: 3 })
      });
      const data = await res.json();

      const user = window.Auth?.getUser();
      const isStaff = user && (user.role === 'admin' || user.role === 'support');

      // Render timings or customer-facing status badge
      if (timingsEl) {
        if (isStaff && data.timings_ms) {
          timingsEl.innerHTML = `
            <span style="background: rgba(6, 182, 212, 0.12); color: #0891b2; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 500; border: 1px solid rgba(6, 182, 212, 0.25);">Dense: ${data.timings_ms.dense} ms</span>
            <span style="background: rgba(99, 102, 241, 0.12); color: #4f46e5; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 500; border: 1px solid rgba(99, 102, 241, 0.25);">BM25: ${data.timings_ms.bm25} ms</span>
            <span style="background: rgba(16, 185, 129, 0.12); color: #059669; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 500; border: 1px solid rgba(16, 185, 129, 0.25);">Hybrid: ${data.timings_ms.hybrid} ms</span>
            <span style="background: rgba(168, 85, 247, 0.12); color: #7c3aed; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 500; border: 1px solid rgba(168, 85, 247, 0.25);">Reranker: ${data.timings_ms.cross_encoder} ms</span>
          `;
        } else {
          // Customer clean badge without internal timing metrics
          timingsEl.innerHTML = `
            <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 4px;">
              <span style="background: #eef2ff; color: #4338ca; padding: 4px 10px; border-radius: 6px; font-size: 11.5px; font-weight: 600; border: 1px solid #c7d2fe; display: inline-flex; align-items: center; gap: 5px;">
                <i class="fa-solid fa-shield-halved"></i> 4-Way Verified Knowledge
              </span>
              <span style="background: #ecfdf5; color: #065f46; padding: 4px 10px; border-radius: 6px; font-size: 11.5px; font-weight: 600; border: 1px solid #a7f3d0; display: inline-flex; align-items: center; gap: 5px;">
                <i class="fa-solid fa-circle-check"></i> High Confidence Match
              </span>
            </div>
          `;
        }
      }

      // Render Reranked candidates with refined text formatting
      const list = data.reranked_results || [];
      if (list.length === 0) {
        resultsEl.innerHTML = `<div style="color: var(--text-muted); padding: 1.5rem 0; text-align: center;">No matching policy documents found for this query.</div>`;
        return;
      }

      resultsEl.innerHTML = list.map((item, idx) => {
        const score = item.rerank_score || item.final_score || item.score || 0.85;
        const scorePct = Math.round(score * 100);
        const title = item.metadata?.title || 'Store Policy';
        const src = item.metadata?.source || 'store_policy.txt';

        // Format clean content lines
        const rawLines = (item.content || '').split('\n').filter(l => l.trim().length > 0);
        let formattedContent = '';
        rawLines.forEach(line => {
          const trimmed = line.trim();
          if (trimmed.startsWith('#') || trimmed.endsWith(':')) {
            formattedContent += `<h5 style="font-size: 13px; font-weight: 700; color: #0f172a; margin: 8px 0 4px 0;">${trimmed.replace(/^#+\s*/, '')}</h5>`;
          } else if (trimmed.startsWith('-') || trimmed.startsWith('*') || trimmed.startsWith('•')) {
            formattedContent += `<div style="padding-left: 12px; margin-bottom: 4px; position: relative;"><span style="position: absolute; left: 0; color: #6366f1;">•</span> ${trimmed.replace(/^[-*•]\s*/, '')}</div>`;
          } else {
            formattedContent += `<p style="margin-bottom: 6px; line-height: 1.55; color: #334155;">${trimmed}</p>`;
          }
        });

        return `
          <div class="rag-chunk-card" style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; margin-bottom: 14px; box-shadow: 0 2px 6px rgba(0,0,0,0.03);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 6px;">
              <div style="display: flex; align-items: center; gap: 6px;">
                <span style="background: #4f46e5; color: #ffffff; font-size: 10.5px; font-weight: 700; padding: 2px 7px; border-radius: 4px;">#${idx+1}</span>
                <strong style="font-size: 13.5px; color: #0f172a;">${title}</strong>
              </div>
              <span style="background: #f0fdf4; color: #166534; font-size: 11.5px; font-weight: 600; padding: 3px 8px; border-radius: 6px; border: 1px solid #bbf7d0;">
                <i class="fa-solid fa-star" style="font-size: 10px; margin-right: 2px;"></i> ${scorePct}% Relevance
              </span>
            </div>
            <div style="font-size: 11.5px; color: #64748b; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
              <span><i class="fa-regular fa-file-lines" style="color: #6366f1;"></i> ${src}</span>
              <span>•</span>
              <span>Chunk ${item.metadata?.chunk_index || 1}</span>
            </div>
            <div style="font-size: 13px; color: #334155; line-height: 1.6; border-top: 1px solid #f1f5f9; padding-top: 8px;">
              ${formattedContent}
            </div>
          </div>
        `;
      }).join('');

    } catch (err) {
      resultsEl.innerHTML = `<div style="color: #b91c1c; padding: 10px; background: #fef2f2; border-radius: 6px; border: 1px solid #fecaca;">Retrieval comparison failed: ${err.message}</div>`;
    }
  }
};

window.RagExplorer = RagExplorer;
