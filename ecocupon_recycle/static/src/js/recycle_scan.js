/**
 * EcoCupon Recycle - QR Scan + Cashback + Wallet
 * AJUSTE 3 + 4 + 5: Validación híbrida → evento → pago
 */
odoo.define('ecocupon_recycle.recycle_scan', function(require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    // ── QR Scan ──
    window.manualScan = function() {
        var qrCode = document.getElementById('qrInput').value.trim();
        if (!qrCode) {
            alert('Ingresa el código QR');
            return;
        }
        processScan(qrCode);
    };

    function processScan(qrCode) {
        var resultDiv = document.getElementById('scanResult');
        var cardDiv = document.getElementById('resultCard');

        cardDiv.className = 'result-card pending';
        cardDiv.innerHTML = '<h2>⏳ Verificando QR...</h2><p>Validando autenticidad</p>';
        resultDiv.style.display = 'block';

        fetch('/kiosk/scan_qr', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({qr_code: qrCode}),
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                if (data.validated) {
                    // AJUSTE 5: Validado → cashback acreditado
                    cardDiv.className = 'result-card success';
                    cardDiv.innerHTML =
                        '<h2>✅ ¡Reciclaje Validado!</h2>' +
                        '<div class="result-amount">+' + Math.round(data.cashback).toLocaleString('es-CL') + ' CLP</div>' +
                        '<p>' + (data.item_name || 'Item') + ' reciclado</p>' +
                        '<p>💰 Wallet: ' + (data.wallet_balance || 0).toLocaleString('es-CL') + ' CLP</p>' +
                        '<p>Método: ' + (data.validation_method || 'Automático') + '</p>';
                    // Update wallet display
                    updateWalletDisplay();
                } else {
                    // Pending validation
                    cardDiv.className = 'result-card pending';
                    cardDiv.innerHTML =
                        '<h2>📋 Pendiente de Validación</h2>' +
                        '<p>' + (data.message || 'Tu reciclaje será validado') + '</p>' +
                        '<p>Cashback: ' + (data.product_name || '') + ' — ' + (data.cashback || 0).toLocaleString('es-CL') + ' CLP</p>' +
                        '<p class="pending-note">🚛 El cashback se acredita cuando se confirme la recogida</p>';
                }
            } else if (data.error) {
                cardDiv.className = 'result-card error';
                if (data.fraud) {
                    cardDiv.innerHTML =
                        '<h2>⚠️ Validación Requerida</h2>' +
                        '<p>' + data.error + '</p>' +
                        '<p>Un administrador revisará tu caso</p>';
                } else {
                    cardDiv.innerHTML =
                        '<h2>❌ ' + (data.reason || 'Error') + '</h2>' +
                        '<p>' + data.error + '</p>' +
                        (data.retry_after ? '<p>Intenta después de: ' + data.retry_after + '</p>' : '');
                }
            }
        })
        .catch(function(err) {
            cardDiv.className = 'result-card error';
            cardDiv.innerHTML = '<h2>❌ Error de Conexión</h2><p>Intenta de nuevo</p>';
            console.error('Scan error:', err);
        });
    }

    // ── Wallet ──
    window.updateWalletDisplay = function() {
        fetch('/kiosk/recycle/wallet', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({}),
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.balance !== undefined) {
                var el = document.querySelector('.wallet-amount');
                if (el) el.textContent = Math.round(data.balance).toLocaleString('es-CL');
                var recycled = document.querySelector('.wallet-recycled');
                if (recycled && data.total_recycled !== undefined) {
                    recycled.textContent = '♻️ ' + data.total_recycled + ' reciclados';
                }
            }
        });
    };

    window.useInPurchase = function() {
        alert('Redirigiendo al kiosko para usar ' + 'CLP en tu compra...');
        // TODO: redirect to kiosk with wallet credit
    };

    window.withdrawCredits = function() {
        var amount = prompt('¿Cuánto deseas retirar?');
        if (!amount) return;

        fetch('/kiosk/recycle/withdraw', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({amount: parseFloat(amount), method: 'flow'}),
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                alert(data.message);
                updateWalletDisplay();
            } else {
                alert(data.error || 'Error al retirar');
            }
        });
    };

    // ── Auto camera ──
    document.addEventListener('DOMContentLoaded', function() {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
                .then(function(stream) {
                    var video = document.createElement('video');
                    video.srcObject = stream;
                    video.setAttribute('playsinline', true);
                    video.style.width = '100%';
                    video.style.height = '100%';
                    video.style.objectFit = 'cover';

                    var scanner = document.getElementById('qrScanner');
                    if (scanner) {
                        scanner.innerHTML = '';
                        scanner.appendChild(video);
                        video.play();
                    }
                })
                .catch(function() {});
        }
    });
});
