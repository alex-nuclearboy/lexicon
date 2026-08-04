"use strict";

const passwordToggles = document.querySelectorAll(
    ".password-control__toggle"
);

passwordToggles.forEach((passwordToggle) => {
    const passwordInput = document.getElementById(
        passwordToggle.getAttribute("aria-controls")
    );

    const toggleText = passwordToggle.querySelector(
        ".password-control__toggle-text"
    );

    if (!passwordInput || !toggleText) {
        return;
    }

    passwordToggle.addEventListener("click", () => {
        const passwordIsVisible =
            passwordInput.type === "text";

        passwordInput.type = passwordIsVisible
            ? "password"
            : "text";

        passwordToggle.setAttribute(
            "aria-pressed",
            String(!passwordIsVisible)
        );

        toggleText.textContent = passwordIsVisible
            ? passwordToggle.dataset.showLabel
            : passwordToggle.dataset.hideLabel;
    });
});
