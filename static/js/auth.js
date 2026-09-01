/**
 * ShopMate AI - Authentication, JWT Handler, and Role-Based Access Control (RBAC)
 */
const Auth = {
  tokenKey: 'shopmate_jwt_token',
  userKey: 'shopmate_user_profile',

  getToken() {
    return localStorage.getItem(this.tokenKey);
  },

  getUser() {
    const raw = localStorage.getItem(this.userKey);
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  isLoggedIn() {
    return !!(this.getToken() && this.getUser());
  },

  fillCredentials(username, password, autoSubmit = false) {
    const uInput = document.getElementById('auth-username');
    const pInput = document.getElementById('auth-password');
    if (uInput) uInput.value = username;
    if (pInput) pInput.value = password;
    if (autoSubmit) {
      const form = document.getElementById('auth-form');
      if (form) form.requestSubmit();
    }
  },

  setAuth(token, user) {
    localStorage.setItem(this.tokenKey, token);
    localStorage.setItem(this.userKey, JSON.stringify(user));
    this.updateUI();
    this.applyRolePermissions();
    if (window.App && typeof window.App.loadHomePreferences === 'function') {
      window.App.loadHomePreferences();
    }
  },

  clearAuth() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
    sessionStorage.removeItem('shopmate_signed_in_session');
    window.location.href = '/login?logout=true';
  },

  getAuthHeaders() {
    const token = this.getToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  },

  applyRolePermissions() {
    const user = this.getUser();
    if (!user) return;
    const role = (user.role || 'customer').toLowerCase();

    // 1. AI Navigation Tabs
    const tabChat = document.getElementById('ai-tab-btn-chat');
    const tabRag = document.getElementById('ai-tab-btn-rag');
    const tabMem = document.getElementById('ai-tab-btn-memory');
    const tabAnalytics = document.getElementById('ai-tab-btn-analytics');
    const tabTools = document.getElementById('ai-tab-btn-tools');

    // 2. RAG Panels
    const ragIngestion = document.getElementById('rag-ingestion-panel');
    const ragComp = document.getElementById('rag-comparator-panel');
    const ragGrid = document.getElementById('rag-grid-layout');

    // 3. Tools Lab Panels
    const toolInventory = document.getElementById('tool-inventory-panel');

    if (role === 'customer') {
      // Customer: Access to Chat, Memory, 4-Way RAG (compare only), Tools Lab (NO inventory check)
      if (tabAnalytics) tabAnalytics.style.setProperty('display', 'none', 'important');
      if (tabChat) tabChat.style.setProperty('display', 'inline-flex', 'important');
      if (tabRag) tabRag.style.setProperty('display', 'inline-flex', 'important');
      if (tabMem) tabMem.style.setProperty('display', 'inline-flex', 'important');
      if (tabTools) tabTools.style.setProperty('display', 'inline-flex', 'important');

      // Hide RAG document ingestion
      if (ragIngestion) ragIngestion.style.setProperty('display', 'none', 'important');
      if (ragComp) {
        ragComp.style.setProperty('width', '100%', 'important');
        ragComp.style.setProperty('grid-column', '1 / -1', 'important');
      }
      if (ragGrid) ragGrid.style.setProperty('grid-template-columns', '1fr', 'important');

      // Hide Tools Lab inventory check
      if (toolInventory) toolInventory.style.setProperty('display', 'none', 'important');
    } else if (role === 'support') {
      // Support: Full access except RAG document ingestion
      if (tabAnalytics) tabAnalytics.style.setProperty('display', 'inline-flex', 'important');
      if (tabChat) tabChat.style.display = 'inline-flex';
      if (tabRag) tabRag.style.display = 'inline-flex';
      if (tabMem) tabMem.style.display = 'inline-flex';
      if (tabTools) tabTools.style.display = 'inline-flex';

      // Hide RAG document ingestion
      if (ragIngestion) ragIngestion.style.setProperty('display', 'none', 'important');
      if (ragComp) {
        ragComp.style.setProperty('width', '100%', 'important');
        ragComp.style.setProperty('grid-column', '1 / -1', 'important');
      }
      if (ragGrid) ragGrid.style.setProperty('grid-template-columns', '1fr', 'important');

      // Show Tools Lab inventory check
      if (toolInventory) toolInventory.style.setProperty('display', 'block', 'important');
    } else if (role === 'admin') {
      // Admin: Full access everywhere
      if (tabAnalytics) tabAnalytics.style.setProperty('display', 'inline-flex', 'important');
      if (tabChat) tabChat.style.display = 'inline-flex';
      if (tabRag) tabRag.style.display = 'inline-flex';
      if (tabMem) tabMem.style.display = 'inline-flex';
      if (tabTools) tabTools.style.display = 'inline-flex';

      // Show RAG document ingestion
      if (ragIngestion) ragIngestion.style.setProperty('display', 'block', 'important');
      if (ragComp) {
        ragComp.style.removeProperty('width');
        ragComp.style.removeProperty('grid-column');
      }
      if (ragGrid) ragGrid.style.setProperty('grid-template-columns', '1fr 1fr', 'important');

      // Show Tools Lab inventory check
      if (toolInventory) toolInventory.style.setProperty('display', 'block', 'important');
    }
  },

  updateUI() {
    const user = this.getUser() || { username: 'Guest', full_name: 'Sign In', role: 'guest' };
    const displayName = user.full_name || user.username;
    
    const label = document.getElementById('auth-username-label');
    const topBarUser = document.getElementById('topbar-user-label');
    const modalActive = document.getElementById('modal-active-user-label');
    const modalActiveRole = document.getElementById('modal-active-role-label');
    const modalAddMem = document.getElementById('modal-add-memory-username');
    const aiMemUser = document.getElementById('ai-memory-username');
    const prefUserBadge = document.getElementById('pref-user-badge');

    if (label) {
      label.textContent = `${displayName} (${user.role.toUpperCase()})`;
    }
    if (topBarUser) {
      topBarUser.textContent = displayName;
    }
    if (modalActive) {
      modalActive.textContent = displayName;
    }
    if (modalActiveRole) {
      modalActiveRole.textContent = user.role.toUpperCase();
    }
    if (modalAddMem) {
      modalAddMem.textContent = displayName;
    }
    if (aiMemUser) {
      aiMemUser.textContent = displayName;
    }
    if (prefUserBadge) {
      prefUserBadge.textContent = displayName;
    }
  },

  checkAuthGate(force = false) {
    if (!this.isLoggedIn() || force) {
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
  },

  init() {
    this.updateUI();
    this.applyRolePermissions();
    this.checkAuthGate();
    
    // Auth Modal trigger
    const trigger = document.getElementById('btn-auth-trigger');
    const modal = document.getElementById('modal-auth');
    const form = document.getElementById('auth-form');

    if (trigger && modal) {
      trigger.addEventListener('click', (e) => {
        e.preventDefault();
        modal.classList.add('active');
      });
    }

    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('auth-username').value.trim();
        const password = document.getElementById('auth-password').value.trim();

        try {
          const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
          });

          if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Login failed');
          }

          const data = await res.json();
          sessionStorage.setItem('shopmate_signed_in_session', 'true');
          this.setAuth(data.access_token, data.user);
          modal.classList.remove('active', 'auth-gate-active');
          form.reset();

          // Reset chat session to clear state for the newly logged-in user
          if (window.Chat) {
            window.Chat.sessionId = 'session_' + Math.random().toString(36).substring(2, 9);
            const msgContainer = document.getElementById('chat-messages');
            if (msgContainer) {
              msgContainer.innerHTML = `
                <div id="chat-empty-state" class="custom-empty-state">
                  <p style="text-align: center; color: var(--text-muted); font-size: 14px;">No messages yet. Ask me anything about products, price matching, or policies.</p>
                </div>
              `;
            }
          }

          // Reload long-term memory
          if (window.MemoryManager) {
            window.MemoryManager.loadPreferences();
          }

          window.App.showToast(`Welcome ${data.user.full_name || data.user.username}! Signed in as ${data.user.role.toUpperCase()}`, 'success');
        } catch (err) {
          window.App.showToast(err.message, 'error');
        }
      });
    }
  }
};

window.Auth = Auth;
