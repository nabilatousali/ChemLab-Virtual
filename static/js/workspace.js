document.addEventListener("DOMContentLoaded", function () {
    // ---------- Menus déroulants (Matériel / Réactifs) ----------
    const toggles = document.querySelectorAll(".dropdown-toggle");

    toggles.forEach(function (toggle) {
        toggle.addEventListener("click", function () {
            const targetId = toggle.getAttribute("data-target");
            const menu = document.getElementById(targetId);
            const isOpen = menu.classList.contains("open");

            // Ferme tous les autres menus avant d'ouvrir celui-ci
            document.querySelectorAll(".dropdown-menu.open").forEach(function (openMenu) {
                openMenu.classList.remove("open");
            });
            document.querySelectorAll(".dropdown-toggle.open").forEach(function (openToggle) {
                openToggle.classList.remove("open");
            });

            if (!isOpen) {
                menu.classList.add("open");
                toggle.classList.add("open");
            }
        });
    });

    // Ferme les menus si on clique ailleurs sur la page
    document.addEventListener("click", function (event) {
        if (!event.target.closest(".dropdown-group")) {
            document.querySelectorAll(".dropdown-menu.open").forEach(function (menu) {
                menu.classList.remove("open");
            });
            document.querySelectorAll(".dropdown-toggle.open").forEach(function (toggle) {
                toggle.classList.remove("open");
            });
        }
    });

    // ---------- Ajout d'un élément sur la paillasse ----------
    const workbenchSurface = document.getElementById("workbenchSurface");
    const workbenchPlaceholder = document.getElementById("workbenchPlaceholder");

    document.querySelectorAll(".dropdown-item").forEach(function (item) {
        item.addEventListener("click", function () {
            const type = item.getAttribute("data-type");
            const name = item.getAttribute("data-name");

            const benchItem = document.createElement("div");
            benchItem.className = "bench-item";

            const icon = document.createElement("div");
            icon.className = "bench-item-icon";

            if (type === "material") {
                const iconUrl = item.getAttribute("data-icon");
                if (iconUrl) {
                    const img = document.createElement("img");
                    img.src = iconUrl;
                    img.style.width = "20px";
                    img.style.height = "20px";
                    icon.appendChild(img);
                } else {
                    icon.textContent = "🧪";
                }
            } else {
                const color = item.getAttribute("data-color") || "#3498db";
                icon.style.background = color;
            }

            const label = document.createElement("span");
            label.textContent = name;

            benchItem.appendChild(icon);
            benchItem.appendChild(label);
            workbenchSurface.appendChild(benchItem);

            if (workbenchPlaceholder) {
                workbenchPlaceholder.style.display = "none";
            }

            // Referme le menu après sélection
            document.querySelectorAll(".dropdown-menu.open").forEach(function (menu) {
                menu.classList.remove("open");
            });
            document.querySelectorAll(".dropdown-toggle.open").forEach(function (toggle) {
                toggle.classList.remove("open");
            });
        });
    });

    // ---------- Réinitialiser la paillasse ----------
    const resetButton = document.getElementById("resetBench");
    if (resetButton) {
        resetButton.addEventListener("click", function () {
            document.querySelectorAll(".bench-item").forEach(function (el) {
                el.remove();
            });
            if (workbenchPlaceholder) {
                workbenchPlaceholder.style.display = "block";
            }
            resetProgress();
        });
    }

    // ---------- Démarrer l'expérience (simulation de progression) ----------
    const startButton = document.getElementById("startExperiment");
    const progressFill = document.getElementById("progressFill");
    const progressPercent = document.getElementById("progressPercent");
    const statusBadge = document.getElementById("statusBadge");

    function resetProgress() {
        if (progressFill) progressFill.style.width = "0%";
        if (progressPercent) progressPercent.textContent = "0%";
        if (statusBadge) {
            statusBadge.innerHTML = '<span class="status-dot"></span> Prêt à commencer';
        }
        document.querySelectorAll("[data-indicator-result]").forEach(function (el) {
            el.textContent = el.getAttribute("data-default");
        });
    }

    if (startButton) {
        startButton.addEventListener("click", function () {
            const benchItems = document.querySelectorAll(".bench-item");
            if (benchItems.length === 0) {
                alert("Ajoutez au moins un matériel ou un réactif sur la paillasse avant de démarrer.");
                return;
            }

            startButton.disabled = true;
            if (statusBadge) {
                statusBadge.innerHTML = '<span class="status-dot"></span> Expérience en cours…';
            }

            let progress = 0;
            const interval = setInterval(function () {
                progress += 20;
                if (progressFill) progressFill.style.width = progress + "%";
                if (progressPercent) progressPercent.textContent = progress + "%";

                if (progress >= 100) {
                    clearInterval(interval);
                    startButton.disabled = false;
                    if (statusBadge) {
                        statusBadge.innerHTML = '<span class="status-dot"></span> Expérience terminée';
                    }
                    // NOTE : les valeurs affichées ici sont un espace réservé.
                    // Le calcul réel des résultats (moteur de réaction) reste à brancher.
                    document.querySelectorAll("[data-indicator-result]").forEach(function (el) {
                        el.textContent = "—";
                    });
                }
            }, 400);
        });
    }
});