// Flash icon set, drawn by Claude and picked by Edison on 26 Oct 2026 (option A,
// tinted tile). 24px grid, 2px margin, round caps and joins, no fills. Stroke
// width is set per size by the --icon-* tokens, so every line lands near 1.4px.
// search, sidebar, check, and send keep the shapes of the Vault icon set, whose
// originals came from Lucide (ISC license). icons/*.svg are generated from this file.
const P = {
  // subjects
  code: '<path d="M8.5 7.5 4 12l4.5 4.5M15.5 7.5 20 12l-4.5 4.5M13.6 5.5l-3.2 13"/>',
  math: '<path d="M16.5 5.6c-.5-1-1.5-1.6-2.5-1.4-1.2.2-1.8 1.3-1.9 2.5l-.9 10.6c-.1 1.2-.7 2.3-1.9 2.5-1 .2-2-.4-2.5-1.4"/>',
  literature: '<path d="M12 6.8C10 5.2 7 4.6 3.8 5v13.6c3.2-.4 6.2.2 8.2 1.8 2-1.6 5-2.2 8.2-1.8V5C17 4.6 14 5.2 12 6.8zM12 6.8v13.6"/>',
  circuits: '<path d="M2.5 12h3l1.8-5.5 3.1 11 3.2-11 3.1 11 1.8-5.5h3"/>',
  design: '<circle cx="9" cy="9" r="5"/><rect x="10.5" y="10.5" width="9.5" height="9.5" rx="2"/>',
  calm: '<path d="M5 19C5 10.6 10.6 5 19 5c0 8.4-5.6 14-14 14zM5 19l7.5-7.5"/>',
  // screens
  home: '<path d="M4 10.4 12 4l8 6.4V19a1 1 0 0 1-1 1h-4.5v-5.5h-5V20H5a1 1 0 0 1-1-1z"/>',
  session: '<path d="M5 5h14a1.5 1.5 0 0 1 1.5 1.5v9A1.5 1.5 0 0 1 19 17h-8.2l-4.3 3.3V17H5a1.5 1.5 0 0 1-1.5-1.5v-9A1.5 1.5 0 0 1 5 5z"/>',
  skills: '<circle cx="12" cy="5.5" r="2.3"/><circle cx="6" cy="18.5" r="2.3"/><circle cx="18" cy="18.5" r="2.3"/><path d="M11 7.6 7 16.4M13 7.6l4 8.8"/>',
  dashboard: '<rect x="4" y="4" width="7" height="7" rx="1.6"/><rect x="13" y="4" width="7" height="7" rx="1.6"/><rect x="4" y="13" width="7" height="7" rx="1.6"/><rect x="13" y="13" width="7" height="7" rx="1.6"/>',
  settings: '<path d="M4 7.5h8.5M17.5 7.5H20M4 16.5h2.5M11.5 16.5H20"/><circle cx="15" cy="7.5" r="2.5"/><circle cx="9" cy="16.5" r="2.5"/>',
  // actions
  review: '<path d="M19.5 9A8 8 0 0 0 5 7.2M4.5 3.8v3.7h3.7M4.5 15A8 8 0 0 0 19 16.8M19.5 20.2v-3.7h-3.7"/>',
  repair: '<rect x="2.6" y="8.2" width="18.8" height="7.6" rx="3.8" transform="rotate(-45 12 12)"/><path d="M9.2 9.2l5.6 5.6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  hint: '<path d="M9.5 17.5h5M10.3 20.5h3.4M12 3.5a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2V17h5v-.6c0-.8.4-1.5 1-2A6 6 0 0 0 12 3.5z"/>',
  checkme: '<circle cx="12" cy="12" r="8.5"/><path d="m8.4 12.3 2.5 2.5 4.7-5.1"/>',
  pause: '<path d="M5.5 9h11v4.5a5 5 0 0 1-5 5h-1a5 5 0 0 1-5-5zM16.5 10.5h1a2.5 2.5 0 0 1 0 5h-1.2M9 3.5v2.5M13 3.5v2.5"/>',
  end: '<path d="M5.5 21V4M5.5 4.5h11.5l-2.2 4 2.2 4H5.5"/>',
  resume: '<path d="M8 5.5v13l10.5-6.5z"/>',
  note: '<path d="M6 3.5h8.5L19 8v12.5H6z"/><path d="M14 3.5V8.5h5M9 12.5h7M9 16h5"/>',
  terminal: '<rect x="3" y="4.5" width="18" height="15" rx="2"/><path d="m7 9.5 3 2.5-3 2.5M12.5 15h4.5"/>',
  send: '<path d="M12 19V5.5M6.5 11 12 5.5l5.5 5.5"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/>',
  sidebar: '<rect x="3.5" y="4" width="17" height="16" rx="2"/><path d="M9.5 4v16"/>',
  chev: '<path d="m9.5 6 6 6-6 6"/>',
  check: '<path d="M5 12.5 9.5 17 19 7.5"/>',
  stop: '<rect x="7" y="7" width="10" height="10" rx="2"/>',
  streak: '<path d="M12 3.5c.5 3 4.5 5 4.5 9.5a4.5 4.5 0 0 1-9 0c0-2 1-3.2 2-4 .2 1.6 1 2.5 2 2.5 0-3 .5-5.5.5-8z"/>',
};
const ic = (n, cls = "") => `<svg class="ico ${cls}" viewBox="0 0 24 24" aria-hidden="true">${P[n]}</svg>`;
if (typeof module !== 'undefined') module.exports = { P, ic };
