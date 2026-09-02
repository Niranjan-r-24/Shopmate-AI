/**
 * ShopMate AI - Master Application Coordinator (Coza Store Luxury Edition)
 */
const App = {
  init() {
    // 1. Topbar and Auth triggers
    const topBarUser = document.getElementById('topbar-user-btn');
    if (topBarUser) {
      topBarUser.addEventListener('click', () => {
        document.getElementById('modal-auth').classList.add('active');
      });
    }

    // 2. Hero AI Search Bar
    const heroSearchForm = document.getElementById('hero-ai-search-form');
    const heroSearchInput = document.getElementById('hero-search-input');
    if (heroSearchForm && heroSearchInput) {
      heroSearchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const q = heroSearchInput.value.trim();
        if (q) {
          this.openAiConcierge('chat', q);
          heroSearchInput.value = '';
        }
      });
    }

    // 3. Hero Prompt Pills
    document.querySelectorAll('.hero-prompt-pill').forEach((pill) => {
      pill.addEventListener('click', () => {
        const query = pill.getAttribute('data-query');
        this.openAiConcierge('chat', query);
      });
    });

    // 4. Cart Drawer Toggles
    const cartTrigger = document.getElementById('btn-cart-drawer-trigger');
    const cartDrawerOverlay = document.getElementById('cart-drawer-overlay');
    const cartCloseBtn = document.getElementById('btn-close-cart-drawer');
    if (cartTrigger && cartDrawerOverlay) {
      cartTrigger.addEventListener('click', () => cartDrawerOverlay.classList.add('active'));
    }
    if (cartCloseBtn && cartDrawerOverlay) {
      cartCloseBtn.addEventListener('click', () => cartDrawerOverlay.classList.remove('active'));
    }
    if (cartDrawerOverlay) {
      cartDrawerOverlay.addEventListener('click', (e) => {
        if (e.target === cartDrawerOverlay) cartDrawerOverlay.classList.remove('active');
      });
    }

    // 5. Wishlist Trigger Toast
    const wishlistBtn = document.getElementById('btn-wishlist-trigger');
    if (wishlistBtn) {
      wishlistBtn.addEventListener('click', () => {
        const user = window.Auth ? window.Auth.getUser() : { username: 'niranjan', full_name: 'Niranjan R' };
        const wishlist = window.Catalog ? window.Catalog.getWishlist() : [];
        const count = wishlist.length;
        const displayName = user.full_name || user.username;
        if (count === 0) {
          this.showToast(`${displayName}: Your Wishlist is currently empty.`, 'info');
        } else {
          const names = wishlist.map(item => item.name).join(', ');
          this.showToast(`${displayName}: ${count} luxury items saved in your Wishlist: ${names}`, 'success');
        }
      });
    }

    // 6. Newsletter Subscription
    const newsForm = document.getElementById('newsletter-form');
    if (newsForm) {
      newsForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.showToast('Welcome to the VIP Circle! ₹2000 luxury voucher applied: VIP10', 'success');
        newsForm.reset();
      });
    }

    // 7. Expandable Filter Toggle in Store
    const filterToggleBtn = document.getElementById('btn-toggle-filter-panel');
    const filterPanel = document.getElementById('filter-expandable-box');
    if (filterToggleBtn && filterPanel) {
      filterToggleBtn.addEventListener('click', () => {
        filterPanel.classList.toggle('active');
        filterToggleBtn.classList.toggle('active');
      });
    }

    // 8. AI Concierge Tab Switcher
    document.querySelectorAll('.ai-tab-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-aitab');
        this.switchAiTab(tab);
      });
    });

    // 9. Modal Closures
    document.querySelectorAll('.modal-overlay').forEach((modal) => {
      modal.addEventListener('click', (e) => {
        if (modal.classList.contains('auth-gate-active')) return;
        if (e.target === modal) modal.classList.remove('active');
      });
    });
    document.querySelectorAll('.close-modal').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.modal-overlay:not(.auth-gate-active)').forEach(m => m.classList.remove('active'));
        const concierge = document.getElementById('modal-ai-concierge');
        if (concierge) concierge.classList.remove('active');
      });
    });

    // 10. Initialize Subsystem Modules
    if (window.Auth) window.Auth.init();
    if (window.Chat) window.Chat.init();
    if (window.Catalog) window.Catalog.init();
    if (window.RagExplorer) window.RagExplorer.init();
    if (window.MemoryManager) window.MemoryManager.init();
    if (window.Analytics) window.Analytics.init();

    // 11. Initialize Home Preferences & Tools Lab
    this.initHomePreferences();
    this.initToolsLab();
  },

  initHomePreferences() {
    this.loadHomePreferences();

    const form = document.getElementById('home-pref-form');
    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const cat = document.getElementById('home-pref-cat').value;
        const key = document.getElementById('home-pref-key').value.trim();
        const val = document.getElementById('home-pref-val').value.trim();
        if (!key || !val) return;

        try {
          const user = window.Auth ? window.Auth.getUser() : null;
          const username = (user && user.username) ? user.username : 'niranjan';

          const res = await fetch(`/api/memory/${username}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(window.Auth ? window.Auth.getAuthHeaders() : {})
            },
            body: JSON.stringify({ category: cat, key, value: val })
          });

          if (!res.ok) throw new Error('Failed to save preference');

          this.showToast(`Preference '${key}' saved!`, 'success');
          form.reset();
          this.loadHomePreferences();
          if (window.MemoryManager) window.MemoryManager.loadPreferences();
        } catch (err) {
          this.showToast(err.message, 'error');
        }
      });
    }
  },

  fillPrefForm(cat, key, val) {
    const cEl = document.getElementById('home-pref-cat');
    const kEl = document.getElementById('home-pref-key');
    const vEl = document.getElementById('home-pref-val');
    if (cEl) cEl.value = cat;
    if (kEl) kEl.value = key;
    if (vEl) vEl.value = val;
    if (kEl) kEl.focus();
  },

  async loadHomePreferences() {
    const list = document.getElementById('home-pref-list');
    if (!list) return;

    const user = window.Auth ? window.Auth.getUser() : null;
    const username = (user && user.username) ? user.username : 'niranjan';

    try {
      const res = await fetch(`/api/memory/${username}`, {
        headers: window.Auth ? window.Auth.getAuthHeaders() : {}
      });
      if (!res.ok) throw new Error('Failed to load');
      const data = await res.json();
      const prefs = data.preferences || [];

      if (prefs.length === 0) {
        list.innerHTML = `
          <div style="grid-column: 1 / -1; padding: 16px; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px; text-align: center; color: #64748b; font-size: 13px;">
            No custom preferences set yet. Use the presets on the right to personalize your recommendations!
          </div>
        `;
        return;
      }

      list.innerHTML = prefs.map(p => `
        <div class="pref-pill-box">
          <div>
            <div class="pref-pill-category">${p.category || 'general'}</div>
            <div class="pref-pill-key">${p.key}</div>
            <div class="pref-pill-val">${p.value}</div>
          </div>
          <button class="pref-pill-del" onclick="App.deleteHomePreference('${p.key}')" title="Remove preference">
            <i class="fa-solid fa-trash-can"></i>
          </button>
        </div>
      `).join('');
    } catch {
      list.innerHTML = `<div style="grid-column: 1 / -1; color: #ef4444; font-size: 12px;">Sign in to view saved preferences.</div>`;
    }
  },

  async deleteHomePreference(key) {
    const user = window.Auth ? window.Auth.getUser() : null;
    const username = (user && user.username) ? user.username : 'niranjan';

    try {
      const res = await fetch(`/api/memory/${username}/${encodeURIComponent(key)}`, {
        method: 'DELETE',
        headers: window.Auth ? window.Auth.getAuthHeaders() : {}
      });
      if (!res.ok) throw new Error('Failed to delete');
      this.showToast(`Preference '${key}' removed.`, 'info');
      this.loadHomePreferences();
      if (window.MemoryManager) window.MemoryManager.loadPreferences();
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  openAiConcierge(tab = 'chat', initialQuery = null) {
    const modal = document.getElementById('modal-ai-concierge');
    if (!modal) return;
    modal.classList.add('active');
    if (window.Auth) window.Auth.applyRolePermissions();
    this.switchAiTab(tab);

    if (initialQuery && window.Chat) {
      window.Chat.sendMessage(initialQuery);
    }
  },

  closeAiConcierge() {
    const modal = document.getElementById('modal-ai-concierge');
    if (modal) modal.classList.remove('active');
  },

  switchAiTab(tabName) {
    const user = window.Auth ? window.Auth.getUser() : null;
    const role = (user && user.role) ? user.role.toLowerCase() : 'customer';

    // Prevent customer from switching to hidden analytics tab
    if (role === 'customer' && tabName === 'analytics') {
      tabName = 'chat';
    }

    document.querySelectorAll('.ai-tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.ai-view-pane').forEach(p => p.classList.remove('active'));

    const btn = document.querySelector(`.ai-tab-btn[data-aitab="${tabName}"]`);
    const pane = document.getElementById(`ai-pane-${tabName}`);

    if (btn) btn.classList.add('active');
    if (pane) pane.classList.add('active');

    if (window.Auth) window.Auth.applyRolePermissions();

    // Trigger tab specific loads
    if (tabName === 'memory' && window.MemoryManager) window.MemoryManager.loadPreferences();
    if (tabName === 'analytics' && window.Analytics) {
      window.Analytics.loadOverview();
    }
    if (tabName === 'rag' && window.RagExplorer) window.RagExplorer.loadStats();
  },

  applyCartCoupon() {
    const input = document.getElementById('cart-coupon-input');
    const code = input ? input.value.trim().toUpperCase() : '';
    if (!code) {
      this.showToast('Please enter a coupon code (e.g. SAVE20)', 'error');
      return;
    }
    if (code === 'SAVE20') {
      document.getElementById('cart-subtotal-display').textContent = '$159.99 (20% Off)';
      this.showToast('Promo code SAVE20 applied! Saved $40.00', 'success');
    } else if (code === 'FREESHIP') {
      this.showToast('Free Expedited Delivery Applied!', 'success');
    } else if (code === 'VIP10') {
      document.getElementById('cart-subtotal-display').textContent = '$179.99 (10% Off)';
      this.showToast('VIP10 Member discount applied!', 'success');
    } else {
      this.showToast(`Validating coupon '${code}' with ShopMate AI...`, 'info');
      this.openAiConcierge('chat', `Can I apply coupon code ${code} on my cart?`);
    }
  },

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast';
    
    const colors = {
      success: 'var(--accent-emerald)',
      error: 'var(--accent-rose)',
      info: 'var(--accent-primary)'
    };
    toast.style.borderColor = colors[type] || 'var(--border-glass)';

    toast.innerHTML = `
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span style="color: ${colors[type] || '#fff'};">●</span>
        <span>${message}</span>
      </div>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  },

  /**
   * Formats raw Tool execution responses into clean, styled UI Cards
   */
  /**
   * Formats raw Tool execution responses into clean, luxury styled UI Cards
   */
  formatToolResult(data, toolType) {
    if (!data) return `<div class="tool-result-card"><p style="color: #ef4444;">No data returned from tool execution.</p></div>`;

    const status = data.status || (data.valid ? 'success' : (data.eligible ? 'success' : 'info'));
    const isSuccess = ['success', 'available', 'valid', 'approved'].includes(String(status).toLowerCase()) || data.valid === true || data.eligible === true;
    const isNotFound = ['not_found', 'invalid', 'expired', 'ineligible', 'error'].includes(String(status).toLowerCase()) || data.valid === false || data.eligible === false;
    
    const badgeClass = isSuccess ? 'badge-success' : (isNotFound ? 'badge-error' : 'badge-info');
    const badgeIcon = isSuccess ? 'fa-circle-check' : (isNotFound ? 'fa-circle-xmark' : 'fa-circle-info');
    const badgeText = isSuccess ? (status === 'success' ? 'Verified / Success' : status.toUpperCase()) : (status ? status.replace(/_/g, ' ').toUpperCase() : 'Notice');

    let metaItems = '';
    let extraSection = '';

    if (toolType === 'inventory') {
      if (data.product) {
        metaItems = `
          <div class="tool-meta-item">
            <div class="tool-meta-label">Product Name</div>
            <div class="tool-meta-value">${data.product.name || 'N/A'}</div>
          </div>
          <div class="tool-meta-item">
            <div class="tool-meta-label">SKU</div>
            <div class="tool-meta-value"><code>${data.product.sku || 'N/A'}</code></div>
          </div>
          <div class="tool-meta-item">
            <div class="tool-meta-label">Stock Units</div>
            <div class="tool-meta-value" style="font-weight: 700; color: ${data.product.in_stock ? '#10b981' : '#ef4444'};">${data.product.stock_count ?? 'N/A'} units in warehouse</div>
          </div>
          <div class="tool-meta-item">
            <div class="tool-meta-label">Catalog Status</div>
            <div class="tool-meta-value">${data.product.in_stock ? '✅ Available for Order' : '❌ Currently Out of Stock'}</div>
          </div>
        `;
      }
    } else if (toolType === 'order') {
      if (data.order) {
        metaItems = `
          <div class="tool-meta-item">
            <div class="tool-meta-label">Order Number</div>
            <div class="tool-meta-value"><code>${data.order.order_number || 'N/A'}</code></div>
          </div>
          <div class="tool-meta-item">
            <div class="tool-meta-label">Status</div>
            <div class="tool-meta-value" style="font-weight: 700; color: #6366f1;">${data.order.status || 'N/A'}</div>
          </div>
          <div class="tool-meta-item">
            <div class="tool-meta-label">Courier & Tracking</div>
            <div class="tool-meta-value">${data.order.courier || 'Expedited'} (<code>${data.order.tracking_number || 'TRK-LIVE'}</code>)</div>
          </div>
          <div class="tool-meta-item">
            <div class="tool-meta-label">Estimated Delivery</div>
            <div class="tool-meta-value">${data.order.estimated_delivery ? new Date(data.order.estimated_delivery).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' }) : 'Pending Dispatch'}</div>
          </div>
        `;
      }
    } else if (toolType === 'coupon') {
      const discount = parseFloat(data.discount_amount) || 0.0;
      const cartTotal = parseFloat(data.cart_total) || 0.0;
      const finalTotal = parseFloat(data.final_total) || 0.0;
      metaItems = `
        <div class="tool-meta-item">
          <div class="tool-meta-label">Promo Code</div>
          <div class="tool-meta-value"><code style="color: #6366f1; font-weight: 700;">${data.coupon_code || 'N/A'}</code></div>
        </div>
        <div class="tool-meta-item">
          <div class="tool-meta-label">Instant Savings</div>
          <div class="tool-meta-value" style="color: #10b981; font-weight: 700;">-$${discount.toFixed(2)}</div>
        </div>
        <div class="tool-meta-item">
          <div class="tool-meta-label">Original Cart</div>
          <div class="tool-meta-value">$${cartTotal.toFixed(2)}</div>
        </div>
        <div class="tool-meta-item">
          <div class="tool-meta-label">Final Payable Subtotal</div>
          <div class="tool-meta-value" style="font-weight: 700; color: #06b6d4;">$${finalTotal.toFixed(2)}</div>
        </div>
      `;
    } else if (toolType === 'return') {
      metaItems = `
        <div class="tool-meta-item">
          <div class="tool-meta-label">Order Number</div>
          <div class="tool-meta-value"><code>${data.order_number || 'N/A'}</code></div>
        </div>
        <div class="tool-meta-item">
          <div class="tool-meta-label">Return Authorization</div>
          <div class="tool-meta-value" style="font-weight: 700; color: ${data.eligible ? '#10b981' : '#ef4444'};">${data.eligible ? '✅ Return Approved' : '❌ Ineligible for Return'}</div>
        </div>
        <div class="tool-meta-item">
          <div class="tool-meta-label">Days Elapsed Since Delivery</div>
          <div class="tool-meta-value">${data.days_since_delivery ?? 'N/A'} days (Policy limit: 30 days)</div>
        </div>
        <div class="tool-meta-item">
          <div class="tool-meta-label">Shipping Label</div>
          <div class="tool-meta-value">${data.prepaid_label ? '📦 Prepaid Courier Label Provided' : 'Standard Customer Return'}</div>
        </div>
      `;
    } else if (toolType === 'compare') {
      const prod = data.shopmate_product;
      const comps = data.competitors || [];
      
      if (prod) {
        const prodPrice = parseFloat(prod.price) || 0.0;
        metaItems = `
          <div class="tool-meta-item">
            <div class="tool-meta-label">Product Name</div>
            <div class="tool-meta-value">${prod.name || 'N/A'}</div>
          </div>
          <div class="tool-meta-item">
            <div class="tool-meta-label">Catalog SKU</div>
            <div class="tool-meta-value"><code>${prod.sku || 'N/A'}</code></div>
          </div>
          <div class="tool-meta-item">
            <div class="tool-meta-label">ShopMate AI Price</div>
            <div class="tool-meta-value" style="font-weight: 700; color: #6366f1;">$${prodPrice.toFixed(2)}</div>
          </div>
          <div class="tool-meta-item">
            <div class="tool-meta-label">Inventory Status</div>
            <div class="tool-meta-value">${prod.in_stock ? '✅ In Stock' : '❌ Out of Stock'}</div>
          </div>
        `;
      }

      let rows = '';
      if (prod) {
        const prodPrice = parseFloat(prod.price) || 0.0;
        rows += `
          <tr style="background: rgba(99, 102, 241, 0.08); font-weight: 600; border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 8px 12px;"><i class="fa-solid fa-gem" style="color: var(--accent-primary);"></i> <strong>ShopMate AI Store</strong></td>
            <td style="padding: 8px 12px; color: #6366f1; font-weight: 700;">$${prodPrice.toFixed(2)}</td>
            <td style="padding: 8px 12px;">✅ Direct Warranty & 30-Day Hassle-Free Returns</td>
          </tr>
        `;
      }

      comps.forEach(c => {
        const compPrice = parseFloat(c.price) || 0.0;
        const diff = parseFloat(c.price_difference) || 0.0;
        const diffStr = diff > 0 ? `<span style="color: #16a34a; font-weight: 600;">-$${diff.toFixed(2)} cheaper</span>` : `<span style="color: #64748b;">+$${Math.abs(diff).toFixed(2)}</span>`;
        const note = c.eligible_for_price_match ? '⚡ Eligible for Instant Price Match' : 'Marketplace Listing';
        rows += `
          <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 8px 12px;"><strong>${c.competitor}</strong></td>
            <td style="padding: 8px 12px; font-weight: 600;">$${compPrice.toFixed(2)} (${diffStr})</td>
            <td style="padding: 8px 12px; font-size: 11.5px; color: #475569;">${note}</td>
          </tr>
        `;
      });

      if (rows) {
        extraSection = `
          <div style="margin-top: 14px;">
            <div style="font-size: 11.5px; font-weight: 600; text-transform: uppercase; color: #64748b; margin-bottom: 6px; letter-spacing: 0.04em;">Side-by-Side Market Comparison</div>
            <table style="width: 100%; font-size: 12.5px; border-collapse: collapse; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #fff;">
              <thead>
                <tr style="background: #f8fafc; text-align: left; border-bottom: 1px solid #e2e8f0;">
                  <th style="padding: 8px 12px; font-weight: 600; color: #334155;">Platform / Retailer</th>
                  <th style="padding: 8px 12px; font-weight: 600; color: #334155;">Price & Difference</th>
                  <th style="padding: 8px 12px; font-weight: 600; color: #334155;">Policy / Match Status</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        `;
      }
    }

    const messageBanner = data.message || data.reason || data.recommended_action ? `
      <div class="tool-message-banner ${isSuccess ? 'msg-success' : 'msg-error'}" style="margin-top: 12px;">
        <i class="fa-solid ${isSuccess ? 'fa-lightbulb' : 'fa-triangle-exclamation'}"></i>
        <span>${data.message || data.reason || data.recommended_action}</span>
      </div>
    ` : '';

    return `
      <div class="tool-result-card" style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-top: 12px;">
        <div class="tool-status-badge ${badgeClass}">
          <i class="fa-solid ${badgeIcon}"></i>
          <span>${badgeText}</span>
        </div>
        ${metaItems ? `<div class="tool-meta-grid" style="margin-top: 12px;">${metaItems}</div>` : ''}
        ${extraSection}
        ${messageBanner}
      </div>
    `;
  },

  initToolsLab() {
    // 1. Inventory Check Tool
    const btnInv = document.getElementById('btn-tool-inventory');
    const inInv = document.getElementById('tool-sku-input');
    const outInv = document.getElementById('tool-inventory-result');
    if (btnInv && inInv && outInv) {
      btnInv.addEventListener('click', async () => {
        const val = inInv.value.trim() || 'ELEC-1001';
        outInv.innerHTML = '<div style="font-size: 12.5px; color: #64748b; padding: 8px;"><i class="fa-solid fa-spinner fa-spin"></i> Checking warehouse inventory in catalog...</div>';
        try {
          const res = await fetch('/api/tools/check-inventory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sku_or_name: val })
          });
          const data = await res.json();
          outInv.innerHTML = App.formatToolResult(data, 'inventory');
        } catch (e) {
          outInv.innerHTML = App.formatToolResult({ status: 'error', message: e.message }, 'inventory');
        }
      });
    }

    // 2. Order Tracker Tool
    const btnOrd = document.getElementById('btn-tool-order');
    const inOrd = document.getElementById('tool-order-input');
    const outOrd = document.getElementById('tool-order-result');
    if (btnOrd && inOrd && outOrd) {
      btnOrd.addEventListener('click', async () => {
        const val = inOrd.value.trim() || 'ORD-9821';
        outOrd.innerHTML = '<div style="font-size: 12.5px; color: #64748b; padding: 8px;"><i class="fa-solid fa-spinner fa-spin"></i> Tracking courier telemetry...</div>';
        try {
          const res = await fetch('/api/tools/get-order-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order_number: val })
          });
          const data = await res.json();
          outOrd.innerHTML = App.formatToolResult(data, 'order');
        } catch (e) {
          outOrd.innerHTML = App.formatToolResult({ status: 'error', message: e.message }, 'order');
        }
      });
    }

    // 3. Coupon Validator Tool
    const btnCpn = document.getElementById('btn-tool-coupon');
    const inCode = document.getElementById('tool-coupon-code');
    const inCart = document.getElementById('tool-coupon-cart');
    const outCpn = document.getElementById('tool-coupon-result');
    if (btnCpn && inCode && outCpn) {
      btnCpn.addEventListener('click', async () => {
        const code = inCode.value.trim() || 'SAVE20';
        const cart = parseFloat(inCart.value || 120.0);
        outCpn.innerHTML = '<div style="font-size: 12.5px; color: #64748b; padding: 8px;"><i class="fa-solid fa-spinner fa-spin"></i> Validating coupon discount...</div>';
        try {
          const res = await fetch('/api/tools/validate-coupon', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, cart_total: cart })
          });
          const data = await res.json();
          outCpn.innerHTML = App.formatToolResult(data, 'coupon');
        } catch (e) {
          outCpn.innerHTML = App.formatToolResult({ status: 'error', message: e.message }, 'coupon');
        }
      });
    }

    // 4. Return Eligibility Tool
    const btnRet = document.getElementById('btn-tool-return');
    const inRetOrd = document.getElementById('tool-return-order');
    const outRet = document.getElementById('tool-return-result');
    if (btnRet && inRetOrd && outRet) {
      btnRet.addEventListener('click', async () => {
        const order_number = inRetOrd.value.trim() || 'ORD-7643';
        outRet.innerHTML = '<div style="font-size: 12.5px; color: #64748b; padding: 8px;"><i class="fa-solid fa-spinner fa-spin"></i> Evaluating store policy rules...</div>';
        try {
          const res = await fetch('/api/tools/check-return', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order_number })
          });
          const data = await res.json();
          outRet.innerHTML = App.formatToolResult(data, 'return');
        } catch (e) {
          outRet.innerHTML = App.formatToolResult({ status: 'error', message: e.message }, 'return');
        }
      });
    }

    // 5. Live Competitor Price Comparison Tool (Amazon & eBay)
    const btnComp = document.getElementById('btn-tool-compare');
    const inComp = document.getElementById('tool-compare-query');
    const outComp = document.getElementById('tool-compare-result');
    if (btnComp && inComp && outComp) {
      btnComp.addEventListener('click', async () => {
        const query = inComp.value.trim() || 'AuraSound Pro';
        outComp.innerHTML = '<div style="font-size: 12.5px; color: #64748b; padding: 8px;"><i class="fa-solid fa-spinner fa-spin"></i> Querying Amazon Rainforest & eBay APIs in real-time...</div>';
        try {
          const res = await fetch('/api/tools/compare-prices', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
          });
          const data = await res.json();
          outComp.innerHTML = App.formatToolResult(data, 'compare');
        } catch (e) {
          outComp.innerHTML = App.formatToolResult({ status: 'error', message: e.message }, 'compare');
        }
      });
    }
  }
};

window.App = App;

document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
