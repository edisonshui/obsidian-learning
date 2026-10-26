# Obsidian learning vault

A one-to-one AI tutor that runs in Claude Code (or Codex) and keeps what you know as Markdown notes in Obsidian. How it works is in [learn/README.md](learn/README.md).

## Setup

You need [Claude Code](https://claude.com/claude-code) with your own Claude account, [Obsidian](https://obsidian.md), Python 3, and git.

1. Clone this repo: `git clone https://github.com/edisonshui/obsidian-learning.git`
2. In Obsidian, choose *Open folder as vault* and pick the cloned folder. When it asks, trust the vault so its `learn-live` plugin (the live chat log) can run. Then install *Dataview* from *Settings > Community plugins > Browse*.
3. In a terminal, `cd` into the folder and run `claude`.
4. The first session sets up `learn/me/preferences.md` from a template and asks how you like to learn.
5. Start a subject with `/learn-start <topic>`. Next time, `/learn-resume <topic>`. To work problems on what you have learned, `/learn-practice <topic>`.

Your subjects, preferences, and chat logs stay on your machine. `.gitignore` keeps them out of git.
