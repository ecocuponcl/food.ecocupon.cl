/**
 * Food Kiosk — Touch-optimized cart & payment
 */
odoo.define('food_kiosk.kiosk', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    // Cart state
    var cart = {
        items: [],
        total: 0,
    };

    // ── Cart UI ─────────────────────────────────────
    window.showCart = function () {
        renderCart();
        document.getElementById('cartPanel').classList.add('visible');
    };

    window.hideCart = function () {
        document.getElementById('cartPanel').classList.remove('visible');
    };

    window.filterCategory = function (tabEl) {
        var categoryId = tabEl.getAttribute('data-category-id');
        // Update active tab
        document.querySelectorAll('.kiosk-tab').forEach(function (t) {
            t.classList.remove('active');
        });
        tabEl.classList.add('active');

        // Filter products
        document.querySelectorAll('.kiosk-product-card').forEach(function (card) {
            var cardCat = card.getAttribute('data-category-id');
            if (categoryId === 'all' || cardCat === categoryId) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
    };

    window.addToCart = function (cardEl) {
        var productId = parseInt(cardEl.getAttribute('data-product-id'));
        var price = parseFloat(cardEl.getAttribute('data-price'));
        var name = cardEl.querySelector('.kiosk-product-name').textContent;

        // Check if already in cart
        var existing = cart.items.find(function (item) {
            return item.productId === productId;
        });
        if (existing) {
            existing.qty += 1;
        } else {
            cart.items.push({
                productId: productId,
                name: name,
                price: price,
                qty: 1,
            });
        }
        updateCartCount();

        // Visual feedback
        cardEl.style.borderColor = '#00c853';
        setTimeout(function () {
            cardEl.style.borderColor = 'transparent';
        }, 300);
    };

    window.updateCartItem = function (productId, delta) {
        var item = cart.items.find(function (i) {
            return i.productId === productId;
        });
        if (item) {
            item.qty += delta;
            if (item.qty <= 0) {
                cart.items = cart.items.filter(function (i) {
                    return i.productId !== productId;
                });
            }
        }
        updateCartCount();
        renderCart();
    };

    function updateCartCount() {
        var count = cart.items.reduce(function (sum, item) {
            return sum + item.qty;
        }, 0);
        var el = document.querySelector('.cart-count');
        if (el) el.textContent = count;
    }

    function calcTotal() {
        return cart.items.reduce(function (sum, item) {
            return sum + item.price * item.qty;
        }, 0);
    }

    function renderCart() {
        var container = document.getElementById('cartItems');
        if (!container) return;

        if (cart.items.length === 0) {
            container.innerHTML = '<p class="kiosk-cart-empty">Agrega productos a tu pedido</p>';
            document.getElementById('cartTotal').textContent = '$0';
            return;
        }

        var html = '';
        cart.items.forEach(function (item) {
            html += '<div class="cart-item">' +
                '<span class="cart-item-name">' + item.name + '</span>' +
                '<div class="cart-item-qty">' +
                    '<button onclick="updateCartItem(' + item.productId + ', -1)">−</button>' +
                    '<span>' + item.qty + '</span>' +
                    '<button onclick="updateCartItem(' + item.productId + ', 1)">+</button>' +
                '</div>' +
                '<span>$' + Math.round(item.price * item.qty).toLocaleString('es-CL') + '</span>' +
            '</div>';
        });
        container.innerHTML = html;

        var total = calcTotal();
        cart.total = total;
        var totalEl = document.getElementById('cartTotal');
        if (totalEl) {
            totalEl.textContent = '$' + total.toLocaleString('es-CL');
        }
    }

    // ── Payment ─────────────────────────────────────
    window.payOrder = function () {
        if (cart.items.length === 0) {
            alert('Agrega productos primero');
            return;
        }

        var payBtn = document.querySelector('.kiosk-btn-pay');
        if (payBtn) {
            payBtn.disabled = true;
            payBtn.textContent = '⏳ Procesando...';
        }

        var total = calcTotal();

        fetch('/kiosk/create_order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                amount: total,
                items: cart.items.map(function (item) {
                    return {
                        product_id: item.productId,
                        qty: item.qty,
                        price: item.price,
                    };
                }),
            }),
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.error) {
                alert('Error: ' + data.error);
                if (payBtn) {
                    payBtn.disabled = false;
                    payBtn.textContent = '💳 Pagar Ahora';
                }
                return;
            }
            if (data.payment_url) {
                // Redirect to Flow payment page
                window.location.href = data.payment_url;
            } else {
                alert('No se pudo generar el pago. Intenta de nuevo.');
                if (payBtn) {
                    payBtn.disabled = false;
                    payBtn.textContent = '💳 Pagar Ahora';
                }
            }
        })
        .catch(function (err) {
            console.error('Payment error:', err);
            alert('Error de conexión. Intenta de nuevo.');
            if (payBtn) {
                payBtn.disabled = false;
                payBtn.textContent = '💳 Pagar Ahora';
            }
        });
    };
});
