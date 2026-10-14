"use strict";
/* Learn live: two additions to the tutoring vault, no build step.

   1. Follow. A live chat log (learn/subjects/<subject>/log.md) is rewritten by
      .claude/hooks/obsidian-live.py while Claude streams. Obsidian keeps the
      scroll position on reload, so the learner had to keep scrolling down. A
      log view that was at the bottom now glides to the new bottom; one the
      learner scrolled up in is left alone, with a "New messages" pill.

   2. Code runner. A side pane with an editor, stdin, and Run, like the CS 124
      playground or Programiz, running Java, Python, or C++ on this machine.
      "Send to tutor" writes .claude/obsidian-live/runner/shared.json, which
      the hook hands to Claude with the learner's next terminal message.
      Fenced code blocks in Reading view get a "Run" button that opens them here.

   3. Theme. A subject's record, plan, resume, and session notes wear the
      background its log and progress page do. Those two carry the theme in
      their cssclasses; hand-written notes carry none, so the plugin puts the
      same classes on the pane showing one (.obsidian/snippets/learning-notes.css). */

const obsidian = require("obsidian");
const { Plugin, ItemView, MarkdownView, Notice, Scope } = obsidian;
const childProcess = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const RUNNER_VIEW = "learn-code-runner";
const LIVE_FILE = /^(learn\/subjects\/[^/]+\/(log|codex-log)\.md|Claude outputs\/Current conversation\.md)$/;
const SUBJECT_NOTE = /^learn\/subjects\/([^/]+)\//;
const THEME_CLASS = /^lv-theme-[a-z][a-z0-9-]*$/;
const AT_BOTTOM_PX = 140;          // this close to the bottom still counts as following
const USER_INPUT_MS = 800;         // scrolls this soon after wheel/key/touch are the learner's
const OUTPUT_LIMIT = 64 * 1024;    // per stream, so a runaway print cannot freeze the pane
const EXTRA_PATH = ["/opt/homebrew/bin", "/usr/local/bin"];  // a Dock-launched app gets a bare PATH

// Errors and run steps go to .claude/obsidian-live/runner/learn-live.log, so a
// failure inside Obsidian can be read from disk instead of the dev console.
let LOG_FILE = null;
function log(message, error) {
  const line = new Date().toISOString() + " " + message +
    (error ? " :: " + (error.stack || error.message || String(error)) : "") + "\n";
  if (error) console.error("Learn live:", message, error);
  if (!LOG_FILE) return;
  try {
    if (fs.existsSync(LOG_FILE) && fs.statSync(LOG_FILE).size > 200 * 1024) fs.writeFileSync(LOG_FILE, "");
    fs.appendFileSync(LOG_FILE, line);
  } catch (ignored) { /* logging must never break a run */ }
}

const DEFAULTS = { follow: true, language: "java", timeLimitSeconds: 10, drafts: {} };

const LANGUAGES = {
  java: {
    label: "Java", aliases: ["java"],
    starter: 'void main() {\n    System.out.println("Hello from Java");\n}\n',
  },
  python: {
    label: "Python", aliases: ["python", "py", "python3"],
    starter: 'print("Hello from Python")\n',
  },
  cpp: {
    label: "C++", aliases: ["cpp", "c++", "cc", "cxx"],
    starter: '#include <iostream>\n\nint main() {\n    std::cout << "Hello from C++" << std::endl;\n}\n',
  },
};

function languageFor(name) {
  const wanted = String(name || "").toLowerCase();
  return Object.keys(LANGUAGES).find((key) => LANGUAGES[key].aliases.includes(wanted)) || null;
}

/* ------------------------------------------------------------ Java snippets

   CS 124 code is often loose statements, with or without classes and methods
   around them. JDK 25 runs a "compact source file" (`void main() { ... }` plus
   top-level methods and classes) directly, so loose statements are moved into
   `void main()` and everything else is kept as written. */

function topLevelItems(code) {
  const items = [];
  let depth = 0, start = 0, i = 0;
  const n = code.length;
  while (i < n) {
    const c = code[i], d = code[i + 1];
    if (c === "/" && d === "/") { const e = code.indexOf("\n", i); i = e < 0 ? n : e; continue; }
    if (c === "/" && d === "*") { const e = code.indexOf("*/", i + 2); i = e < 0 ? n : e + 2; continue; }
    if (code.startsWith('"""', i)) { const e = code.indexOf('"""', i + 3); i = e < 0 ? n : e + 3; continue; }
    if (c === '"' || c === "'") {
      i++;
      while (i < n && code[i] !== c && code[i] !== "\n") i += code[i] === "\\" ? 2 : 1;
      i++;
      continue;
    }
    if (c === "{" || c === "(" || c === "[") depth++;
    else if (c === "}" || c === ")" || c === "]") {
      depth--;
      // A block ends an item unless the statement goes on: `};`, `} else`, `}).run()`.
      if (depth === 0 && c === "}" && !/^\s*(;|\)|,|\.|else\b|catch\b|finally\b|while\b)/.test(code.slice(i + 1))) {
        items.push(code.slice(start, i + 1));
        start = i + 1;
      }
    } else if (c === ";" && depth === 0) {
      items.push(code.slice(start, i + 1));
      start = i + 1;
    }
    i++;
  }
  items.push(code.slice(start));
  return items.map((item) => item.trim()).filter(Boolean);
}

const LEADING_COMMENTS = /^(\s*(\/\/[^\n]*|\/\*[\s\S]*?\*\/))*\s*/;
const TYPE_DECL = /^(@\w+(\([^)]*\))?\s*)*((public|private|protected|static|final|abstract|sealed|non-sealed|strictfp)\s+)*(class|interface|enum|record|@interface)\s+[A-Za-z_$]/;
const METHOD_DECL = /^(@\w+(\([^)]*\))?\s*)*((public|private|protected|static|final|abstract|synchronized|default)\s+)*(<[^>]*>\s*)?(?<type>[\w$.]+(\s*<[^;{}()]*>)?(\s*\[\s*\])*)\s+(?<name>[A-Za-z_$][\w$]*)\s*\(/;
const NOT_A_NAME = new Set(["if", "for", "while", "switch", "catch", "synchronized", "return", "new",
                            "else", "do", "try", "throw", "case", "yield", "assert"]);

function classify(item) {
  const text = item.replace(LEADING_COMMENTS, "");
  if (/^import\s/.test(text)) return "import";
  if (/^package\s/.test(text)) return "package";
  if (TYPE_DECL.test(text)) return "type";
  const method = METHOD_DECL.exec(text);
  if (method && text.endsWith("}") && !NOT_A_NAME.has(method.groups.name) && !NOT_A_NAME.has(method.groups.type)) {
    return "method";
  }
  return "statement";
}

function prepareJava(code) {
  const items = topLevelItems(code);
  const kinds = items.map(classify);
  const compactMain = items.some((item, k) => kinds[k] === "method" &&
    /\bmain\s*\(/.test(item.replace(LEADING_COMMENTS, "").split("{")[0]));
  const classMain = items.find((item, k) => kinds[k] === "type" && /\bstatic\s+void\s+main\s*\(/.test(item));
  const statements = items.filter((_, k) => kinds[k] === "statement");
  if (!statements.length || compactMain || classMain) {
    // Written as a program already. A class with main must name the file.
    const named = !compactMain && classMain && /\b(class|record|enum|interface)\s+([A-Za-z_$][\w$]*)/.exec(classMain);
    return { fileName: (named ? named[2] : "Main") + ".java", source: code, wrapped: false };
  }
  const imports = items.filter((_, k) => kinds[k] === "import");
  const declarations = items.filter((_, k) => kinds[k] === "type" || kinds[k] === "method");
  const body = statements.map((s) => s.split("\n").map((line) => "    " + line).join("\n")).join("\n");
  const parts = [];
  if (imports.length) parts.push(imports.join("\n"));
  if (declarations.length) parts.push(declarations.join("\n\n"));
  parts.push("void main() {\n" + body + "\n}");
  return { fileName: "Main.java", source: parts.join("\n\n") + "\n", wrapped: true };
}

/* ------------------------------------------------------------ formatting

   Lesson code is written to be read in a chat: 2-space indents and one-line
   methods like `void speak() { System.out.println("pet"); }`. formatCode lays
   it out the way an editor would: one statement per line, 4-space indents, a
   block's body on lines of its own. Array initializers and anything inside
   parentheses (a lambda passed to a call) are left as written. Only
   whitespace changes, so the program means the same thing. */

function formatCode(language, code) {
  if (language === "python") return reindentPython(code);
  return reindentBraces(splitBraces(code));
}

// Copies a comment, string, char, or text block starting at i; returns its end.
function skipLiteral(code, i) {
  const c = code[i], d = code[i + 1], n = code.length;
  if (c === "/" && d === "/") { const e = code.indexOf("\n", i); return e < 0 ? n : e; }
  if (c === "/" && d === "*") { const e = code.indexOf("*/", i + 2); return e < 0 ? n : e + 2; }
  if (code.startsWith('"""', i)) { const e = code.indexOf('"""', i + 3); return e < 0 ? n : e + 3; }
  if (c === '"' || c === "'") {
    let k = i + 1;
    while (k < n && code[k] !== c && code[k] !== "\n") k += code[k] === "\\" ? 2 : 1;
    return Math.min(n, k + 1);
  }
  return i;
}

function splitBraces(code) {
  let out = "", i = 0, parens = 0;
  const blocks = [];   // per open brace: true for a block, false for an initializer
  const n = code.length;
  const restOfLine = (k) => { const e = code.indexOf("\n", k); return code.slice(k, e < 0 ? n : e); };
  const breakAfter = (k) => {   // end the line at k unless only a comment or nothing follows
    const rest = restOfLine(k);
    if (!rest.trim() || /^\s*\/[/*]/.test(rest)) return k;
    out = out.replace(/[ \t]+$/, "") + "\n";
    return k + rest.length - rest.trimStart().length;
  };
  const inBlock = () => !blocks.length || blocks[blocks.length - 1];
  while (i < n) {
    if ((i === 0 || code[i - 1] === "\n") && /^[ \t]*#/.test(restOfLine(i))) {   // C++ preprocessor line
      const line = restOfLine(i); out += line; i += line.length; continue;
    }
    const end = skipLiteral(code, i);
    if (end > i) { out += code.slice(i, end); i = end; continue; }
    const c = code[i];
    out += c; i++;
    if (c === "(" || c === "[") parens++;
    else if (c === ")" || c === "]") parens = Math.max(0, parens - 1);
    else if (c === "{") {
      const before = out.slice(0, -1).trimEnd().slice(-1);
      const block = inBlock() && parens === 0 && !/[=,(\[{\]]/.test(before);
      blocks.push(block);
      if (block) i = breakAfter(i);
    } else if (c === "}") {
      const block = blocks.length ? blocks.pop() : true;
      if (!block) continue;
      const line = out.slice(out.lastIndexOf("\n") + 1, -1);
      if (/\S/.test(line)) out = out.slice(0, -1).replace(/[ \t]+$/, "") + "\n}";
      if (!/^\s*(;|,|\)|else\b|catch\b|finally\b|while\b)/.test(restOfLine(i))) i = breakAfter(i);
    } else if (c === ";" && parens === 0 && inBlock()) {
      i = breakAfter(i);
    }
  }
  return out;
}

function reindentBraces(code) {
  const stack = [];   // per open brace: "switch" or "block"
  let parens = 0, comment = false, textBlock = false;
  const lines = [];
  for (const raw of code.split("\n")) {
    const text = raw.trim();
    if (textBlock) lines.push(raw);
    else if (!text) lines.push("");
    else if (comment) lines.push("    ".repeat(stack.length) + (text.startsWith("*") ? " " : "") + text);
    else if (text.startsWith("#")) lines.push(text);
    else {
      const closers = /^[})\]]*/.exec(text)[0];
      const braces = (closers.match(/}/g) || []).length;
      const open = stack.slice(0, stack.length - braces);
      let level = open.length;
      if (open[open.length - 1] === "switch" && !/^(case\b|default\b|})/.test(text)) level++;
      if (parens - (closers.length - braces) > 0) level += 2;
      lines.push("    ".repeat(level) + text);
    }
    // Carry brace, paren, comment, and text-block state to the next line.
    for (let k = 0; k < raw.length; k++) {
      if (textBlock) { const e = raw.indexOf('"""', k); if (e < 0) break; textBlock = false; k = e + 2; continue; }
      if (comment) { const e = raw.indexOf("*/", k); if (e < 0) break; comment = false; k = e + 1; continue; }
      if (raw.startsWith('"""', k)) { textBlock = true; k += 2; continue; }
      if (raw.startsWith("/*", k)) { comment = true; k++; continue; }
      if (raw.startsWith("//", k)) break;
      const end = skipLiteral(raw, k);
      if (end > k) { k = end - 1; continue; }
      const c = raw[k];
      if (c === "{") stack.push(/\bswitch\b/.test(raw.slice(0, k)) ? "switch" : "block");
      else if (c === "}") stack.pop();
      else if (c === "(" || c === "[") parens++;
      else if (c === ")" || c === "]") parens = Math.max(0, parens - 1);
    }
  }
  return lines.join("\n").replace(/\n+$/, "") + "\n";
}

function reindentPython(code) {
  const lines = code.replace(/\t/g, "    ").split("\n");
  const width = (line) => /^ */.exec(line)[0].length;
  const filled = lines.filter((line) => line.trim());
  if (!filled.length) return code;
  const margin = Math.min(...filled.map(width));
  const gcd = (a, b) => (b ? gcd(b, a % b) : a);
  const unit = filled.map((line) => width(line) - margin).filter(Boolean).reduce(gcd, 0);
  const scale = unit > 1 ? 4 / unit : 1;   // odd steps are left alone
  return lines.map((line) => (line.trim() ? " ".repeat((width(line) - margin) * scale) + line.trimStart() : ""))
    .join("\n").replace(/\n+$/, "") + "\n";
}

/* ------------------------------------------------------------ running */

function runStep(command, args, cwd, input, limitMs) {
  return new Promise((resolve) => {
    const env = Object.assign({}, process.env, {
      PATH: EXTRA_PATH.concat((process.env.PATH || "/usr/bin:/bin").split(":")).join(":"),
    });
    let stdout = "", stderr = "", timedOut = false, settled = false;
    let child;
    const finish = (result) => { if (!settled) { settled = true; clearTimeout(timer); resolve(result); } };
    try {
      child = childProcess.spawn(command, args, { cwd, env });
    } catch (error) {
      resolve({ code: null, stdout, stderr: String(error.message || error), timedOut, missing: true });
      return;
    }
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGKILL");
      // "close" waits for every pipe to shut, which a grandchild can hold open.
      // The run must end anyway, or the pane would stay in "Running..." for good.
      setTimeout(() => finish({ code: null, stdout, stderr, timedOut, missing: false }), 1000);
    }, limitMs);
    const cut = { stdout: false, stderr: false };
    const take = (name, sofar, chunk) => {
      if (cut[name]) return sofar;
      const joined = sofar + chunk;
      if (joined.length <= OUTPUT_LIMIT) return joined;
      cut[name] = true;
      return joined.slice(0, OUTPUT_LIMIT) + "\n[output cut]";
    };
    child.stdout.on("data", (chunk) => { stdout = take("stdout", stdout, chunk.toString()); });
    child.stderr.on("data", (chunk) => { stderr = take("stderr", stderr, chunk.toString()); });
    child.on("error", (error) => finish({ code: null, stdout, stderr: String(error.message || error),
                                          timedOut, missing: error.code === "ENOENT" }));
    child.on("close", (code) => finish({ code, stdout, stderr, timedOut, missing: false }));
    child.stdin.on("error", () => {});   // the program may exit without reading stdin
    if (input) child.stdin.write(input);
    child.stdin.end();
  });
}

const INSTALL_HINT = {
  java: "Java was not found. Install a JDK (for example Temurin 25 from adoptium.net).",
  python: "python3 was not found. Install Python from python.org or Homebrew.",
  cpp: "clang++ was not found. Run `xcode-select --install` in a terminal.",
};

async function runCode(language, code, input, limitSeconds) {
  const started = Date.now();
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "learn-live-"));
  const limit = Math.max(1, limitSeconds) * 1000;
  let steps, note = "";
  if (language === "java") {
    const prepared = prepareJava(code);
    fs.writeFileSync(path.join(dir, prepared.fileName), prepared.source);
    steps = [["java", [prepared.fileName]]];
    if (prepared.wrapped) note = "Loose statements were run inside void main(), so error line numbers may be shifted.";
  } else if (language === "python") {
    fs.writeFileSync(path.join(dir, "main.py"), code);
    steps = [["python3", ["-u", "main.py"]]];
  } else {
    fs.writeFileSync(path.join(dir, "main.cpp"), code);
    steps = [["clang++", ["-std=c++20", "-o", "main", "main.cpp"]], [path.join(dir, "main"), []]];
  }
  let result = { code: null, stdout: "", stderr: "", timedOut: false };
  for (let k = 0; k < steps.length; k++) {
    const last = k === steps.length - 1;
    log("step " + steps[k][0] + " " + steps[k][1].join(" ") + " in " + dir);
    result = await runStep(steps[k][0], steps[k][1], dir, last ? input : "", limit);
    log("step ended code=" + result.code + " timedOut=" + result.timedOut + " missing=" + Boolean(result.missing) +
        (result.stderr ? " stderr=" + JSON.stringify(result.stderr.slice(0, 300)) : ""));
    if (result.missing) { result.stderr = INSTALL_HINT[language] + "\n" + result.stderr; break; }
    if (result.timedOut || result.code !== 0) break;
  }
  fs.rm(dir, { recursive: true, force: true }, () => {});
  return { language, code, stdin: input, stdout: result.stdout, stderr: result.stderr,
           exit_code: result.code, timed_out: result.timedOut, ms: Date.now() - started,
           ran_at: new Date().toISOString(), note };
}

/* ------------------------------------------------------------ editor */

const KEYWORDS = {
  java: "abstract assert boolean break byte case catch char class const continue default do double else enum extends final finally float for goto if implements import instanceof int interface long native new package private protected public record return sealed short static strictfp super switch synchronized this throw throws transient try var void volatile while yield permits non-sealed",
  python: "and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield match case",
  cpp: "auto bool break case catch char class const constexpr continue default delete do double else enum explicit extern float for friend goto if inline int long mutable namespace new noexcept operator private protected public return short signed sizeof static struct switch template this throw try typedef typename union unsigned using virtual void volatile while nullptr",
};
const ATOMS = new Set(["true", "false", "null", "True", "False", "None", "nullptr", "NULL"]);

function streamMode(language) {
  const keywords = new Set(KEYWORDS[language].split(" "));
  const python = language === "python";
  return {
    name: language,
    startState: () => ({ comment: false, depth: 0 }),
    copyState: (state) => ({ comment: state.comment, depth: state.depth }),
    token(stream, state) {
      if (state.comment) {
        if (stream.skipTo("*/")) { stream.pos += 2; state.comment = false; } else stream.skipToEnd();
        return "comment";
      }
      if (stream.eatSpace()) return null;
      const ch = stream.peek();
      if (python ? ch === "#" : stream.match("//", false)) { stream.skipToEnd(); return "comment"; }
      if (!python && stream.match("/*")) { state.comment = true; return "comment"; }
      if (language === "cpp" && ch === "#") { stream.skipToEnd(); return "meta"; }
      if (ch === '"' || ch === "'") {
        stream.next();
        let escaped = false, next;
        while ((next = stream.next()) != null) {
          if (next === ch && !escaped) break;
          escaped = !escaped && next === "\\";
        }
        return "string";
      }
      if (/\d/.test(ch)) { stream.match(/^(0x[\da-f_]+|[\d_]*\.?[\d_]+(e[+-]?\d+)?)[lfd]?/i); return "number"; }
      if (ch === "@") { stream.next(); stream.eatWhile(/[\w$]/); return "meta"; }
      if (/[A-Za-z_$]/.test(ch)) {
        stream.eatWhile(/[\w$]/);
        const word = stream.current();
        if (keywords.has(word)) return "keyword";
        if (ATOMS.has(word)) return "atom";
        if (/^[A-Z]/.test(word)) return "typeName";
        if (stream.match(/^\s*\(/, false)) return "def";
        return "variableName";
      }
      stream.next();
      if (ch === "{") state.depth++;
      if (ch === "}") state.depth = Math.max(0, state.depth - 1);
      return /[+\-*/%=<>!&|^~?:]/.test(ch) ? "operator" : null;
    },
    indent(state, textAfter, context) {
      if (python) return null;   // null keeps the previous line's indent
      return Math.max(0, state.depth - (/^\s*\}/.test(textAfter) ? 1 : 0)) * context.unit;
    },
    languageData: {
      commentTokens: python ? { line: "#" } : { line: "//", block: { open: "/*", close: "*/" } },
      indentOnInput: /^\s*\}$/,
    },
  };
}

/* Colours come from the parse tree, not from @lezer/highlight. Obsidian 1.14
   hands plugins a different copy of @lezer/highlight from the one its
   @codemirror/language tags nodes with, so classHighlighter matched nothing
   and the runner was all black (seen 2026-10-13). The stream parser names
   each node after the token streamMode returned, so marking nodes by name
   needs no tags at all. */
function tokenColours(view, state, lang) {
  const marks = {};
  const markFor = (name) => marks[name] || (marks[name] = view.Decoration.mark({ class: "lv-tok-" + name }));
  const build = (editor) => {
    const builder = new state.RangeSetBuilder();
    const tree = lang.syntaxTree(editor.state);
    for (const { from, to } of editor.visibleRanges) {
      tree.iterate({ from, to, enter: (node) => {
        if (node.name !== "Document" && node.to > node.from) builder.add(node.from, node.to, markFor(node.name));
      } });
    }
    return builder.finish();
  };
  return view.ViewPlugin.fromClass(class {
    constructor(editor) { this.decorations = build(editor); }
    update(update) {
      if (update.docChanged || update.viewportChanged ||
          lang.syntaxTree(update.state) !== lang.syntaxTree(update.startState)) this.decorations = build(update.view);
    }
  }, { decorations: (plugin) => plugin.decorations });
}

function buildEditor(parent, doc, language, onChange, onRun, onFormat) {
  try {
    const view = require("@codemirror/view");
    const state = require("@codemirror/state");
    const commands = require("@codemirror/commands");
    const lang = require("@codemirror/language");
    let brackets = [], bracketKeys = [];
    try {
      const auto = require("@codemirror/autocomplete");
      brackets = auto.closeBrackets(); bracketKeys = auto.closeBracketsKeymap;
    } catch (error) { /* closing brackets are a nicety */ }
    const languageSlot = new state.Compartment();
    let current = language;
    const currentLanguage = () => current;
    const modeFor = (name) => lang.StreamLanguage.define(streamMode(name));
    const editor = new view.EditorView({
      parent,
      state: state.EditorState.create({
        doc,
        extensions: [
          view.lineNumbers(), view.highlightActiveLineGutter(), view.highlightActiveLine(),
          view.drawSelection(), commands.history(), lang.indentOnInput(), lang.bracketMatching(), brackets,
          tokenColours(view, state, lang), languageSlot.of(modeFor(language)),
          state.EditorState.tabSize.of(4), lang.indentUnit.of("    "),
          // Code pasted from a lesson comes in 2-space, one-line-method style.
          // Several lines are re-laid out; a single line is pasted as is.
          view.EditorView.domEventHandlers({ paste(event, editor) {
            const text = event.clipboardData && event.clipboardData.getData("text/plain");
            if (!text || !text.includes("\n")) return false;
            const { from } = editor.state.selection.main;
            const line = editor.state.doc.lineAt(from);
            const before = line.text.slice(0, from - line.from);
            const base = /^\s*$/.test(before) ? before : "";
            const lines = formatCode(currentLanguage(), text).replace(/\n$/, "").split("\n");
            const placed = lines.map((l, k) => (k && l ? base + l : l)).join("\n");
            event.preventDefault();
            editor.dispatch(editor.state.replaceSelection(placed));
            return true;
          } }),
          view.keymap.of([{ key: "Mod-Enter", run: () => { onRun(); return true; } },
                          { key: "Shift-Alt-f", run: () => { onFormat(); return true; } },
                          ...bracketKeys, ...commands.defaultKeymap, ...commands.historyKeymap,
                          commands.indentWithTab]),
          view.EditorView.updateListener.of((update) => { if (update.docChanged) onChange(update.state.doc.toString()); }),
        ],
      }),
    });
    return {
      get: () => editor.state.doc.toString(),
      // A dispatch, not a new state, so Cmd+Z brings back what was replaced.
      set: (text) => editor.dispatch({ changes: { from: 0, to: editor.state.doc.length, insert: text } }),
      setLanguage: (name) => { current = name; editor.dispatch({ effects: languageSlot.reconfigure(modeFor(name)) }); },
      focus: () => editor.focus(),
      destroy: () => editor.destroy(),
    };
  } catch (error) {
    console.warn("Learn live: CodeMirror unavailable, using a plain text box", error);
    const area = parent.createEl("textarea", { cls: "learn-runner-plain" });
    area.value = doc;
    area.spellcheck = false;
    area.addEventListener("input", () => onChange(area.value));
    area.addEventListener("keydown", (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") { event.preventDefault(); onRun(); }
      if (event.key === "Tab") { event.preventDefault(); area.setRangeText("    ", area.selectionStart, area.selectionEnd, "end"); onChange(area.value); }
    });
    return { get: () => area.value, set: (text) => { area.value = text; onChange(text); },
             setLanguage: () => {}, focus: () => area.focus(), destroy: () => area.remove() };
  }
}

/* ------------------------------------------------------------ runner pane */

class RunnerView extends ItemView {
  constructor(leaf, plugin) {
    super(leaf);
    this.plugin = plugin;
    this.language = LANGUAGES[plugin.settings.language] ? plugin.settings.language : "java";
    this.running = false;
    this.scope = new Scope(this.app.scope);
    this.scope.register(["Mod"], "Enter", () => { this.runEditor(); return false; });
  }

  getViewType() { return RUNNER_VIEW; }
  getDisplayText() { return "Code runner"; }
  getIcon() { return "square-terminal"; }

  async onOpen() {
    const root = this.contentEl;
    root.empty();
    root.addClass("learn-runner");
    const bar = root.createDiv({ cls: "learn-runner-bar" });
    this.picker = bar.createEl("select", { cls: "dropdown" });
    for (const key of Object.keys(LANGUAGES)) this.picker.createEl("option", { value: key, text: LANGUAGES[key].label });
    this.picker.value = this.language;
    this.picker.addEventListener("change", () => this.switchLanguage(this.picker.value));
    this.runButton = bar.createEl("button", { cls: "mod-cta", text: "Run", attr: { "aria-label": "Run (Cmd+Enter)" } });
    this.runButton.addEventListener("click", () => this.runEditor());
    this.sendButton = bar.createEl("button", { text: "Send to tutor",
      attr: { "aria-label": "Run, then hand the code and output to Claude with your next terminal message" } });
    this.sendButton.addEventListener("click", () => this.runEditor(true));
    const format = bar.createEl("button", { cls: "clickable-icon", text: "Format", attr: { "aria-label": "4-space indents, one statement per line (Shift+Alt+F; Cmd+Z undoes)" } });
    format.addEventListener("click", () => this.formatEditor());
    const reset = bar.createEl("button", { cls: "clickable-icon", text: "Reset", attr: { "aria-label": "Replace with the starter program (Cmd+Z undoes)" } });
    reset.addEventListener("click", () => this.editor.set(LANGUAGES[this.language].starter));
    this.target = root.createDiv({ cls: "learn-runner-target" });
    this.showTarget();

    this.editorHost = root.createDiv({ cls: "learn-runner-editor" });
    this.editor = buildEditor(this.editorHost, this.plugin.draftFor(this.language), this.language,
                              (text) => this.plugin.saveDraft(this.language, text), () => this.runEditor(),
                              () => this.formatEditor());

    const input = root.createEl("details", { cls: "learn-runner-stdin" });
    input.createEl("summary", { text: "Input (stdin)" });
    this.stdin = input.createEl("textarea", { attr: { placeholder: "Typed input for Scanner / input() / cin, one value per line", rows: "3" } });

    // Capture phase on the pane itself, so neither Obsidian's hotkeys nor the
    // editor's own Enter handling can take Cmd+Enter first.
    this.registerDomEvent(root, "keydown", (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
        event.preventDefault();
        event.stopPropagation();
        this.runEditor();
      }
    }, { capture: true });

    const output = root.createDiv({ cls: "learn-runner-output" });
    this.status = output.createDiv({ cls: "learn-runner-status", text: "Cmd+Enter runs. Nothing leaves this computer unless you press Send to tutor." });
    this.out = output.createEl("pre", { cls: "learn-runner-out" });
  }

  async onClose() { if (this.editor) this.editor.destroy(); }

  switchLanguage(language) {
    this.language = language;
    this.picker.value = language;
    this.plugin.settings.language = language;
    this.plugin.saveSettings();
    this.editor.setLanguage(language);
    this.editor.set(this.plugin.draftFor(language));
  }

  loadCode(language, code) {
    log("load " + language + " (" + code.length + " chars)");
    if (language !== this.language) this.switchLanguage(language);
    this.editor.set(formatCode(language, code));
    this.editor.focus();
    this.status.setText("Loaded from the note. Edit it, then Cmd+Enter. Cmd+Z brings back what was here.");
    this.out.empty();
  }

  formatEditor() {
    const text = this.editor.get();
    const formatted = formatCode(this.language, text);
    if (formatted !== text) this.editor.set(formatted);
  }

  // Which lesson Send goes to: the hook gives the code only to the
  // conversation teaching this subject.
  showTarget() {
    if (!this.target) return;
    const subject = this.plugin.lastSubject;
    this.target.setText(subject ? "Send to tutor goes to the " + subject + " lesson."
                                : "Send to tutor goes to whichever Claude chat you message next.");
  }

  async runEditor(share = false) {
    log("run requested (share=" + share + ", running=" + this.running + ", language=" + this.language + ")");
    if (this.running) return;
    this.running = true;
    this.runButton.disabled = this.sendButton.disabled = true;
    this.status.setText("Running...");
    this.out.empty();
    try {
      const result = await runCode(this.language, this.editor.get(), this.stdin.value, this.plugin.settings.timeLimitSeconds);
      this.showResult(result);
      if (share) {
        const subject = this.plugin.shareResult(result);
        const where = subject ? "the " + subject + " lesson" : "your next Claude chat";
        this.status.appendText(" · Sent to " + where + ". It arrives with your next message there.");
        new Notice("Code sent to " + where + ". Send any message there (for example \"check my code\") and Claude gets it with that message.");
      }
    } catch (error) {
      log("run failed", error);
      this.status.setText("Could not run: " + (error.message || error));
    } finally {
      this.running = false;
      this.runButton.disabled = this.sendButton.disabled = false;
    }
  }

  showResult(result) {
    const seconds = (result.ms / 1000).toFixed(2) + " s";
    const verdict = result.timed_out ? "Stopped after " + this.plugin.settings.timeLimitSeconds + " s (time limit)"
      : result.exit_code === 0 ? "Finished in " + seconds : "Exit code " + result.exit_code + " after " + seconds;
    this.status.setText(verdict + (result.note ? " · " + result.note : ""));
    this.status.toggleClass("is-error", result.exit_code !== 0 || result.timed_out);
    if (result.stdout) this.out.createSpan({ text: result.stdout });
    if (result.stderr) this.out.createSpan({ cls: "learn-runner-stderr", text: result.stderr });
    if (!result.stdout && !result.stderr) this.out.createSpan({ cls: "learn-runner-quiet", text: "(no output)" });
  }
}

/* ------------------------------------------------------------ theme */

// The theme class for the pane showing `notePath`, or null for none.
// `classesOf(path)` is that note's frontmatter cssclasses. A note that names a
// theme itself (a log, a progress page) is left alone; the rest of a subject's
// folder borrows its progress page's theme, which learn-status.py rewrites at
// every session start, or else its log's.
function paneTheme(notePath, classesOf) {
  const match = SUBJECT_NOTE.exec(notePath || "");
  if (!match) return null;
  const themeIn = (path) => classesOf(path).find((name) => THEME_CLASS.test(name));
  if (themeIn(notePath)) return null;
  const folder = "learn/subjects/" + match[1] + "/";
  return themeIn(folder + "progress.md") || themeIn(folder + "log.md") || "lv-theme-calm";
}

/* ------------------------------------------------------------ plugin */

class LearnLivePlugin extends Plugin {
  async onload() {
    try {
      const folder = path.join(this.app.vault.adapter.getBasePath(), ".claude", "obsidian-live", "runner");
      fs.mkdirSync(folder, { recursive: true });
      LOG_FILE = path.join(folder, "learn-live.log");
    } catch (error) { console.error("Learn live: no log file", error); }
    log("loaded");
    const caught = (error) => { if (error && String(error.stack || "").includes("learn-live")) log("uncaught", error); };
    this.registerDomEvent(window, "error", (event) => caught(event.error));
    this.registerDomEvent(window, "unhandledrejection", (event) => caught(event.reason));
    this.settings = Object.assign({}, DEFAULTS, await this.loadData());
    this.settings.drafts = Object.assign({}, this.settings.drafts);
    this.views = new WeakMap();   // MarkdownView -> follow state
    this.timers = new Map();

    this.registerView(RUNNER_VIEW, (leaf) => new RunnerView(leaf, this));
    this.addRibbonIcon("square-terminal", "Open code runner", () => this.openRunner());
    this.addCommand({ id: "open-code-runner", name: "Open code runner", callback: () => this.openRunner() });
    this.addCommand({ id: "toggle-follow", name: "Toggle following live chat logs", callback: () => this.setFollow(!this.settings.follow) });
    this.addCommand({ id: "jump-to-latest", name: "Jump to the latest message", callback: () => this.jumpActive() });

    this.followItem = this.addStatusBarItem();
    this.followItem.addClass("mod-clickable", "learn-follow-status");
    this.followItem.addEventListener("click", () => this.setFollow(!this.settings.follow));
    this.renderFollowItem();

    this.registerEvent(this.app.vault.on("modify", (file) => { if (LIVE_FILE.test(file.path)) this.onLogChanged(file); }));
    this.registerEvent(this.app.workspace.on("layout-change", () => this.watchLogs()));
    this.registerEvent(this.app.workspace.on("file-open", (file) => { this.noteSubject(file); this.watchLogs(); }));
    this.app.workspace.onLayoutReady(() => this.watchLogs());

    this.registerEvent(this.app.workspace.on("layout-change", () => this.themePanes()));
    this.registerEvent(this.app.workspace.on("file-open", () => this.themePanes()));
    this.registerEvent(this.app.metadataCache.on("changed", () => this.themePanes()));
    this.registerEvent(this.app.metadataCache.on("resolved", () => this.themePanes()));
    this.app.workspace.onLayoutReady(() => this.themePanes());

    this.lastSubject = null;
    this.app.workspace.onLayoutReady(() => this.noteSubject(this.app.workspace.getActiveFile()));
    this.registerMarkdownPostProcessor((element, context) => this.addRunButtons(element, context));
  }

  onunload() {
    for (const timer of this.timers.values()) clearTimeout(timer);
    // A pill outlives the plugin otherwise, and its click goes to the old copy.
    for (const view of this.logViews()) {
      view.contentEl.querySelectorAll(".learn-follow-pill").forEach((pill) => pill.remove());
    }
    for (const leaf of this.app.workspace.getLeavesOfType("markdown")) this.setPaneTheme(leaf.view.containerEl, null);
  }

  async saveSettings() { await this.saveData(this.settings); }

  /* ---- follow */

  setFollow(on) {
    this.settings.follow = on;
    this.saveSettings();
    this.renderFollowItem();
    if (on) this.logViews().forEach((view) => this.followAgain(view));
  }

  renderFollowItem() {
    this.followItem.setText(this.settings.follow ? "Live log: following" : "Live log: not following");
    this.followItem.setAttr("aria-label", "Click to " + (this.settings.follow ? "stop" : "start") + " scrolling live chat logs as Claude writes");
  }

  logViews() {
    return this.app.workspace.getLeavesOfType("markdown").map((leaf) => leaf.view)
      .filter((view) => view instanceof MarkdownView && view.file && LIVE_FILE.test(view.file.path));
  }

  scrollerOf(view) {
    // In Reading view the element that scrolls is .markdown-preview-view, one
    // level inside previewMode.containerEl (.markdown-reading-view). Scrolling
    // the outer one did nothing, which is why "New messages" did nothing.
    if (view.getMode() === "preview") {
      const container = view.previewMode.containerEl;
      return container.querySelector(".markdown-preview-view") || container;
    }
    return (view.editor && view.editor.cm && view.editor.cm.scrollDOM) || view.contentEl.querySelector(".cm-scroller");
  }

  watchLogs() { this.logViews().forEach((view) => this.watchView(view)); }

  watchView(view) {
    if (this.views.has(view)) return this.views.get(view);
    const follow = { following: true, unseen: false, userUntil: 0, pill: null };
    this.views.set(view, follow);
    const mark = () => { follow.userUntil = Date.now() + USER_INPUT_MS; };
    for (const name of ["wheel", "touchmove", "keydown", "pointerdown"]) {
      view.registerDomEvent(view.contentEl, name, mark, { passive: true, capture: true });
    }
    // Only a scroll the learner made changes follow mode. A re-render moving
    // the page, or this plugin's own glide, must not switch it off.
    view.registerDomEvent(view.contentEl, "scroll", (event) => {
      if (Date.now() > follow.userUntil || !(event.target instanceof HTMLElement)) return;
      const target = event.target;
      follow.following = target.scrollHeight - target.scrollTop - target.clientHeight < AT_BOTTOM_PX;
      if (follow.following) follow.unseen = false;
      this.renderPill(view, follow);
    }, { capture: true, passive: true });
    return follow;
  }

  onLogChanged(file) {
    for (const view of this.logViews()) {
      if (view.file.path !== file.path) continue;
      const follow = this.watchView(view);
      if (this.settings.follow && follow.following) this.glide(view);
      else { follow.unseen = true; this.renderPill(view, follow); }
    }
  }

  glide(view) {
    clearTimeout(this.timers.get(view));
    // Reading view renders lazily, so the bottom moves once it is reached.
    // Smooth for the first step, then jump until it stops moving.
    const step = (round) => {
      const element = this.scrollerOf(view);
      if (!element) return;
      element.scrollTo({ top: element.scrollHeight, behavior: round === 0 ? "smooth" : "auto" });
      this.timers.set(view, setTimeout(() => {
        if (round < 6 && element.scrollHeight - element.scrollTop - element.clientHeight > 4) step(round + 1);
      }, round === 0 ? 650 : 150));
    };
    this.timers.set(view, setTimeout(() => step(0), 120));
  }

  followAgain(view) {
    const follow = this.watchView(view);
    follow.following = true;
    follow.unseen = false;
    follow.userUntil = 0;   // the click on the pill is not a scroll away from the bottom
    this.renderPill(view, follow);
    this.glide(view);
  }

  jumpActive() {
    const view = this.app.workspace.getActiveViewOfType(MarkdownView);
    if (view && view.file && LIVE_FILE.test(view.file.path)) this.followAgain(view);
  }

  renderPill(view, follow) {
    const show = follow.unseen && !follow.following;
    if (!follow.pill && show) {
      view.contentEl.addClass("learn-follow-host");
      follow.pill = view.contentEl.createEl("button", { cls: "learn-follow-pill", text: "New messages ↓" });
      follow.pill.addEventListener("click", () => this.followAgain(view));
    }
    if (follow.pill) follow.pill.toggleClass("is-hidden", !show);
  }

  /* ---- theme */

  classesOf(notePath) {
    const file = this.app.vault.getAbstractFileByPath(notePath);
    const cache = file && this.app.metadataCache.getFileCache(file);
    const value = cache && cache.frontmatter && (cache.frontmatter.cssclasses || cache.frontmatter.cssclass);
    return [].concat(value || []).flatMap((name) => String(name).split(/[\s,]+/)).filter(Boolean);
  }

  themePanes() {
    for (const leaf of this.app.workspace.getLeavesOfType("markdown")) {
      const view = leaf.view;
      if (!(view instanceof MarkdownView)) continue;
      this.setPaneTheme(view.containerEl, view.file && paneTheme(view.file.path, (p) => this.classesOf(p)));
    }
  }

  setPaneTheme(element, theme) {
    const have = Array.from(element.classList).filter((name) => name === "learning-themed" || THEME_CLASS.test(name));
    const want = theme ? ["learning-themed", theme] : [];
    if (have.sort().join(" ") === want.sort().join(" ")) return;
    element.removeClass(...have);
    if (want.length) element.addClass(...want);
  }

  /* ---- runner */

  draftFor(language) { return this.settings.drafts[language] || LANGUAGES[language].starter; }

  saveDraft(language, text) {
    this.settings.drafts[language] = text;
    clearTimeout(this.timers.get("draft"));
    this.timers.set("draft", setTimeout(() => this.saveSettings(), 500));
  }

  async openRunner() {
    let leaf = this.app.workspace.getLeavesOfType(RUNNER_VIEW)[0];
    if (!leaf) {
      leaf = this.app.workspace.getRightLeaf(false);
      await leaf.setViewState({ type: RUNNER_VIEW, active: true });
    }
    await this.app.workspace.revealLeaf(leaf);
    if (leaf.loadIfDeferred) await leaf.loadIfDeferred();
    return leaf.view;
  }

  async openInRunner(language, code) {
    const view = await this.openRunner();
    if (view instanceof RunnerView) view.loadCode(language, code);
    else log("runner leaf holds " + (view && view.getViewType ? view.getViewType() : typeof view) + ", not the runner");
  }

  addRunButtons(element, context) {
    for (const code of element.querySelectorAll("pre > code")) {
      const tag = Array.from(code.classList).find((name) => name.startsWith("language-"));
      const language = tag && languageFor(tag.slice("language-".length));
      const pre = code.parentElement;
      if (!language || pre.querySelector(".learn-run-block")) continue;
      const button = pre.createEl("button", { cls: "learn-run-block",
        attr: { "aria-label": "Open in the code runner" } });
      obsidian.setIcon(button, "play");
      button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        log("run button clicked on a " + language + " block");
        this.noteSubject(context && this.app.vault.getAbstractFileByPath(context.sourcePath));
        this.openInRunner(language, code.textContent || "").catch((error) => {
          log("opening the runner failed", error);
          new Notice("Code runner: " + (error.message || error));
        });
      });
    }
  }

  shareResult(result) {
    const base = this.app.vault.adapter.getBasePath();
    const folder = path.join(base, ".claude", "obsidian-live", "runner");
    fs.mkdirSync(folder, { recursive: true });
    const share = Object.assign({ id: Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
                                  sent_at: new Date().toISOString() }, result);
    if (this.lastSubject) share.subject = this.lastSubject;
    const temporary = path.join(folder, ".shared.json.tmp");
    fs.writeFileSync(temporary, JSON.stringify(share));
    fs.renameSync(temporary, path.join(folder, "shared.json"));
    return share.subject || null;
  }

  // The subject of the learning note opened last (log, plan, session note).
  noteSubject(file) {
    const match = file && /^learn\/subjects\/([^/]+)\//.exec(file.path);
    if (!match || match[1] === this.lastSubject) return;
    this.lastSubject = match[1];
    for (const leaf of this.app.workspace.getLeavesOfType(RUNNER_VIEW)) {
      if (leaf.view instanceof RunnerView) leaf.view.showTarget();
    }
  }
}

module.exports = LearnLivePlugin;
module.exports.default = LearnLivePlugin;
module.exports.prepareJava = prepareJava;
module.exports.formatCode = formatCode;
module.exports.runCode = runCode;
module.exports.streamMode = streamMode;
module.exports.paneTheme = paneTheme;
module.exports.RunnerView = RunnerView;
