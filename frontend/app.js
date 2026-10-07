// BTube Global Application Script

document.addEventListener('DOMContentLoaded', () => {
    initCategoryChips();
});

function initCategoryChips() {
    const chips = document.querySelectorAll('.cat-chip');
    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            chips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
        });
    });
}
