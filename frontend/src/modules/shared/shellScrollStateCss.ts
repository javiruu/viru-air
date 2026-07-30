// Next.js 15.5 Turbopack cannot parse scroll-state container queries in imported CSS.
export const SHELL_SCROLL_STATE_CSS = `
@supports (container-type: scroll-state) {
  .shell-header {
    container-type: scroll-state;
  }

  @container scroll-state(stuck: top) {
    .shell-header.shell-header {
      padding: var(--shell-header-stuck-padding-block) var(--shell-header-stuck-padding-inline);
      border-radius: var(--shell-header-stuck-radius);
      border-bottom: none;
      border: var(--shell-header-stuck-border);
      background: var(--shell-header-stuck-bg);
      box-shadow: var(--shell-header-stuck-shadow);
      -webkit-backdrop-filter: blur(var(--shell-header-stuck-backdrop-blur)) saturate(140%);
      backdrop-filter: blur(var(--shell-header-stuck-backdrop-blur)) saturate(140%);
    }
  }
}
`;
