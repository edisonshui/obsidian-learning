const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");
const { parseLog, readLog } = require("../lib/log");

const SAMPLE = `---
type: learning-chat-log
---

# Chat log

> [!info] Live note
> This updates while you chat.

## Conversation — 2026-10-26

*claude-opus-5-5 · medium effort*

> [!quote] You · 14:21
> /learn-start cs124-quiz9

Here are the criteria.

1. One
2. Two

> [!question] Question · 14:22
> **How much time?**
>
> - **About 60 min** — One session
> - **About 2 hours** — Two sessions

> [!quote] Your answer · 14:25
> **How much time?**
>
> About 2 hours

> [!thinking]+ Thinking (shown in the terminal)
> A note to self.

> [!question] Question · 15:46
> Which one compiles?
>
> - **A** — first

> [!warning] Probe check · 15:46
> Withdrawn before it was asked.

> [!quote] Your answer · 15:46
> PreToolUse:AskUserQuestion hook error: This probe may not stand alone.

> [!question] Question · 15:46
> Which one compiles?
>
> - **A** — first

> [!code] Your code · 15:50
> \`\`\`java
> class A {}
> \`\`\`

Correct.
`;

test("splits conversations and reads the model line", () => {
  const convos = parseLog(SAMPLE);
  assert.equal(convos.length, 1);
  assert.equal(convos[0].date, "2026-10-26");
  assert.equal(convos[0].model, "claude-opus-5-5 · medium effort");
});

test("the info callout before the first conversation is not an item", () => {
  const kinds = parseLog(SAMPLE)[0].items.map((x) => x.kind);
  assert.ok(!kinds.includes("info"));
  assert.equal(kinds[0], "you");
});

test("tutor text between callouts keeps its Markdown", () => {
  const tutor = parseLog(SAMPLE)[0].items.find((x) => x.kind === "tutor");
  assert.match(tutor.text, /^Here are the criteria\.\n\n1\. One/);
});

test("a question carries its options and the learner's pick", () => {
  const q = readLog(SAMPLE)[0].items.find((x) => x.kind === "question");
  assert.deepEqual(q.groups[0].options.map((o) => o.label), ["About 60 min", "About 2 hours"]);
  assert.deepEqual(q.picked, ["About 2 hours"]);
  assert.equal(q.answered, true);
});

test("a hook error is never shown as the learner's answer", () => {
  const items = readLog(SAMPLE)[0].items;
  assert.ok(!items.some((x) => x.kind === "answer" && /hook error/.test(x.text)));
});

test("a question the hook held back and asked again shows once", () => {
  const qs = readLog(SAMPLE)[0].items.filter((x) => x.kind === "question" && /compiles/.test(x.text));
  assert.deepEqual(qs.map((q) => q.withdrawn), [true, false]);
});

test("the last question with no answer after it is still waiting", () => {
  const qs = readLog(SAMPLE)[0].items.filter((x) => x.kind === "question");
  assert.equal(qs[qs.length - 1].answered, false);
});

test("code sent from the runner is its own kind", () => {
  const code = parseLog(SAMPLE)[0].items.find((x) => x.kind === "code");
  assert.match(code.text, /class A \{\}/);
});

test("every real subject log in the vault parses without throwing", () => {
  const root = path.join(__dirname, "..", "..", "learn", "subjects");
  if (!fs.existsSync(root)) return;
  for (const slug of fs.readdirSync(root)) {
    const file = path.join(root, slug, "log.md");
    if (fs.existsSync(file)) assert.ok(Array.isArray(readLog(fs.readFileSync(file, "utf8"))), slug);
  }
});
