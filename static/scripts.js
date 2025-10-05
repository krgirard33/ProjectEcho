document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.date-header').forEach(header => {
        header.style.cursor = 'pointer'; // Indicate it's clickable
        header.addEventListener('click', function () {
            const targetId = this.getAttribute('data-target');
            const targetElement = document.getElementById(targetId);

            if (targetElement) {
                // Toggle the 'hidden' class
                targetElement.classList.toggle('hidden');
            }
        });
    });
});