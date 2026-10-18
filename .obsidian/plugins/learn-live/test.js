// Checks for main.js outside Obsidian. Run: node .obsidian/plugins/learn-live/test.js
// The name-clash check needs Obsidian's typings: `npm i obsidian` in any folder,
// then OBSIDIAN_DTS=<that folder>/node_modules/obsidian/obsidian.d.ts. Without it, it is skipped.
// Why it exists: RunnerView once defined load(language, code), which replaced
// Component.load(); Obsidian calls that while opening a view, so the pane never built.
const Module = require("module");
const orig = Module._load;
Module._load = function (req, ...rest) {
  if (req === "obsidian") { class C {} return { Plugin: C, ItemView: C, MarkdownView: C, Notice: C, Scope: C, setIcon(){} }; }
  return orig.call(this, req, ...rest);
};
const plugin = require(require("path").join(__dirname, "main.js"));
const { prepareJava, runCode, formatCode, paneTheme, opensInReading } = plugin;
let fails = 0;
const eq = (label, got, want) => { const ok = JSON.stringify(got) === JSON.stringify(want); if (!ok) fails++; console.log((ok ? "  pass  " : "  FAIL  ") + label + (ok ? "" : "\n     got  " + JSON.stringify(got) + "\n     want " + JSON.stringify(want))); };

function clashCheck() {
  const fs = require("fs");
  const file = process.env.OBSIDIAN_DTS;
  if (!file || !fs.existsSync(file)) { console.log("  skip  name clash check (set OBSIDIAN_DTS)"); return; }
  const dts = fs.readFileSync(file, "utf8");
  function members(name) {
    const start = dts.search(new RegExp("export (abstract )?class " + name + "\\b"));
    if (start < 0) throw new Error("no class " + name);
    let depth = 0, i = dts.indexOf("{", start), text = "";
    for (; i < dts.length; i++) { const c = dts[i]; if (c === "{") depth++; if (c === "}") { depth--; if (!depth) break; } if (depth === 1) text += c; else if (depth === 2 && c === "\n") text += "\n"; }
    const names = new Set();
    for (const m of text.matchAll(/^\s*(?:abstract |static |readonly |protected )*([A-Za-z_$][\w$]*)\??\s*[(:<]/gm)) names.add(m[1]);
    const ext = new RegExp("export (abstract )?class " + name + "(<[^>]*>)? extends (\\w+)").exec(dts);
    if (ext) for (const n of members(ext[3])) names.add(n);
    return names;
  }
  const overrides = new Set(["onload", "onunload", "getViewType", "getDisplayText", "getIcon", "onOpen", "onClose"]);
  for (const [label, cls, base] of [["LearnLivePlugin", plugin, "Plugin"], ["RunnerView", plugin.RunnerView, "ItemView"]]) {
    const inherited = members(base);
    const clashes = Object.getOwnPropertyNames(cls.prototype).filter((n) => n !== "constructor" && inherited.has(n) && !overrides.has(n));
    eq(label + " shadows no " + base + " method", clashes, []);
  }
}
function formatChecks() {
  // The Quiz 7 probe as the tutor wrote it (2-space, one-line methods).
  eq("format: lesson Java gets 4-space indents and one statement per line",
     formatCode("java", 'class Pet {\n  void speak() { System.out.println("pet"); }\n}\nclass Point {\n  private int x;\n  Point(int setX) { x = setX; }\n}\nPoint a = new Point(3); Point b = a;\n'),
     'class Pet {\n    void speak() {\n        System.out.println("pet");\n    }\n}\nclass Point {\n    private int x;\n    Point(int setX) {\n        x = setX;\n    }\n}\nPoint a = new Point(3);\nPoint b = a;\n');
  eq("format: initializers, for headers, lambdas in calls, strings, and comments are left alone",
     formatCode("java", 'int[] a = {1, 2};\nint[][] g = new int[][] {{1}, {2}};\nfor (int i = 0; i < 2; i++) { sum += i; } // add\nlist.forEach(x -> { use(x); });\nString s = "{ ; }";\n'),
     'int[] a = {1, 2};\nint[][] g = new int[][] {{1}, {2}};\nfor (int i = 0; i < 2; i++) {\n    sum += i;\n} // add\nlist.forEach(x -> { use(x); });\nString s = "{ ; }";\n');
  eq("format: else, catch, and switch keep their shape",
     formatCode("java", 'if (a) { x(); } else { y(); }\ntry { z(); } catch (Exception e) { w(); }\nswitch (k) {\ncase 1:\nf();\nbreak;\ndefault:\ng();\n}\n'),
     'if (a) {\n    x();\n} else {\n    y();\n}\ntry {\n    z();\n} catch (Exception e) {\n    w();\n}\nswitch (k) {\n    case 1:\n        f();\n        break;\n    default:\n        g();\n}\n');
  eq("format: javadoc lines line up under the opener",
     formatCode("java", 'class A {\n/**\n* Doc.\n*/\nint f() { return 1; }\n}\n'),
     'class A {\n    /**\n     * Doc.\n     */\n    int f() {\n        return 1;\n    }\n}\n');
  eq("format: C++ keeps preprocessor lines and struct semicolons",
     formatCode("cpp", '#include <iostream>\nstruct S { int a; };\nint main() { std::cout << 1; }\n'),
     '#include <iostream>\nstruct S {\n    int a;\n};\nint main() {\n    std::cout << 1;\n}\n');
  eq("format: Python 2-space indents become 4, and a pasted margin is removed",
     formatCode("python", '  def f(x):\n    if x:\n      return 1\n    return 0\n'),
     'def f(x):\n    if x:\n        return 1\n    return 0\n');
  eq("format: formatting twice changes nothing",
     formatCode("java", formatCode("java", 'class A { int f() { return 1; } }\n')),
     formatCode("java", 'class A { int f() { return 1; } }\n'));
}

function themeChecks() {
  const classes = {
    "learn/subjects/q7/progress.md": ["learning-note", "learning-themed", "lv-theme-code"],
    "learn/subjects/q7/log.md": ["learning-log", "lv-theme-math"],
    "learn/subjects/new/log.md": ["learning-log", "lv-theme-design"],
  };
  const classesOf = (path) => classes[path] || [];
  eq("theme: a subject's hand-written notes take its progress page's theme",
     ["record.md", "plan.md", "resume.md", "sessions/2026-10-13-s01.md"].map((n) => paneTheme("learn/subjects/q7/" + n, classesOf)),
     ["lv-theme-code", "lv-theme-code", "lv-theme-code", "lv-theme-code"]);
  eq("theme: a note that names its own theme is left alone",
     [paneTheme("learn/subjects/q7/log.md", classesOf), paneTheme("learn/subjects/q7/progress.md", classesOf)], [null, null]);
  eq("theme: no progress page falls back to the log, then calm",
     [paneTheme("learn/subjects/new/record.md", classesOf), paneTheme("learn/subjects/none/record.md", classesOf)],
     ["lv-theme-design", "lv-theme-calm"]);
  eq("theme: notes outside a subject folder get none",
     [paneTheme("learn/Home.md", classesOf), paneTheme("learn/system/tutor.md", classesOf), paneTheme(null, classesOf)],
     [null, null, null]);
  eq("reading view: live logs and generated notes open in it, hand-written notes do not",
     [opensInReading("learn/subjects/q7/log.md", { type: "learning-chat-log" }),
      opensInReading("learn/subjects/q7/log.md", null),
      opensInReading("learn/Home.md", { type: "learning-home", generated: true }),
      opensInReading("learn/subjects/q7/progress.md", { type: "learning-progress" }),
      opensInReading("learn/subjects/q7/record.md", { type: "learning-record" }),
      opensInReading("learn/system/tutor.md", null)],
     [true, true, true, true, false, false]);
}

(async () => {
  clashCheck();
  formatChecks();
  themeChecks();
  const cases = [
    ["loose statements", 'int x = 3;\nSystem.out.println(x * 2);', "6\n", true],
    ["classes then statements (CS 124 style)", 'public class Pet { public String speak() { return "..."; } }\npublic class Cat extends Pet {\n  @Override\n  public String speak() { return "meow"; }\n}\nPet p = new Cat();\nSystem.out.println(p.speak());', "meow\n", true],
    ["method + statements + control flow", 'int twice(int x) {\n  return 2 * x;\n}\nfor (int i = 0; i < 2; i++) {\n  System.out.println(twice(i));\n}\nif (true) {\n  System.out.println("a");\n} else {\n  System.out.println("b");\n}', "0\n2\na\n", true],
    ["lambda block and array initializer stay statements", 'int[] a = {1, 2, 3};\nRunnable r = () -> {\n  System.out.println(a.length);\n};\nr.run();', "3\n", true],
    ["full program, helper class first", 'class Helper { static int f() { return 4; } }\npublic class Main2 {\n  public static void main(String[] args) { System.out.println(Helper.f()); }\n}', "4\n", false],
    ["compact void main", 'void main() {\n  IO.println("compact");\n}', "compact\n", false],
    ["imports and comments", '// a comment\nimport java.util.ArrayList;\n/* block */ ArrayList<String> xs = new ArrayList<>();\nxs.add("q"); // trailing\nSystem.out.println(xs);', "[q]\n", true],
    ["strings with braces and semicolons", 'String s = "{ ; }";\nSystem.out.println(s);', "{ ; }\n", true],
  ];
  for (const [label, code, want, wrapped] of cases) {
    const r = await runCode("java", code, "", 10);
    eq("java: " + label, [r.stdout, r.exit_code, prepareJava(code).wrapped], [want, 0, wrapped]);
    if (r.exit_code !== 0) console.log(prepareJava(code).source, r.stderr);
  }
  let r = await runCode("java", 'Scanner s = new Scanner(System.in);\nSystem.out.println("got " + s.nextLine());', "hello\n", 10);
  eq("java: stdin reaches Scanner", r.stdout, "got hello\n");
  r = await runCode("java", 'int x = "s";', "", 10);
  eq("java: a compile error is reported, not swallowed", [r.exit_code !== 0, /incompatible types/.test(r.stderr)], [true, true]);
  r = await runCode("java", 'while (true) {}', "", 2);
  eq("java: an infinite loop is stopped at the time limit", r.timed_out, true);
  r = await runCode("python", 'print(input()[::-1])', "abc\n", 10);
  eq("python: runs with stdin", [r.stdout, r.exit_code], ["cba\n", 0]);
  r = await runCode("cpp", '#include <iostream>\nint main(){int a; std::cin>>a; std::cout<<a*a<<"\\n";}', "7", 10);
  eq("c++: compiles and runs with stdin", [r.stdout, r.exit_code], ["49\n", 0]);
  r = await runCode("cpp", 'int main(){ return x; }', "", 10);
  eq("c++: a compile error stops before running", [r.exit_code !== 0, /undeclared identifier/.test(r.stderr)], [true, true]);
  r = await runCode("python", 'print("x" * 200000)', "", 10);
  eq("output is capped", r.stdout.length < 70000 && r.stdout.endsWith("[output cut]"), true);
  console.log(fails ? "FAILED " + fails : "all passed");
  process.exit(fails ? 1 : 0);
})();
