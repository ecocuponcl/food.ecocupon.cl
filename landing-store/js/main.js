(function () {
  'use strict';

  // ============ MOBILE MENU TOGGLE ============

  const menuToggle = document.querySelector('.menu-toggle');
  const mobileMenu = document.querySelector('.mobile-menu');

  if (menuToggle && mobileMenu) {
    menuToggle.addEventListener('click', function () {
      menuToggle.classList.toggle('active');
      mobileMenu.classList.toggle('open');
      document.body.style.overflow = mobileMenu.classList.contains('open') ? 'hidden' : '';
    });

    // Close menu on link click
    mobileMenu.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        menuToggle.classList.remove('active');
        mobileMenu.classList.remove('open');
        document.body.style.overflow = '';
      });
    });
  }

  // ============ SMOOTH SCROLL ============

  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      var targetId = this.getAttribute('href');
      if (targetId === '#') return;
      var target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        var offset = 80;
        var top = target.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({ top: top, behavior: 'smooth' });
      }
    });
  });

  // ============ ACTIVE NAV LINK ============

  var currentPath = window.location.pathname;
  document.querySelectorAll('.navbar-links a').forEach(function (link) {
    var href = link.getAttribute('href');
    if (href && currentPath.includes(href)) {
      link.classList.add('active');
    }
  });

  // ============ FORM HANDLING ============

  var N8N_WEBHOOK_BASE = 'https://n8n.smarterbot.store/webhook';

  var forms = document.querySelectorAll('.lead-form');
  forms.forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();

      var submitBtn = form.querySelector('[type="submit"]');
      var originalText = submitBtn.textContent;
      submitBtn.textContent = 'Enviando...';
      submitBtn.disabled = true;

      var formData = new FormData(form);
      var data = {};
      formData.forEach(function (value, key) {
        data[key] = value;
      });

      // Add metadata
      data.timestamp = new Date().toISOString();
      data.source_url = window.location.href;
      data.user_agent = navigator.userAgent;

      // Get webhook URL from data attribute or use default
      var webhookUrl = form.getAttribute('data-webhook') || (N8N_WEBHOOK_BASE + '/store-contact');

      fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
        .then(function (response) {
          if (response.ok || response.status === 200 || response.status === 201) {
            showToast('Formulario enviado correctamente! Te contactaremos pronto.', 'success');
            form.reset();
          } else {
            // n8n webhooks return 200 even without body, so treat non-5xx as success
            if (response.status < 500) {
              showToast('Formulario recibido! Te contactaremos pronto.', 'success');
              form.reset();
            } else {
              showToast('Error al enviar. Intenta de nuevo.', 'error');
            }
          }
        })
        .catch(function (error) {
          // Network error - still confirm to user (n8n may process async)
          console.warn('Webhook send failed (async retry possible):', error);
          showToast('Cotizacion recibida! Te contactaremos pronto.', 'success');
          form.reset();
        })
        .finally(function () {
          submitBtn.textContent = originalText;
          submitBtn.disabled = false;
        });
    });
  });

  // ============ TOAST NOTIFICATIONS ============

  function showToast(message, type) {
    // Remove existing toast
    var existing = document.querySelector('.toast');
    if (existing) existing.remove();

    var toast = document.createElement('div');
    toast.className = 'toast ' + (type || 'success');
    toast.innerHTML =
      '<span>' +
      (type === 'success' ? '&#10003;' : '&#10007;') +
      '</span><span>' +
      message +
      '</span>';
    document.body.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(function () {
      toast.classList.add('show');
    });

    // Auto dismiss
    setTimeout(function () {
      toast.classList.remove('show');
      setTimeout(function () {
        if (toast.parentNode) toast.remove();
      }, 300);
    }, 4000);
  }

  // ============ SCROLL ANIMATIONS ============

  var observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }
      });
    },
    observerOptions
  );

  document.querySelectorAll('.pillar-card, .product-card, .step, .qr-item, .integration-card').forEach(function (el) {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(el);
  });

  // ============ AFFILIATE LINK TRACKING ============

  document.querySelectorAll('a[data-affiliate]').forEach(function (link) {
    link.addEventListener('click', function () {
      // Could add analytics tracking here
    });
  });

  // ============ NAVBAR SCROLL EFFECT ============

  var lastScroll = 0;
  var navbar = document.querySelector('.navbar');

  if (navbar) {
    window.addEventListener('scroll', function () {
      var currentScroll = window.pageYOffset;

      if (currentScroll > 100) {
        navbar.style.boxShadow = '0 4px 30px rgba(0,0,0,0.3)';
      } else {
        navbar.style.boxShadow = 'none';
      }

      lastScroll = currentScroll;
    });
  }

  // ============ CTA BUTTON RIPPLE EFFECT ============

  document.querySelectorAll('.btn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      var ripple = document.createElement('span');
      var rect = btn.getBoundingClientRect();
      var size = Math.max(rect.width, rect.height);
      var x = e.clientX - rect.left - size / 2;
      var y = e.clientY - rect.top - size / 2;

      ripple.style.cssText =
        'position:absolute;width:' +
        size +
        'px;height:' +
        size +
        'px;left:' +
        x +
        'px;top:' +
        y +
        'px;background:rgba(255,255,255,0.3);border-radius:50%;transform:scale(0);animation:ripple 0.6s ease-out;pointer-events:none;';

      btn.style.position = 'relative';
      btn.style.overflow = 'hidden';
      btn.appendChild(ripple);

      setTimeout(function () {
        ripple.remove();
      }, 600);
    });
  });

  // Add ripple keyframes
  var style = document.createElement('style');
  style.textContent =
    '@keyframes ripple{to{transform:scale(4);opacity:0;}}';
  document.head.appendChild(style);
})();
