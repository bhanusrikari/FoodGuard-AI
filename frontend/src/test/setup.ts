import '@testing-library/jest-dom/vitest'

// Native <dialog>.showModal()/close() aren't implemented in jsdom — Modal.tsx
// (and therefore ConfirmDialog) call these directly, so stub them for tests.
if (typeof window !== 'undefined' && window.HTMLDialogElement) {
  window.HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute('open', '')
  }
  window.HTMLDialogElement.prototype.close = function () {
    this.removeAttribute('open')
  }
}
