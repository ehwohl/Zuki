export default function WindowControls() {
  const close = () => window.close()
  const minimize = () => {
    // PWA window-controls-overlay: delegate to browser built-in where possible
    if ('windowControlsOverlay' in navigator) return
    window.resizeTo(window.outerWidth, 0)
  }

  return (
    <div
      className="fixed top-0 right-0 z-[9999] flex items-center gap-1 px-2 py-1.5 opacity-0 hover:opacity-100 transition-opacity no-drag"
      style={{ transitionDuration: '200ms' }}
    >
      {/* Minimize */}
      <button
        onClick={minimize}
        className="w-5 h-5 flex items-center justify-center rounded-sm border border-[var(--border-color)] hover:border-[var(--accent-warning)] hover:text-[var(--accent-warning)] text-[var(--text-secondary)] transition-colors"
        title="Minimize"
      >
        <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
          <path d="M1 4h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>

      {/* Close */}
      <button
        onClick={close}
        className="w-5 h-5 flex items-center justify-center rounded-sm border border-[var(--border-color)] hover:border-[var(--accent-down,#FF3B5C)] hover:text-[#FF3B5C] text-[var(--text-secondary)] transition-colors"
        title="Close"
      >
        <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
          <path d="M1.5 1.5l5 5M6.5 1.5l-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  )
}
