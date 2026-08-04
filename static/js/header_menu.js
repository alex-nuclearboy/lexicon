"use strict";

const headerMenus = document.querySelectorAll(
    "[data-header-menu]"
);

const hoverQuery = window.matchMedia(
    "(hover: hover) and (pointer: fine)"
);

headerMenus.forEach((menu) => {
    const toggle = menu.querySelector(
        "[data-header-menu-toggle]"
    );

    const panel = menu.querySelector(
        "[data-header-menu-panel]"
    );

    if (!toggle || !panel) {
        return;
    }

    const setMenuOpen = (isOpen) => {
        menu.dataset.open = String(isOpen);

        toggle.setAttribute(
            "aria-expanded",
            String(isOpen)
        );

        toggle.setAttribute(
            "aria-label",
            isOpen
                ? toggle.dataset.closeLabel
                : toggle.dataset.openLabel
        );

        panel.setAttribute(
            "aria-hidden",
            String(!isOpen)
        );
    };

    const closeMenu = (
        returnFocus = false
    ) => {
        setMenuOpen(false);

        if (returnFocus) {
            toggle.focus();
        }
    };

    toggle.addEventListener("click", () => {
        const isOpen =
            toggle.getAttribute("aria-expanded")
            === "true";

        setMenuOpen(!isOpen);
    });

    menu.addEventListener("mouseenter", () => {
        if (hoverQuery.matches) {
            setMenuOpen(true);
        }
    });

    menu.addEventListener("mouseleave", () => {
        if (
            hoverQuery.matches
            && !menu.contains(document.activeElement)
        ) {
            closeMenu();
        }
    });

    menu.addEventListener("focusin", () => {
        setMenuOpen(true);
    });

    menu.addEventListener("focusout", (event) => {
        const nextElement = event.relatedTarget;

        if (
            !menu.contains(nextElement)
            && !(
                hoverQuery.matches
                && menu.matches(":hover")
            )
        ) {
            closeMenu();
        }
    });

    document.addEventListener("click", (event) => {
        if (!menu.contains(event.target)) {
            closeMenu();
        }
    });

    document.addEventListener("keydown", (event) => {
        const isOpen =
            toggle.getAttribute("aria-expanded")
            === "true";

        if (event.key === "Escape" && isOpen) {
            closeMenu(true);
        }
    });
});
