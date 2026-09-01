/**
 * ShopMate AI - User Long-Term Memory & Preferences Manager
 */
const MemoryManager = {
  init() {
    this.loadPreferences();

    const addBtn = document.getElementById('btn-add-memory-modal');
    const modal = document.getElementById('modal-add-memory');
    const form = document.getElementById('add-memory-form');

    if (addBtn && modal) {
      addBtn.addEventListener('click', () => modal.classList.add('active'));
    }

    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const category = document.getElementById('mem-category').value;
        const key = document.getElementById('mem-key').value.trim();
        const value = document.getElementById('mem-val').value.trim();

        try {
          const res = await fetch('/api/memory', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...window.Auth.getAuthHeaders()
            },
            body: JSON.stringify({
              category,
              key,
              value,
              session_id: window.Chat ? window.Chat.sessionId : 'default_session'
            })
          });

          if (!res.ok) throw new Error('Failed to save preference');

          modal.classList.remove('active');
          form.reset();
          this.loadPreferences();
          window.App.showToast('Preference stored in Long-Term Memory!', 'success');
        } catch (err) {
          window.App.showToast(err.message, 'error');
        }
      });
    }
  },

  async loadPreferences() {
    const grid = document.getElementById('memories-grid');
    if (!grid) return;

    try {
      const sessionId = window.Chat ? window.Chat.sessionId : 'default_session';
      const res = await fetch(`/api/memory?session_id=${sessionId}`, {
        headers: window.Auth.getAuthHeaders()
      });
      const data = await res.json();

      if (!data.preferences || data.preferences.length === 0) {
        grid.innerHTML = `
          <div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 3rem 0;">
            <i class="fa-solid fa-brain" style="font-size: 2rem; margin-bottom: 0.75rem; color: var(--text-dim);"></i>
            <p>No user preferences stored yet.</p>
            <p style="font-size: 0.78rem; margin-top: 0.25rem;">ShopMate AI automatically extracts preferences when you chat (e.g. <em>"I prefer Sony headphones"</em> or <em>"My shoe size is 10"</em>).</p>
          </div>
        `;
        return;
      }

      grid.innerHTML = data.preferences.map((m) => {
        return `
          <div class="glass-panel" style="padding: 1rem; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <span style="background: rgba(99, 102, 241, 0.15); color: var(--accent-indigo); padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.72rem; font-weight: 600; text-transform: uppercase;">
                  ${m.category}
                </span>
                <span style="font-size: 0.72rem; color: var(--accent-emerald);">Confidence: 100%</span>
              </div>
              <h4 style="font-size: 0.88rem; color: #fff; margin-bottom: 0.25rem;">${m.key.replace(/_/g, ' ').toUpperCase()}</h4>
              <p style="font-size: 0.95rem; font-weight: 600; color: var(--accent-cyan); margin-bottom: 0.5rem;">${m.value}</p>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.75rem; padding-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.06); font-size: 0.72rem; color: var(--text-dim);">
              <span>${m.created_at || 'Active'}</span>
              <button class="icon-btn" style="width: 24px; height: 24px; font-size: 0.7rem;" title="Delete" onclick="MemoryManager.deletePreference(${m.id})">
                <i class="fa-solid fa-trash-can"></i>
              </button>
            </div>
          </div>
        `;
      }).join('');
    } catch {
      grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--accent-rose);">Failed to load memory cards.</div>`;
    }
  },

  async deletePreference(id) {
    try {
      const res = await fetch(`/api/memory/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete');
      this.loadPreferences();
      window.App.showToast('Memory item removed', 'info');
    } catch (e) {
      window.App.showToast(e.message, 'error');
    }
  }
};

window.MemoryManager = MemoryManager;
