/* ============================================================
   ChemLab Virtual — Chat de groupe en temps réel
   Envoi sans rechargement + réception par polling (toutes les
   2,5 s, en pause quand l'onglet est caché). Repli automatique
   sur l'envoi classique si la requête échoue.
   ============================================================ */
(function () {
    "use strict";

    function getCookie(name) {
        var value = "; " + document.cookie;
        var parts = value.split("; " + name + "=");
        if (parts.length === 2) return parts.pop().split(";").shift();
        return "";
    }

    document.addEventListener("DOMContentLoaded", function () {
        var chat = document.getElementById("groupChatMessages");
        if (chat) chat.scrollTop = chat.scrollHeight;
        if (!chat) return;

        var url = chat.getAttribute("data-chat-url");
        if (!url) return;

        var lastId = parseInt(chat.getAttribute("data-last-id") || "0", 10) || 0;
        var form = document.getElementById("groupChatForm");

        function nearBottom() {
            return chat.scrollHeight - chat.scrollTop - chat.clientHeight < 80;
        }

        function appendMessage(msg) {
            if (!msg || !msg.id) return;
            if (chat.querySelector('[data-message-id="' + msg.id + '"]')) return;

            var empty = chat.querySelector(".dropdown-empty");
            if (empty) empty.remove();

            var div = document.createElement("div");
            div.className = "group-chat-message" + (msg.mine ? " mine" : "");
            div.setAttribute("data-message-id", msg.id);

            var sender = document.createElement("span");
            sender.className = "group-chat-sender";
            sender.textContent = msg.sender;

            var text = document.createElement("p");
            text.textContent = msg.content;

            var time = document.createElement("span");
            time.className = "group-chat-time";
            time.textContent = msg.sent_at;

            div.appendChild(sender);
            div.appendChild(text);
            div.appendChild(time);

            var stick = nearBottom();
            chat.appendChild(div);
            if (msg.id > lastId) lastId = msg.id;
            if (stick) chat.scrollTop = chat.scrollHeight;
        }

        function poll() {
            fetch(url + "?after=" + lastId, {
                headers: { "X-Requested-With": "XMLHttpRequest" }
            })
                .then(function (response) {
                    if (!response.ok) throw new Error("polling");
                    return response.json();
                })
                .then(function (data) {
                    (data.messages || []).forEach(appendMessage);
                })
                .catch(function () { /* silencieux : nouvel essai au prochain tour */ });
        }

        setInterval(function () {
            if (!document.hidden) poll();
        }, 2500);

        if (form) {
            form.addEventListener("submit", function (event) {
                event.preventDefault();
                var input = form.querySelector('input[name="content"]');
                var content = input.value.trim();
                if (!content) return;

                fetch(form.action, {
                    method: "POST",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "X-CSRFToken": getCookie("csrftoken")
                    },
                    body: new FormData(form)
                })
                    .then(function (response) {
                        if (!response.ok) throw new Error("envoi");
                        return response.json();
                    })
                    .then(function (data) {
                        if (data.message) appendMessage(data.message);
                        input.value = "";
                    })
                    .catch(function () {
                        form.submit(); // repli : envoi classique avec rechargement
                    });
            });
        }
    });
})();
