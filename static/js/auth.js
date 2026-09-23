/**
 * ShopMate AI - Authentication, JWT Handler, and Role-Based Access Control (RBAC)
 */
const Auth = {
  tokenKey: 'shopmate_jwt_token',
  refreshTokenKey: 'shopmate_refresh_token',
  userKey: 'shopmate_user_profile',

  getToken() {
    return localStorage.getItem(this.tokenKey);
  },

  getRefreshToken() {
    return localStorage.getItem(this.refreshTokenKey);
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

  setAuth(token, user, refreshToken = null) {
    localStorage.setItem(this.tokenKey, token);
    if (refreshToken) {
      localStorage.setItem(this.refreshTokenKey, refreshToken);
    }
    localStorage.setItem(this.userKey, JSON.stringify(user));
    this.updateUI();
    this.applyRolePermissions();
    if (window.App && typeof window.App.loadHomePreferences === 'function') {
      window.App.loadHomePreferences();
    }
  },

  clearAuth() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.refreshTokenKey);
    localStorage.removeItem(this.userKey);
    sessionStorage.removeItem('shopmate_signed_in_session');
    window.location.href = '/login?logout=true';
  },

  getAuthHeaders() {
    const token = this.getToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  },

  async refreshToken() {
    const refToken = this.getRefreshToken();
    if (!refToken) {
      this.clearAuth();
      return null;
    }
    try {
      const res = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refToken })
      });
      if (!res.ok) {
        this.clearAuth();
        return null;
      }
      const data = await res.json();
      localStorage.setItem(this.tokenKey, data.access_token);
      if (data.refresh_token) {
        localStorage.setItem(this.refreshTokenKey, data.refresh_token);
      }
      return data.access_token;
    } catch {
      this.clearAuth();
      return null;
    }
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
    const displayName = user.full_name || user.username || 'Account';
    
    const label = document.getElementById('auth-username-label');
    const topBarUser = document.getElementById('topbar-user-label');
    const modalActive = document.getElementById('modal-active-user-label');
    const modalActiveRole = document.getElementById('modal-active-role-label');
    const modalAddMem = document.getElementById('modal-add-memory-username');
    const aiMemUser = document.getElementById('ai-memory-username');
    const prefUserBadge = document.getElementById('pref-user-badge');

    if (label) {
      label.textContent = `${displayName} (${(user.role || 'GUEST').toUpperCase()})`;
    }
    if (topBarUser) {
      topBarUser.textContent = displayName;
    }
    if (modalActive) {
      modalActive.textContent = displayName;
    }
    if (modalActiveRole) {
      modalActiveRole.textContent = (user.role || '').toUpperCase();
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
      if (window.location.pathname !== '/login' && window.location.pathname !== '/signup') {
        window.location.href = '/login';
      }
    }
  },

  init() {
    this.updateUI();
    this.applyRolePermissions();
    this.checkAuthGate();
  }
};

window.Auth = Auth;
