/* ============================================================
   ChemLab Virtual — Navbar
   Comportements : scroll (compact + progression), tiroir mobile,
   recherche (filtre vivant + redirection), menu profil.
   Aucune dépendance externe.
   ============================================================ */
(function () {
    "use strict";

    function ready(fn) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", fn);
        } else {
            fn();
        }
    }

    var MOBILE_QUERY = "(max-width: 1024px)";

    ready(function () {
        var navbar = document.getElementById("chemlabNavbar");
        var nav = document.getElementById("navbarNav");
        var burger = document.getElementById("navbarBurger");
        var overlay = document.getElementById("navbarOverlay");
        var progress = document.getElementById("navbarProgress");

        var search = document.getElementById("navbarSearch");
        var searchToggle = document.getElementById("navbarSearchToggle");
        var searchInput = document.getElementById("navbarSearchInput");
        var searchClear = document.getElementById("navbarSearchClear");
        var catalogueUrl = searchInput ? searchInput.getAttribute("data-catalogue-url") : "";

        var user = document.getElementById("navbarUser");
        var userToggle = document.getElementById("navbarUserToggle");

        function isMobile() {
            return window.matchMedia(MOBILE_QUERY).matches;
        }

        /* ---------- Défilement : barre compacte + progression ---------- */
        if (navbar || progress) {
            var ticking = false;
            var onScroll = function () {
                var top = window.scrollY || document.documentElement.scrollTop || 0;

                if (navbar) {
                    if (top > 10) {
                        navbar.classList.add("is-scrolled");
                    } else {
                        navbar.classList.remove("is-scrolled");
                    }
                }

                if (progress) {
                    var doc = document.documentElement;
                    var max = doc.scrollHeight - window.innerHeight;
                    var ratio = max > 0 ? (top / max) * 100 : 0;
                    progress.style.width = Math.min(100, Math.max(0, ratio)) + "%";
                }
                ticking = false;
            };

            window.addEventListener("scroll", function () {
                if (!ticking) {
                    ticking = true;
                    window.requestAnimationFrame(onScroll);
                }
            }, { passive: true });

            onScroll();
        }

        /* ---------------------- Tiroir mobile ---------------------- */
        function openMenu() {
            if (!nav) return;
            nav.classList.add("is-open");
            if (burger) {
                burger.classList.add("is-open");
                burger.setAttribute("aria-expanded", "true");
                burger.setAttribute("aria-label", "Fermer le menu");
            }
            if (overlay) overlay.classList.add("is-visible");
            document.body.classList.add("navbar-lock");
        }

        function closeMenu() {
            if (!nav) return;
            nav.classList.remove("is-open");
            if (burger) {
                burger.classList.remove("is-open");
                burger.setAttribute("aria-expanded", "false");
                burger.setAttribute("aria-label", "Ouvrir le menu");
            }
            if (overlay) overlay.classList.remove("is-visible");
            document.body.classList.remove("navbar-lock");
        }

        if (burger && nav) {
            burger.addEventListener("click", function () {
                if (nav.classList.contains("is-open")) {
                    closeMenu();
                } else {
                    openMenu();
                }
            });

            /* Un clic sur un lien referme le tiroir */
            nav.addEventListener("click", function (event) {
                if (event.target.closest("a")) closeMenu();
            });
        }

        if (overlay) overlay.addEventListener("click", closeMenu);

        /* ---------------------- Menu profil ---------------------- */
        function closeUserMenu() {
            if (user) {
                user.classList.remove("is-open");
                if (userToggle) userToggle.setAttribute("aria-expanded", "false");
            }
        }

        if (user && userToggle) {
            userToggle.addEventListener("click", function (event) {
                event.stopPropagation();
                var open = user.classList.toggle("is-open");
                userToggle.setAttribute("aria-expanded", open ? "true" : "false");
            });
        }

        /* ---------------------- Recherche ---------------------- */
        function cards() {
            return document.querySelectorAll(".experiment-grid .experiment-card");
        }

        function applyFilter(term) {
            var list = cards();
            if (!list.length) return;
            var needle = term.trim().toLowerCase();
            Array.prototype.forEach.call(list, function (card) {
                var haystack = (card.textContent || "").toLowerCase();
                card.hidden = needle !== "" && haystack.indexOf(needle) === -1;
            });
        }

        function openSearch() {
            if (!search) return;
            search.classList.add("is-open");
            if (searchToggle) searchToggle.setAttribute("aria-expanded", "true");
            if (searchInput) searchInput.focus();
        }

        function closeSearch() {
            if (!search) return;
            search.classList.remove("is-open");
            if (searchToggle) searchToggle.setAttribute("aria-expanded", "false");
        }

        if (searchToggle) {
            searchToggle.addEventListener("click", function (event) {
                event.stopPropagation();
                if (search && search.classList.contains("is-open")) {
                    closeSearch();
                } else {
                    openSearch();
                }
            });
        }

        if (searchInput) {
            /* Restaure une recherche transmise par ?q=... */
            var query = new URLSearchParams(window.location.search).get("q");
            if (query) {
                searchInput.value = query;
                applyFilter(query);
            }

            searchInput.addEventListener("input", function () {
                if (cards().length) applyFilter(searchInput.value);
            });

            searchInput.addEventListener("keydown", function (event) {
                if (event.key !== "Enter") return;
                event.preventDefault();
                var term = searchInput.value.trim();

                if (cards().length) {
                    applyFilter(term);
                } else if (catalogueUrl) {
                    window.location.href = catalogueUrl + (term ? "?q=" + encodeURIComponent(term) : "");
                }
            });
        }

        if (searchClear && searchInput) {
            searchClear.addEventListener("click", function () {
                searchInput.value = "";
                applyFilter("");
                searchInput.focus();
            });
        }

        /* -------- Fermetures globales (clic extérieur / Échap) -------- */
        document.addEventListener("click", function (event) {
            if (search && !search.contains(event.target)) closeSearch();
            if (user && !user.contains(event.target)) closeUserMenu();
        });

        document.addEventListener("keydown", function (event) {
            if (event.key !== "Escape") return;
            closeMenu();
            closeSearch();
            closeUserMenu();
        });

        /* -------- Réinitialise l'état au passage desktop -------- */
        window.addEventListener("resize", function () {
            if (!isMobile()) closeMenu();
        });
    });
})();