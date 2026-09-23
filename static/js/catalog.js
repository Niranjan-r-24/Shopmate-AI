/**
 * ShopMate AI - Luxury Product Catalog Controller
 */
const Catalog = {
  activeCategory: 'all',
  maxPrice: 150000,
  inStockOnly: false,
  sortBy: 'rating',
  searchTerm: '',

  init() {
    this.loadProducts();
    this.updateWishlistBadge();

    // 1. Category Filter Tabs
    document.querySelectorAll('#category-filter-tabs .filter-tab-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#category-filter-tabs .filter-tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.activeCategory = btn.getAttribute('data-category');
        this.loadProducts();
      });
    });

    // 2. Filter panel inputs
    const priceSlider = document.getElementById('store-price-slider');
    const priceVal = document.getElementById('store-price-val');
    const inStockToggle = document.getElementById('store-instock-checkbox');
    const sortSelect = document.getElementById('store-sort-select');
    const keywordInput = document.getElementById('store-keyword-input');

    if (priceSlider && priceVal) {
      priceSlider.addEventListener('input', (e) => {
        this.maxPrice = parseFloat(e.target.value);
        priceVal.textContent = `₹${this.maxPrice}`;
        this.loadProducts();
      });
    }

    if (inStockToggle) {
      inStockToggle.addEventListener('change', (e) => {
        this.inStockOnly = e.target.checked;
        this.loadProducts();
      });
    }

    if (sortSelect) {
      sortSelect.addEventListener('change', (e) => {
        this.sortBy = e.target.value;
        this.loadProducts();
      });
    }

    if (keywordInput) {
      keywordInput.addEventListener('input', (e) => {
        this.searchTerm = e.target.value.trim();
        this.loadProducts();
      });
    }
  },

  getWishlistKey() {
    const user = window.Auth ? window.Auth.getUser() : { username: 'niranjan' };
    return 'shopmate_wishlist_' + (user.username || 'niranjan');
  },

  getWishlist() {
    const raw = localStorage.getItem(this.getWishlistKey());
    try {
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  },

  isInWishlist(sku) {
    const wishlist = this.getWishlist();
    return wishlist.some(item => item.sku === sku);
  },

  toggleWishlist(sku, name, btn) {
    let wishlist = this.getWishlist();
    const idx = wishlist.findIndex(item => item.sku === sku);
    const icon = btn.querySelector('i');

    if (idx > -1) {
      wishlist.splice(idx, 1);
      localStorage.setItem(this.getWishlistKey(), JSON.stringify(wishlist));
      if (icon) {
        icon.className = 'fa-regular fa-heart';
        icon.style.color = '';
      }
      window.App.showToast(`Removed ${name} from Wishlist`, 'info');
    } else {
      wishlist.push({ sku, name });
      localStorage.setItem(this.getWishlistKey(), JSON.stringify(wishlist));
      if (icon) {
        icon.className = 'fa-solid fa-heart favorited';
        icon.style.color = 'var(--accent-rose)';
      }
      window.App.showToast(`Added ${name} to Wishlist!`, 'success');
    }
    this.updateWishlistBadge();
  },

  updateWishlistBadge() {
    const badge = document.getElementById('wishlist-count');
    if (badge) {
      badge.textContent = String(this.getWishlist().length);
    }
  },

  filterByCategory(category) {
    this.activeCategory = category;
    document.querySelectorAll('#category-filter-tabs .filter-tab-btn').forEach((btn) => {
      if (btn.getAttribute('data-category').toLowerCase() === category.toLowerCase()) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
    this.loadProducts();
    const el = document.getElementById('store-products');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  },

  async loadProducts() {
    const grid = document.getElementById('main-product-grid');
    if (!grid) return;

    grid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px 0;">
        <span class="status-dot"></span> Loading curated luxury catalog...
      </div>
    `;

    try {
      const params = new URLSearchParams({
        category: this.activeCategory,
        max_price: this.maxPrice,
        in_stock_only: this.inStockOnly,
        sort_by: this.sortBy
      });
      if (this.searchTerm) params.append('search', this.searchTerm);

      const res = await fetch(`/api/products?${params.toString()}`);
      const data = await res.json();

      if (!data.products || data.products.length === 0) {
        grid.innerHTML = `
          <div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 50px 0;">
            <i class="fa-solid fa-box-open" style="font-size: 28px; color: #ccc; margin-bottom: 10px;"></i>
            <p>No products match your active luxury filters.</p>
          </div>
        `;
        return;
      }

      grid.innerHTML = data.products.map((p) => {
        const inStock = p.stock_count > 0;
        return `
          <div class="product-card">
            <div class="product-image-wrap">
              <img src="${p.image_url || 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500'}" alt="${p.name}">
              
              <div class="product-badge-group">
                ${p.original_price > p.price ? '<span class="badge-tag sale">SALE</span>' : ''}
                <span class="badge-tag ${inStock ? 'stock' : 'outstock'}">${inStock ? 'In Stock' : 'Out of Stock'}</span>
              </div>

              <div class="product-action-hover">
                <button class="btn-card-icon" title="Ask AI about this item" onclick="Catalog.askAboutProduct('${p.sku}', '${p.name.replace(/'/g, "\\'")}')">
                  <i class="fa-solid fa-robot"></i>
                </button>
                <button class="btn-card-icon" title="Add to Bag" onclick="Catalog.addToCart('${p.sku}', '${p.name.replace(/'/g, "\\'")}', ${p.price}, '${p.image_url}')">
                  <i class="fa-solid fa-bag-shopping"></i>
                </button>
                <button class="btn-card-icon" title="Save to Wishlist" onclick="Catalog.toggleWishlist('${p.sku}', '${p.name.replace(/'/g, "\\'")}', this)">
                  <i class="${Catalog.isInWishlist(p.sku) ? 'fa-solid fa-heart favorited' : 'fa-regular fa-heart'}" style="${Catalog.isInWishlist(p.sku) ? 'color: var(--accent-rose);' : ''}"></i>
                </button>
              </div>
            </div>

            <div class="product-info">
              <span class="product-category-name">${p.brand} • ${p.category}</span>
              <h3 class="product-title">${p.name}</h3>
              
              <div class="product-price-row">
                <span class="price-current">₹${Number(p.price).toFixed(2)}</span>
                ${p.original_price > p.price ? `<span class="price-original">₹${Number(p.original_price).toFixed(2)}</span>` : ''}
              </div>

              <div class="product-card-footer">
                <span style="font-size: 12px; color: var(--accent-gold);"><i class="fa-solid fa-star"></i> ${p.rating} (${p.review_count})</span>
                <button class="btn-ask-ai" onclick="Catalog.askAboutProduct('${p.sku}', '${p.name.replace(/'/g, "\\'")}')">
                  <i class="fa-solid fa-sparkles"></i> Ask ShopMate
                </button>
              </div>
            </div>
          </div>
        `;
      }).join('');
    } catch (e) {
      grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--accent-rose);">Failed loading products: ${e.message}</div>`;
    }
  },

  askAboutProduct(sku, name) {
    window.App.openAiConcierge('chat', `Tell me key features, warranty details, and inventory stock for ${name} (SKU: ${sku})`);
  },

  addToCart(sku, name, price, img) {
    if (window.App && typeof window.App.addToCart === 'function') {
      window.App.addToCart(sku, name, price, img);
    }
  }
};

window.Catalog = Catalog;
