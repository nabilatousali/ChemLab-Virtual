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
    // Structure gardée en mémoire pour l'analyse (envoi au serveur)
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

    // ---------- Alerte de sécurité avant versement ----------
    const DANGER_CODES = ["GHS01", "GHS02", "GHS03", "GHS05", "GHS06", "GHS08"];
    let ghsLabels = {};
    try {
        ghsLabels = JSON.parse(document.getElementById("ghs-labels").textContent);
    } catch (error) {
        ghsLabels = {};
    }

    const safetyModalOverlay = document.getElementById("safetyModalOverlay");
    const safetyModalReagent = document.getElementById("safetyModalReagent");
    const safetyModalChips = document.getElementById("safetyModalChips");
    const safetyModalAdvice = document.getElementById("safetyModalAdvice");
    const safetyModalIncompatible = document.getElementById("safetyModalIncompatible");
    const safetyCancel = document.getElementById("safetyCancel");
    const safetyConfirm = document.getElementById("safetyConfirm");

    let pendingPour = null;

    function hazardCodes(value) {
        return (value || "").split(",").map(function (code) {
            return code.trim().toUpperCase();
        }).filter(Boolean);
    }

    function safetyChip(code, label) {
        const chip = document.createElement("span");
        chip.className = "safety-chip " + (DANGER_CODES.indexOf(code) >= 0 ? "danger" : "warning");
        chip.textContent = code + " · " + (label || ghsLabels[code] || "Danger");
        return chip;
    }

    function incompatibleInContainer(containerId, incompatibleList) {
        const state = benchState[containerId];
        if (!state || !incompatibleList.length) return [];
        const present = {};
        state.pours.forEach(function (pour) { present[pour.reagent] = true; });
        return incompatibleList.filter(function (name) { return present[name]; });
    }

    function openSafetyModal(name, codes, advice, conflicts) {
        safetyModalReagent.textContent = name;
        safetyModalChips.innerHTML = "";
        codes.forEach(function (code) {
            safetyModalChips.appendChild(safetyChip(code));
        });
        safetyModalAdvice.textContent = advice || "";
        safetyModalAdvice.style.display = advice ? "block" : "none";
        if (conflicts.length > 0) {
            safetyModalIncompatible.textContent = "Incompatible avec déjà présent : "
                + conflicts.join(", ") + " — risque de réaction dangereuse.";
            safetyModalIncompatible.style.display = "block";
        } else {
            safetyModalIncompatible.style.display = "none";
        }
        safetyModalOverlay.classList.add("open");
    }

    function closeSafetyModal() {
        safetyModalOverlay.classList.remove("open");
        pendingPour = null;
    }

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

    safetyCancel.addEventListener("click", closeSafetyModal);

    safetyModalOverlay.addEventListener("click", function (event) {
        if (event.target === safetyModalOverlay) closeSafetyModal();
    });

    safetyConfirm.addEventListener("click", function () {
        if (!pendingPour) return;
        const pour = pendingPour;
        closeSafetyModal();
        openVolumeModal(pour.name, pour.color);
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
            const codes = hazardCodes(item.getAttribute("data-hazards"));
            const advice = item.getAttribute("data-advice") || "";
            const incompatible = (item.getAttribute("data-incompatible") || "")
                .split("|").map(function (name) { return name.trim(); }).filter(Boolean);
            const conflicts = incompatibleInContainer(selectedContainerId, incompatible);
            closeAllMenus();
            if (codes.length > 0 || conflicts.length > 0) {
                pendingPour = { name: name, color: color };
                openSafetyModal(name, codes, advice, conflicts);
            } else {
                openVolumeModal(name, color);
            }
        });
    });

    // ---------- Analyser le mélange ----------
    const analyzeButton = document.getElementById("analyzeMixture");
    const statusBadge = document.getElementById("statusBadge");

    function resetAnalysis() {
        if (statusBadge) {
            statusBadge.innerHTML = '<span class="status-dot"></span> Prêt à commencer';
        }
        document.querySelectorAll("[data-indicator-result]").forEach(function (el) {
            el.textContent = el.getAttribute("data-default");
        });
        const feedbackPanel = document.getElementById("resultFeedback");
        if (feedbackPanel) feedbackPanel.style.display = "none";
        const safetyPanel = document.getElementById("safetyPanel");
        if (safetyPanel) safetyPanel.style.display = "none";
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
            statusBadge.innerHTML = '<span class="status-dot"></span> Mélange analysé';
        }

        const feedbackPanel = document.getElementById("resultFeedback");
        const feedbackList = document.getElementById("feedbackList");
        if (feedbackPanel && feedbackList) {
            feedbackList.innerHTML = "";

            if (data.composition && data.composition.length > 0) {
                data.composition.forEach(function (item) {
                    const li = document.createElement("li");
                    li.className = "feedback-item mixed";

                    const icon = document.createElement("span");
                    icon.className = "feedback-icon";
                    const swatch = document.createElement("span");
                    swatch.className = "color-swatch";
                    swatch.style.background = item.color || "#94a3b8";
                    icon.appendChild(swatch);

                    const text = document.createElement("span");
                    text.textContent = item.reagent + " : " + item.volume + " mL (" + item.percent + " %)";

                    li.appendChild(icon);
                    li.appendChild(text);
                    feedbackList.appendChild(li);
                });
            }

            if (data.warnings && data.warnings.length > 0) {
                data.warnings.forEach(function (warning) {
                    const li = document.createElement("li");
                    li.className = "feedback-warning";
                    li.textContent = "Attention : " + warning;
                    feedbackList.appendChild(li);
                });
            }

            feedbackPanel.style.display = "block";
        }

        const safetyPanel = document.getElementById("safetyPanel");
        const safetyChips = document.getElementById("safetyChips");
        const safetyWarnings = document.getElementById("safetyWarnings");
        const safetyAdvice = document.getElementById("safetyAdvice");
        if (safetyPanel && safetyChips && safetyWarnings && safetyAdvice) {
            safetyChips.innerHTML = "";
            safetyWarnings.innerHTML = "";
            safetyAdvice.innerHTML = "";

            const pictograms = (data.safety && data.safety.pictograms) || [];
            const warnings = (data.safety && data.safety.warnings) || [];
            const adviceList = (data.safety && data.safety.advice) || [];

            pictograms.forEach(function (pic) {
                safetyChips.appendChild(safetyChip(pic.code, pic.label));
            });

            warnings.forEach(function (warning) {
                const li = document.createElement("li");
                li.className = "feedback-warning";
                li.textContent = warning;
                safetyWarnings.appendChild(li);
            });

            adviceList.forEach(function (item) {
                const li = document.createElement("li");
                li.className = "safety-advice-item";
                const name = document.createElement("strong");
                name.textContent = item.reagent;
                li.appendChild(name);
                li.appendChild(document.createTextNode(" : " + item.text));
                safetyAdvice.appendChild(li);
            });

            safetyPanel.style.display = (pictograms.length || warnings.length || adviceList.length)
                ? "block"
                : "none";
        }
    }

    if (analyzeButton) {
        analyzeButton.addEventListener("click", function () {
            const containerIds = Object.keys(benchState);
            const hasPours = containerIds.some(function (id) { return benchState[id].pours.length > 0; });

            if (!hasPours) {
                alert("Versez au moins un réactif dans un récipient avant d'analyser.");
                return;
            }

            const submitUrl = analyzeButton.getAttribute("data-submit-url");

            analyzeButton.disabled = true;
            if (statusBadge) {
                statusBadge.innerHTML = '<span class="status-dot"></span> Analyse en cours…';
            }

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
                    analyzeButton.disabled = false;
                    applyResults(data);
                })
                .catch(function (error) {
                    analyzeButton.disabled = false;
                    resetAnalysis();
                    alert("Une erreur est survenue pendant l'analyse du mélange.");
                    console.error(error);
                });
        });
    }

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
            resetAnalysis();
        });
    }
});
