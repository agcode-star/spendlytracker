// main.js — students will add JavaScript here as features are built

// Render Lucide icons (<i data-lucide="...">) once the DOM is ready.
document.addEventListener("DOMContentLoaded", function () {
    if (window.lucide) {
        window.lucide.createIcons();
    }
});
