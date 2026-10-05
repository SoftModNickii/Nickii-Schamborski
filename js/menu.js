// Aufklappmenue oben rechts, auf allen Seiten gleich.
// Schaltflaeche statt div, damit es per Tastatur und Screenreader
// erreichbar ist. Escape und ein Klick daneben schliessen es.
(function () {
    const toggle = document.querySelector('.menu-toggle');
    const menu = document.getElementById('menuDropdown');
    if (!toggle || !menu) return;

    function setOpen(open) {
        menu.classList.toggle('active', open);
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    toggle.addEventListener('click', function (event) {
        event.stopPropagation();
        const open = !menu.classList.contains('active');
        setOpen(open);
        if (open) {
            const first = menu.querySelector('a');
            if (first) first.focus();
        }
    });

    document.addEventListener('click', function (event) {
        if (!toggle.contains(event.target) && !menu.contains(event.target)) {
            setOpen(false);
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && menu.classList.contains('active')) {
            setOpen(false);
            toggle.focus();
        }
    });
})();
