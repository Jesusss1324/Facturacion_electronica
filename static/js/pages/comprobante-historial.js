document.addEventListener('DOMContentLoaded', () => {
  // Manejo de selección de tarjeta en vista dividida mediante delegación
  document.addEventListener('click', (event) => {
    const card = event.target.closest('.invoice-card-item');
    if (!card) return;

    // Si el clic fue directamente en un enlace o botón interno, dejar fluir el evento nativo
    if (event.target.closest('a') || event.target.closest('button')) {
      return;
    }
    const link = card.querySelector('.item-encf-link');
    if (link && link.href) {
      window.location.href = link.href;
    }
  });
});
