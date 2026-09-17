document.addEventListener("DOMContentLoaded", function () {
    // ---------- Menus déroulants (Matériel / Réactifs) ----------
    const toggles = document.querySelectorAll(".dropdown-toggle");

    toggles.forEach(function (toggle) {
        toggle.addEventListener("click", function () {
            const targetId = toggle.getAttribute("data-target");
            const menu = document.getElementById(targetId);
            const isOpen = menu.classList.contains("open");

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

    document.addEventListener("click", function (event) {
        if (!event.target.closest(".dropdown-group")) {
            closeAllMenus();
        }
    });

    function closeAllMenus() {
        document.querySelectorAll(".dropdown-menu.open").forEach(function (menu) {
            menu.classList.remove("open");
        });
        document.querySelectorAll(".dropdown-toggle.open").forEach(function (toggle) {
            toggle.classList.remove("open");
        });
    }

    // ---------- État de la paillasse ----------
    const workbenchSurface = document.getElementById("workbenchSurface");
    const workbenchPlaceholder = document.getElementById("workbenchPlaceholder");

    let containerCounter = 0;
    let selectedContainerId = null;
    // Structure gardée en mémoire pour l'étape suivante (envoi au serveur)
    const benchState = {};

    function selectContainer(containerId) {
        document.querySelectorAll(".bench-container").forEach(function (el) {
            el.classList.remove("selected");
        });
        selectedContainerId = containerId;
        const el = document.querySelector('.bench-container[data-container-id="' + containerId + '"]');
        if (el) el.classList.add("selected");
    }

    function createContainer(name, iconUrl) {
        containerCounter += 1;
        const containerId = "c" + containerCounter;

        benchState[containerId] = {
            material: name,
            pours: []
        };

        const wrapper = document.createElement("div");
        wrapper.className = "bench-item bench-container";
        wrapper.setAttribute("data-container-id", containerId);

        const body = document.createElement("div");
        body.className = "container-body";
        if (iconUrl) {
            const img = document.createElement("img");
            img.src = iconUrl;
            img.style.width = "24px";
            img.style.height = "24px";
            img.style.margin = "auto";
            body.appendChild(img);
        } else {
            const fallback = document.createElement("i");
            fallback.setAttribute("data-lucide", "flask-round");
            fallback.className = "container-icon-fallback";
            fallback.style.width = "22px";
            fallback.style.height = "22px";
            body.appendChild(fallback);
            if (window.lucide) window.lucide.createIcons();
        }

        const nameEl = document.createElement("div");
        nameEl.className = "container-name";
        nameEl.textContent = name;

        const contentsEl = document.createElement("div");
        contentsEl.className = "container-contents";
        contentsEl.textContent = "Vide";

        const hintEl = document.createElement("div");
        hintEl.className = "container-select-hint";
        hintEl.textContent = "Cliquez pour sélectionner";

        wrapper.appendChild(body);
        wrapper.appendChild(nameEl);
        wrapper.appendChild(contentsEl);
        wrapper.appendChild(hintEl);

        wrapper.addEventListener("click", function () {
            selectContainer(containerId);
        });

        workbenchSurface.appendChild(wrapper);
        if (workbenchPlaceholder) workbenchPlaceholder.style.display = "none";

        selectContainer(containerId);
    }

    function pourReagentIntoContainer(containerId, reagentName, color, volume) {
        const state = benchState[containerId];
        if (!state) return;

        state.pours.push({ reagent: reagentName, volume: volume });

        const wrapper = document.querySelector('.bench-container[data-container-id="' + containerId + '"]');
        if (!wrapper) return;

        const body = wrapper.querySelector(".container-body");
        const layer = document.createElement("div");
        layer.className = "container-liquid-layer";
        layer.style.background = color;
        layer.style.height = "14px";
        body.insertBefore(layer, body.firstChild);

        const contentsEl = wrapper.querySelector(".container-contents");
        const summary = state.pours
            .map(function (p) { return p.reagent + " (" + p.volume + " mL)"; })
            .join(", ");
        contentsEl.textContent = summary;
    }

    // ---------- Fenêtre de saisie du volume ----------
    const volumeModalOverlay = document.getElementById("volumeModalOverlay");
    const volumeModalReagent = document.getElementById("volumeModalReagent");
    const volumeModalContainer = document.getElementById("volumeModalContainer");
    const volumeInput = document.getElementById("volumeInput");
    const volumeModalError = document.getElementById("volumeModalError");
    const volumeCancel = document.getElementById("volumeCancel");
    const volumeConfirm = document.getElementById("volumeConfirm");

    let pendingReagent = null;

    function openVolumeModal(reagentName, color) {
        const containerState = benchState[selectedContainerId];
        pendingReagent = { name: reagentName, color: color };

        volumeModalReagent.textContent = reagentName;
        volumeModalContainer.textContent = containerState ? containerState.material : "—";
        volumeInput.value = "";
        volumeModalError.textContent = "";
        volumeModalOverlay.classList.add("open");
        volumeInput.focus();
    }

    function closeVolumeModal() {
        volumeModalOverlay.classList.remove("open");
        pendingReagent = null;
    }

    volumeCancel.addEventListener("click", closeVolumeModal);

    volumeModalOverlay.addEventListener("click", function (event) {
        if (event.target === volumeModalOverlay) closeVolumeModal();
    });

    volumeConfirm.addEventListener("click", function () {
        const rawValue = volumeInput.value.trim();
        const value = parseFloat(rawValue);

        if (rawValue === "" || isNaN(value) || value <= 0) {
            volumeModalError.textContent = "Indiquez un volume valide, supérieur à 0.";
            return;
        }

        pourReagentIntoContainer(selectedContainerId, pendingReagent.name, pendingReagent.color, value);
        closeVolumeModal();
    });

    // ---------- Clic sur un élément du menu (matériel ou réactif) ----------
    document.querySelectorAll(".dropdown-item").forEach(function (item) {
        item.addEventListener("click", function () {
            const type = item.getAttribute("data-type");
            const name = item.getAttribute("data-name");

            if (type === "material") {
                const iconUrl = item.getAttribute("data-icon");
                createContainer(name, iconUrl);
                closeAllMenus();
                return;
            }

            // type === "reagent"
            if (!selectedContainerId) {
                alert("Choisissez d'abord un récipient sur la paillasse, puis sélectionnez-le avant de verser un réactif.");
                closeAllMenus();
                return;
            }

            const color = item.getAttribute("data-color") || "#3498db";
            closeAllMenus();
            openVolumeModal(name, color);
        });
    });

    // ---------- Réinitialiser la paillasse ----------
    const resetButton = document.getElementById("resetBench");
    if (resetButton) {
        resetButton.addEventListener("click", function () {
            document.querySelectorAll(".bench-item").forEach(function (el) {
                el.remove();
            });
            Object.keys(benchState).forEach(function (key) { delete benchState[key]; });
            selectedContainerId = null;
            containerCounter = 0;
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

    function getCsrfToken() {
        const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        return input ? input.value : "";
    }

    function buildPayload() {
        const containers = Object.keys(benchState).map(function (id) {
            return {
                material: benchState[id].material,
                pours: benchState[id].pours
            };
        });
        return { containers: containers };
    }

    function applyResults(data) {
        document.querySelectorAll("[data-indicator-result]").forEach(function (el) {
            const indicatorId = el.getAttribute("data-indicator-id");
            const entry = data.indicators ? data.indicators[indicatorId] : null;
            if (entry) {
                el.textContent = "";
                if (typeof entry.value === "string" && entry.value.match(/^#[0-9a-f]{6}$/i)) {
                    el.innerHTML = '<span class="color-swatch" style="background:' + entry.value + '"></span>';
                } else if (typeof entry.value === "boolean") {
                    el.textContent = entry.value ? "Oui" : "Non";
                } else if (entry.value !== null && entry.value !== undefined) {
                    el.textContent = entry.value + (entry.unit || "");
                } else {
                    el.textContent = el.getAttribute("data-default");
                }
            } else {
                el.textContent = el.getAttribute("data-default");
            }
        });

        if (statusBadge) {
            if (data.is_successful) {
                statusBadge.innerHTML = '<span class="status-dot"></span> Expérience réussie (' + data.score + '%)';
            } else {
                statusBadge.innerHTML = '<span class="status-dot"></span> À corriger (' + data.score + '%)';
            }
        }

        const feedbackPanel = document.getElementById("resultFeedback");
        const feedbackList = document.getElementById("feedbackList");
        if (feedbackPanel && feedbackList) {
            feedbackList.innerHTML = "";

            if (data.details && data.details.length > 0) {
                data.details.forEach(function (detail) {
                    const li = document.createElement("li");
                    li.className = "feedback-item " + (detail.correct ? "correct" : "incorrect");

                    const icon = document.createElement("span");
                    icon.className = "feedback-icon";
                    icon.innerHTML = '<i data-lucide="' + (detail.correct ? "check-circle-2" : "x-circle") + '" style="width:18px;height:18px"></i>';

                    const text = document.createElement("span");
                    text.textContent = detail.reagent + " : " + detail.actual + " mL versés (attendu : " + detail.target + " mL)";

                    li.appendChild(icon);
                    li.appendChild(text);
                    feedbackList.appendChild(li);
                });
                feedbackPanel.style.display = "block";
                if (window.lucide) window.lucide.createIcons();
            } else {
                feedbackPanel.style.display = "none";
            }
        }
    }

    if (startButton) {
        startButton.addEventListener("click", function () {
            const containerIds = Object.keys(benchState);
            const hasPours = containerIds.some(function (id) { return benchState[id].pours.length > 0; });

            if (!hasPours) {
                alert("Versez au moins un réactif dans un récipient avant de démarrer.");
                return;
            }

            const submitUrl = startButton.getAttribute("data-submit-url");

            startButton.disabled = true;
            if (statusBadge) {
                statusBadge.innerHTML = '<span class="status-dot"></span> Expérience en cours…';
            }

            let progress = 0;
            const interval = setInterval(function () {
                progress += 20;
                if (progress <= 80) {
                    if (progressFill) progressFill.style.width = progress + "%";
                    if (progressPercent) progressPercent.textContent = progress + "%";
                }
            }, 200);

            fetch(submitUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken()
                },
                body: JSON.stringify(buildPayload())
            })
                .then(function (response) {
                    if (!response.ok) throw new Error("Réponse serveur invalide");
                    return response.json();
                })
                .then(function (data) {
                    clearInterval(interval);
                    if (progressFill) progressFill.style.width = "100%";
                    if (progressPercent) progressPercent.textContent = "100%";
                    startButton.disabled = false;
                    applyResults(data);
                })
                .catch(function (error) {
                    clearInterval(interval);
                    startButton.disabled = false;
                    resetProgress();
                    alert("Une erreur est survenue pendant le calcul des résultats.");
                    console.error(error);
                });
        });
    }
});