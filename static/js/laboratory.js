document.addEventListener("DOMContentLoaded", function () {
    const startButton = document.querySelector(
        '[data-action="start"]'
    );

    const progressBar = document.querySelector(
        ".progress-bar span"
    );

    const progressLabel = document.querySelector(
        ".progress-label strong"
    );

    const timerElement = document.querySelector(
        '[data-result="timer"]'
    );

    let timerInterval = null;
    let seconds = 0;

    function formatTime(value) {
        const minutes = Math.floor(value / 60);
        const remainingSeconds = value % 60;

        return (
            String(minutes).padStart(2, "0") +
            ":" +
            String(remainingSeconds).padStart(2, "0")
        );
    }

    if (startButton) {
        startButton.addEventListener("click", function () {
            startButton.disabled = true;
            startButton.textContent = "Expérience en cours...";

            if (progressBar) {
                progressBar.style.width = "35%";
            }

            if (progressLabel) {
                progressLabel.textContent = "35%";
            }

            timerInterval = window.setInterval(function () {
                seconds += 1;

                if (timerElement) {
                    timerElement.textContent = formatTime(seconds);
                }
            }, 1000);
        });
    }

    document.querySelectorAll(
        '[data-action="reset"]'
    ).forEach(function (button) {
        button.addEventListener("click", function () {
            window.location.reload();
        });
    });

    document.querySelectorAll(
        ".material-item"
    ).forEach(function (material) {
        material.addEventListener("click", function () {
            material.classList.toggle("selected");
        });
    });
});
