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

    // ── QR Scanner ─────────────────────────────────────
    var html5QrcodeScanner;

    window.openQRScanner = function () {
        var container = document.getElementById('qr-scanner-container');
        if (container) {
            container.style.display = 'block';
            initQRScanner();
        }
    };

    window.closeQRScanner = function () {
        var container = document.getElementById('qr-scanner-container');
        if (container) {
            container.style.display = 'none';
        }
        if (html5QrcodeScanner) {
            html5QrcodeScanner.stop().catch(function (err) {
                console.error('QR stop error:', err);
            });
            html5QrcodeScanner = null;
        }
    };

    function initQRScanner() {
        if (typeof Html5Qrcode === 'undefined') {
            console.error('html5-qrcode library not loaded');
            return;
        }

        // Clean up any previous instance
        if (html5QrcodeScanner) {
            html5QrcodeScanner.stop().catch(function () {});
        }

        html5QrcodeScanner = new Html5Qrcode("qr-reader");

        var config = {
            fps: 10,
            qrbox: { width: 250, height: 250 },
            aspectRatio: 1.0
        };

        html5QrcodeScanner.start(
            { facingMode: "environment" },
            config,
            onQRCodeSuccess,
            onQRCodeError
        ).catch(function (err) {
            console.error("QR init error:", err);
        });
    }

    function onQRCodeSuccess(decodedText) {
        // Pause scanner to prevent double scans
        if (html5QrcodeScanner) {
            html5QrcodeScanner.pause();
        }

        // Validate QR with backend
        fetch('/recycle/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ qr_code: decodedText })
        })
        .then(function (r) { return r.json(); })
        .then(function (result) {
            if (result.valid) {
                // Add to cart as recyclable item with cashback
                addToCart({
                    name: result.material + ' (' + result.weight + 'kg)',
                    price: -result.cashback,
                    cashback: result.cashback,
                    material: result.material,
                    weight: result.weight,
                    isRecycle: true
                });

                // Visual feedback
                showNotification('✅ ' + result.material + ' — $' + result.cashback.toLocaleString('es-CL') + ' CLP acreditado');

                // Close scanner after short delay
                setTimeout(function () {
                    closeQRScanner();
                }, 1500);
            } else {
                showNotification('❌ QR inválido: ' + (result.message || result.error || 'Error desconocido'));
                // Resume scanner
                if (html5QrcodeScanner) {
                    html5QrcodeScanner.resume().catch(function () {});
                }
            }
        })
        .catch(function (err) {
            console.error('QR validation error:', err);
            showNotification('❌ Error de conexión al validar QR');
            if (html5QrcodeScanner) {
                html5QrcodeScanner.resume().catch(function () {});
            }
        });
    }

    function onQRCodeError(error) {
        // Silent fail - user will scan again
        if (error) {
            console.debug('QR scan error:', error);
        }
    }

    function showNotification(message) {
        // Remove existing notification
        var existing = document.querySelector('.kiosk-notification');
        if (existing) existing.remove();

        var notif = document.createElement('div');
        notif.className = 'kiosk-notification';
        notif.textContent = message;
        notif.style.cssText = 'position:fixed; top:20px; left:50%; transform:translateX(-50%); ' +
            'background:#00c853; color:#1a1a2e; padding:16px 24px; border-radius:12px; ' +
            'font-size:16px; font-weight:bold; z-index:10001; box-shadow:0 4px 20px rgba(0,200,83,0.4); ' +
            'max-width:90vw; text-align:center;';
        document.body.appendChild(notif);

        setTimeout(function () {
            notif.style.opacity = '0';
            notif.style.transition = 'opacity 0.5s';
            setTimeout(function () {
                notif.remove();
            }, 500);
        }, 3000);
    }

    // Override addToCart to handle QR recycle items
    var _originalAddToCart = window.addToCart;
    window.addToCart = function (cardEl) {
        // Support programmatic calls with object (from QR scanner)
        if (typeof cardEl !== 'object' || cardEl instanceof HTMLElement === false) {
            if (typeof cardEl === 'object' && cardEl.isRecycle) {
                // It's a recycle item from QR scanner
                var existing = cart.items.find(function (item) {
                    return item.isRecycle && item.material === cardEl.material;
                });
                if (existing) {
                    existing.qty += 1;
                } else {
                    cart.items.push({
                        productId: 0,
                        name: cardEl.name,
                        price: cardEl.price,
                        qty: 1,
                        isRecycle: true,
                        material: cardEl.material,
                        weight: cardEl.weight,
                        cashback: cardEl.cashback,
                    });
                }
                updateCartCount();
                showNotification('♻️ ' + cardEl.name + ' agregado');
                return;
            }
        }
        // Call original for product cards
        _originalAddToCart(cardEl);
    };
});
