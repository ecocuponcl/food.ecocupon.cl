/**
 * EcoCupon Recycle - QR Scan & Cashback
 */
odoo.define('ecocupon_recycle.recycle_scan', function(require) {
    'use strict';

    var publicWidget = require('web.public.widget');

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

        // Show loading
        cardDiv.className = 'result-card pending';
        cardDiv.innerHTML = '<h2>⏳ Validando...</h2><p>Verificando autenticidad</p>';
        resultDiv.style.display = 'block';

        // Call backend
        fetch('/kiosk/scan_qr', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({qr_code: qrCode}),
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                cardDiv.className = 'result-card success';
                cardDiv.innerHTML =
                    '<h2>✅ ¡Reciclaje Validado!</h2>' +
                    '<div class="result-amount">+' + Math.round(data.cashback).toLocaleString('es-CL') + ' CLP</div>' +
                    '<p>' + (data.item_name || 'Item') + ' reciclado correctamente</p>' +
                    '<p>💰 Cashback acreditado a tu cuenta</p>';
            } else if (data.pending) {
                cardDiv.className = 'result-card pending';
                cardDiv.innerHTML =
                    '<h2>📋 Pendiente</h2>' +
                    '<p>' + (data.message || 'Tu reciclaje será validado pronto') + '</p>';
            } else if (data.error) {
                cardDiv.className = 'result-card error';
                if (data.fraud) {
                    cardDiv.innerHTML =
                        '<h2>⚠️ Validación Requerida</h2>' +
                        '<p>' + (data.reason || 'Verificación necesaria') + '</p>' +
                        '<p>Un administrador revisará tu reciclaje</p>';
                } else {
                    cardDiv.innerHTML =
                        '<h2>❌ Error</h2>' +
                        '<p>' + data.error + '</p>';
                }
            }
        })
        .catch(function(err) {
            cardDiv.className = 'result-card error';
            cardDiv.innerHTML = '<h2>❌ Error de Conexión</h2><p>Intenta de nuevo</p>';
            console.error('Scan error:', err);
        });
    }

    // Auto-start QR scanner if camera available
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
                .catch(function() {
                    // Camera not available, manual input is fallback
                });
        }
    });
});
