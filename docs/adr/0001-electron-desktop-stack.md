# Electron, with xterm.js and node-pty, for the desktop app

Edison accepted this on 2026-10-21. The Vault app must run on Windows and Linux as well as macOS, because the friends testing it do not all have Macs. That rules out the native Mac app that brand guideline v0.1 planned ("macOS first, Windows and Linux later"). The app's centre is a real terminal running the learner's own `claude` or `codex`. So the stack is Electron, with xterm.js to draw the terminal and node-pty to run the process. VS Code, Hyper, Tabby, and Wave Terminal use the same pair. T3 Code, OpenAI's Codex app, and Claude desktop all ship on Electron.

## Considered options

- **Tauri 2.** About a seventh of the install size and a quarter of the idle memory. It was rejected for two reasons. Its terminal plugin (`tauri-plugin-pty`, 22 stars) calls itself still in development. It also draws with WebKit on macOS and Linux and WebView2 on Windows, so the Holo light gradients would render three ways, and several teams moved back to Electron over those differences.
- **Native SwiftUI.** Mac only.
- **Flutter, Compose Multiplatform, Avalonia, and Qt.** Each draws its own interface, so the HTML prototype, KaTeX math, and mermaid diagrams would be rebuilt from scratch.

## Consequences

- The download is around 100 MB or more, and the app uses several hundred MB of memory.
- Electron's free update service needs signed macOS builds. Builds are unsigned for now, so friends update by hand.

Evidence and sources: `.scratch/vault-app/stack-research.md` (gitignored, local only).
