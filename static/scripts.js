function toggleEntries(header) {
    // Get the next sibling element, which should be the <ul> list
    const list = header.nextElementSibling;

    // Toggle the 'hidden' class on the list
    list.classList.toggle('hidden');
}