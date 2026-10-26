// node-pty ships prebuilt binaries, but npm's script allowlist skips its own
// postinstall, which is what marks spawn-helper executable. Without the bit,
// every terminal fails with "posix_spawnp failed".
const fs = require("fs");
const path = require("path");
const root = path.join(__dirname, "..", "node_modules", "node-pty", "prebuilds");
for (const dir of fs.existsSync(root) ? fs.readdirSync(root) : []) {
  const helper = path.join(root, dir, "spawn-helper");
  if (fs.existsSync(helper)) fs.chmodSync(helper, 0o755);
}
