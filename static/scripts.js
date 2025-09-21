document.addEventListener('DOMContentLoaded', function () {
    const dateHeaders = document.querySelectorAll('.date-section .date-header');

    dateHeaders.forEach(header => {
        header.addEventListener('click', function () {
            const list = this.nextElementSibling;
            list.classList.toggle('hidden');
        });
    });
});