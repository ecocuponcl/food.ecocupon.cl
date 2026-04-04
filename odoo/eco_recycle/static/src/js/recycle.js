document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("recycleForm");
    if (!form) return;

    const validationType = document.getElementById("validationType");
    const photoSection = document.getElementById("photoSection");

    validationType.addEventListener("change", function () {
        photoSection.style.display = this.value === "photo" ? "block" : "none";
    });

    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const btn = form.querySelector("button[type=submit]");
        btn.disabled = true;
        btn.textContent = "⏳ Validando...";

        const data = {
            qr_token: document.getElementById("qrToken").value,
            phone: document.getElementById("phone").value,
            validation_type: validationType.value,
        };

        // Get GPS if selected
        if (data.validation_type === "gps" && navigator.geolocation) {
            try {
                const pos = await new Promise((resolve, reject) =>
                    navigator.geolocation.getCurrentPosition(resolve, reject)
                );
                data.lat = pos.coords.latitude;
                data.lng = pos.coords.longitude;
            } catch (err) {
                showResult("No se pudo obtener ubicación", "danger");
                btn.disabled = false;
                btn.textContent = "✅ Validar y Recibir Cashback";
                return;
            }
        }

        try {
            const resp = await fetch("/recycle/submit", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(data),
            });
            const result = await resp.json();

            if (result.error) {
                showResult(result.error, "danger");
            } else {
                showResult(
                    `✅ ${result.message} — Saldo: $${result.wallet_balance} CLP`,
                    "success"
                );
            }
        } catch (err) {
            showResult("Error de conexión", "danger");
        }

        btn.disabled = false;
        btn.textContent = "✅ Validar y Recibir Cashback";
    });

    function showResult(msg, type) {
        const el = document.getElementById("result");
        el.style.display = "block";
        el.className = `alert alert-${type}`;
        el.textContent = msg;
    }
});
