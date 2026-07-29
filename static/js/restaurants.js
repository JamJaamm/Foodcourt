/* ============================================================
   FoodCourt — Restaurants Page JavaScript (restaurants.js)
   ============================================================ */
'use strict';

// State management for filtering and sorting
let activeCategory = 'all';
let searchQuery = '';
let activeSort = 'default';
let activeFilters = {
  freeDelivery: false,
  openNow: false,
  topRated: false,
  vegetarian: false
};

document.addEventListener('DOMContentLoaded', () => {
  // Parse URL Parameters
  const catParam = window.getUrlParam('category');
  if (catParam) activeCategory = catParam;

  const searchParam = window.getUrlParam('q');
  if (searchParam) {
    searchQuery = searchParam;
    const searchInput = document.getElementById('restaurants-search-input');
    if (searchInput) searchInput.value = searchParam;
  }

  // Render & setup filters
  renderCategoryPills();
  setupFilterListeners();
  
  // Initial load
  loadFilteredRestaurants();
});

/* ══════════════════════════════════════════════
   RENDER CATEGORY PILLS
   ══════════════════════════════════════════════ */
function renderCategoryPills() {
  const container = document.getElementById('filter-pills-container');
  if (!container || !window.FOODCOURT_DATA) return;

  const categories = [
    { id: 'all', name: 'All Cuisines', emoji: '🍽️' },
    ...window.FOODCOURT_DATA.categories
  ];

  container.innerHTML = categories.map(c => {
    const isActive = c.id === activeCategory;
    return `
      <button class="filter-pill ${isActive ? 'active' : ''}" 
              data-category="${c.id}" 
              onclick="selectCategory('${c.id}')">
        <span>${c.emoji}</span>
        <span>${c.name}</span>
      </button>
    `;
  }).join('');
}

/* ══════════════════════════════════════════════
   SELECT CATEGORY HANDLER
   ══════════════════════════════════════════════ */
window.selectCategory = function(catId) {
  activeCategory = catId;
  
  // Update UI active state
  document.querySelectorAll('.filter-pill').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-category') === catId);
  });

  // Re-load data
  loadFilteredRestaurants();
  
  // Update URL silently
  const url = new URL(window.location);
  if (catId === 'all') {
    url.searchParams.delete('category');
  } else {
    url.searchParams.set('category', catId);
  }
  window.history.replaceState({}, '', url);
};

/* ══════════════════════════════════════════════
   LISTENERS SETUP
   ══════════════════════════════════════════════ */
function setupFilterListeners() {
  // Search text input
  const searchInput = document.getElementById('restaurants-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.toLowerCase().trim();
      loadFilteredRestaurants();
    });
  }

  // Sort dropdown select
  const sortSelect = document.getElementById('restaurants-sort-select');
  if (sortSelect) {
    sortSelect.addEventListener('change', (e) => {
      activeSort = e.target.value;
      loadFilteredRestaurants();
    });
  }

  // Checkbox triggers
  const setupToggle = (id, key) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', (e) => {
        activeFilters[key] = e.target.checked;
        loadFilteredRestaurants();
      });
    }
  };

  setupToggle('toggle-free-delivery', 'freeDelivery');
  setupToggle('toggle-open-now', 'openNow');
  setupToggle('toggle-top-rated', 'topRated');
  setupToggle('toggle-vegetarian', 'vegetarian');
}

/* ══════════════════════════════════════════════
   FILTER AND SORT IMPLEMENTATION
   ══════════════════════════════════════════════ */
function loadFilteredRestaurants() {
  const container = document.getElementById('restaurants-grid');
  const emptyState = document.getElementById('restaurants-empty-state');
  if (!container || !window.FOODCOURT_DATA) return;

  // Show skeletons
  window.Skeleton.show(container, 8);
  emptyState.classList.add('d-none');
  container.classList.remove('d-none');

  setTimeout(() => {
    window.Skeleton.hide(container);

    let list = [...window.FOODCOURT_DATA.restaurants];

    // 1. Filter by category
    if (activeCategory !== 'all') {
      list = list.filter(r => r.category === activeCategory);
    }

    // 2. Filter by search query
    if (searchQuery) {
      list = list.filter(r => 
        r.name.toLowerCase().includes(searchQuery) ||
        r.cuisine.toLowerCase().includes(searchQuery) ||
        r.tags.some(t => t.toLowerCase().includes(searchQuery))
      );
    }

    // 3. Filter by toggles
    if (activeFilters.freeDelivery) {
      list = list.filter(r => r.deliveryFee === 0);
    }
    if (activeFilters.openNow) {
      list = list.filter(r => r.isOpen);
    }
    if (activeFilters.topRated) {
      list = list.filter(r => r.rating >= 4.7);
    }
    if (activeFilters.vegetarian) {
      // Find restaurants that have vegetarian tags or menu items (or category salads/tacos/ramen often have it)
      list = list.filter(r => 
        r.tags.some(t => t.toLowerCase().includes('vegan') || t.toLowerCase().includes('vegetarian') || t.toLowerCase().includes('salad'))
      );
    }

    // 4. Sort
    if (activeSort === 'rating') {
      list.sort((a, b) => b.rating - a.rating);
    } else if (activeSort === 'deliveryTime') {
      list.sort((a, b) => a.deliveryTime - b.deliveryTime);
    } else if (activeSort === 'minOrder') {
      list.sort((a, b) => a.minOrder - b.minOrder);
    } else if (activeSort === 'distance') {
      list.sort((a, b) => a.distance - b.distance);
    } else {
      // Default: featured first, then by rating
      list.sort((a, b) => {
        if (a.isFeatured && !b.isFeatured) return -1;
        if (!a.isFeatured && b.isFeatured) return 1;
        return b.rating - a.rating;
      });
    }

    // Update Results count
    const countEl = document.getElementById('results-count');
    if (countEl) {
      countEl.textContent = `Showing ${list.length} restaurant${list.length === 1 ? '' : 's'}`;
    }

    // Empty state trigger
    if (list.length === 0) {
      container.classList.add('d-none');
      emptyState.classList.remove('d-none');
      return;
    }

    // Render cards using base app.js render function
    container.innerHTML = list.map((r, idx) => {
      const cardHtml = window.renderRestaurantCard(r);
      return cardHtml.replace('class="col"', `class="col stagger-${(idx % 6) + 1}"`);
    }).join('');

    // Re-initialize reveals
    if (window.ScrollReveal) {
      window.ScrollReveal.init();
    }
  }, 400); // Fast mock delay for sleek UX
}

/* ══════════════════════════════════════════════
   RESET ALL FILTERS
   ══════════════════════════════════════════════ */
window.resetFilters = function() {
  activeCategory = 'all';
  searchQuery = '';
  activeSort = 'default';
  activeFilters = {
    freeDelivery: false,
    openNow: false,
    topRated: false,
    vegetarian: false
  };

  // Reset inputs in DOM
  const searchInput = document.getElementById('restaurants-search-input');
  if (searchInput) searchInput.value = '';

  const sortSelect = document.getElementById('restaurants-sort-select');
  if (sortSelect) sortSelect.value = 'default';

  const resetToggle = (id) => {
    const el = document.getElementById(id);
    if (el) el.checked = false;
  };
  resetToggle('toggle-free-delivery');
  resetToggle('toggle-open-now');
  resetToggle('toggle-top-rated');
  resetToggle('toggle-vegetarian');

  // Reset Category Pills UI
  document.querySelectorAll('.filter-pill').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-category') === 'all');
  });

  // Re-load
  loadFilteredRestaurants();

  // Reset URL
  const url = new URL(window.location);
  url.search = '';
  window.history.replaceState({}, '', url);

  Toast.show('All filters reset 🧹', 'info');
};
