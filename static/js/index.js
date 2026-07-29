/* ============================================================
   FoodCourt — Landing Page JavaScript (index.js)
   ============================================================ */
'use strict';

document.addEventListener('DOMContentLoaded', () => {
  initTypewriter();
  renderCategories();
  renderFeaturedRestaurants();
  renderTestimonials();
  initStatsCounter();
});

/* ══════════════════════════════════════════════
   TYPEWRITER EFFECT
   ══════════════════════════════════════════════ */
function initTypewriter() {
  const words = ['Delivered Fast', 'Always Hot', 'Fresh & Tasty', 'Piping Hot', 'On Time'];
  const highlightEl = document.querySelector('.hero-headline .highlight');
  if (!highlightEl) return;

  let wordIndex = 0;
  let charIndex = 0;
  let isDeleting = false;
  let delay = 150;

  function type() {
    const currentWord = words[wordIndex];
    
    if (isDeleting) {
      highlightEl.textContent = currentWord.substring(0, charIndex - 1);
      charIndex--;
      delay = 60;
    } else {
      highlightEl.textContent = currentWord.substring(0, charIndex + 1);
      charIndex++;
      delay = 120;
    }

    if (!isDeleting && charIndex === currentWord.length) {
      isDeleting = true;
      delay = 2000; // Wait before deleting
    } else if (isDeleting && charIndex === 0) {
      isDeleting = false;
      wordIndex = (wordIndex + 1) % words.length;
      delay = 400; // Wait before starting next word
    }

    setTimeout(type, delay);
  }

  // Clear hardcoded text and start loop
  highlightEl.textContent = '';
  setTimeout(type, 1000);
}

/* ══════════════════════════════════════════════
   RENDER CATEGORIES
   ══════════════════════════════════════════════ */
function renderCategories() {
  const container = document.getElementById('categories-container');
  if (!container || !window.FOODCOURT_DATA) return;

  const categories = window.FOODCOURT_DATA.categories;
  container.innerHTML = categories.map((c, idx) => `
    <a href="/restaurants/?category=${c.id}" class="category-pill reveal stagger-${(idx % 6) + 1}" style="--pill-color: ${c.color}">
      <span class="category-pill-emoji">${c.emoji}</span>
      <span class="category-pill-name">${c.name}</span>
    </a>
  `).join('');
}

/* ══════════════════════════════════════════════
   RENDER FEATURED RESTAURANTS
   ══════════════════════════════════════════════ */
function renderFeaturedRestaurants() {
  const container = document.getElementById('featured-restaurants');
  if (!container || !window.FOODCOURT_DATA) return;

  // Show skeleton loader
  window.Skeleton.show(container, 6);

  // Simulate server fetch delay
  setTimeout(() => {
    window.Skeleton.hide(container);
    
    // Get top 6 featured open restaurants
    const featured = window.FOODCOURT_DATA.restaurants
      .filter(r => r.isFeatured)
      .slice(0, 6);

    if (featured.length === 0) {
      container.innerHTML = `<div class="col-12 text-center text-muted">No featured restaurants found.</div>`;
      return;
    }

    container.innerHTML = featured.map((r, idx) => {
      // Re-use core render function from app.js but inject staggered animation
      const cardHtml = window.renderRestaurantCard(r);
      // Inject stagger class into the column or outer element
      return cardHtml.replace('class="col"', `class="col stagger-${(idx % 6) + 1}"`);
    }).join('');

    // Re-initialize ScrollReveal to pick up newly rendered cards
    if (window.ScrollReveal) {
      window.ScrollReveal.init();
    }
  }, 1000);
}

/* ══════════════════════════════════════════════
   RENDER TESTIMONIALS
   ══════════════════════════════════════════════ */
function renderTestimonials() {
  const container = document.getElementById('testimonials-container');
  if (!container || !window.FOODCOURT_DATA) return;

  const testimonials = window.FOODCOURT_DATA.testimonials.slice(0, 3);
  container.innerHTML = testimonials.map((t, idx) => `
    <div class="col-md-4 stagger-${idx + 1}">
      <div class="testimonial-card reveal">
        <div class="testimonial-stars">
          ${'★'.repeat(t.rating)}${'☆'.repeat(5 - t.rating)}
        </div>
        <p class="testimonial-text">"${t.text}"</p>
        <div class="testimonial-author">
          <img src="${t.avatar}" alt="${t.name}" loading="lazy">
          <div>
            <div class="testimonial-name">${t.name}</div>
            <div class="testimonial-location">${t.location} · ${t.date}</div>
          </div>
        </div>
      </div>
    </div>
  `).join('');
}

/* ══════════════════════════════════════════════
   STATS COUNT-UP
   ══════════════════════════════════════════════ */
function initStatsCounter() {
  const stats = document.querySelectorAll('.hero-stat-num[data-count]');
  if (stats.length === 0) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const target = entry.target;
        const countTo = parseInt(target.getAttribute('data-count'), 10);
        let count = 0;
        const duration = 2000; // 2 seconds
        const stepTime = Math.abs(Math.floor(duration / countTo));
        const suffix = target.innerHTML.includes('min') ? '<span style="font-size:1rem">min</span>' :
                       target.innerHTML.includes('k+') ? '<span style="font-size:1rem">k+</span>' : '';

        const timer = setInterval(() => {
          count += Math.ceil(countTo / 50); // Increment
          if (count >= countTo) {
            clearInterval(timer);
            target.innerHTML = countTo + suffix;
          } else {
            target.innerHTML = count + suffix;
          }
        }, Math.max(stepTime, 20));

        observer.unobserve(target);
      }
    });
  }, { threshold: 0.5 });

  stats.forEach(s => observer.observe(s));
}

/* ══════════════════════════════════════════════
   SEARCH SUBMIT HANDLER
   ══════════════════════════════════════════════ */
window.heroSearch = function(event) {
  event.preventDefault();
  const input = document.getElementById('hero-search-input');
  if (!input) return;
  
  const query = encodeURIComponent(input.value.trim());
  window.location.href = `/restaurants/?q=${query}`;
};
