#!/usr/bin/env node

import { existsSync, mkdirSync, cpSync, readFileSync, writeFileSync } from "node:fs";
import { resolve, join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { emitKeypressEvents } from "node:readline";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PKG_ROOT = resolve(__dirname, "..");
const PLUGIN_SRC = join(PKG_ROOT, "job-matching-plugin");
const CWD = process.cwd();
const REPO_URL = "https://github.com/hieutrong512/JobScout";

const RESET = "\x1b[0m";
const GREEN = "\x1b[32m";
const CYAN = "\x1b[36m";
const YELLOW = "\x1b[33m";
const BOLD = "\x1b[1m";
const DIM = "\x1b[2m";

function log(msg) { console.log(msg); }
function ok(msg) { log(`${GREEN}✓${RESET} ${msg}`); }
function info(msg) { log(`${CYAN}→${RESET} ${msg}`); }
function warn(msg) { log(`${YELLOW}!${RESET} ${msg}`); }
function heading(msg) { log(`\n${BOLD}${msg}${RESET}`); }

const command = process.argv[2];

const HELP = `
${BOLD}jobscout${RESET} — AI job matching setup CLI

${BOLD}Usage:${RESET}
  npx jobscout ${CYAN}<command>${RESET}

${BOLD}Commands:${RESET}
  ${CYAN}setup${RESET}           Chọn nền tảng (menu) rồi cài đặt
  ${CYAN}setup claude${RESET}    Cài cho Claude Code
  ${CYAN}setup codex${RESET}     Cài cho Codex CLI
  ${CYAN}setup all${RESET}       Cài cho tất cả nền tảng

${BOLD}Examples:${RESET}
  ${DIM}npx jobscout setup          ${RESET}# hiện menu chọn Claude Code / Codex
  ${DIM}npx jobscout setup claude    ${RESET}# chỉ Claude Code
  ${DIM}npx jobscout setup all       ${RESET}# tất cả
`;

function copyDir(src, dest) {
  cpSync(src, dest, { recursive: true });
}

function ensureDir(dir) {
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

// Copy a file, rewriting plugin-relative schema paths to the target layout.
function copyFileRewrite(src, dest, schemaPath = ".claude/schemas/") {
  let text = readFileSync(src, "utf8");
  text = text
    .replace(/\$\{CLAUDE_PLUGIN_ROOT\}\/schemas\//g, schemaPath)
    .replace(/\.\/schemas\//g, schemaPath);
  ensureDir(dirname(dest));
  writeFileSync(dest, text);
}

function detectPlatforms() {
  const platforms = [];
  if (existsSync(join(CWD, ".claude")) || process.env.CLAUDE_CODE) {
    platforms.push("claude");
  }
  if (existsSync(join(CWD, ".codex")) || process.env.CODEX_HOME) {
    platforms.push("codex");
  }
  return platforms;
}

// ─────────────────────────────────────────────────────────────────────────────
// Interactive multi-select (zero-dep). Trả về mảng platform ("claude"/"codex").
// ─────────────────────────────────────────────────────────────────────────────
function selectPlatforms(defaults = []) {
  const items = [
    { value: "claude", label: "Claude Code", checked: defaults.includes("claude") },
    { value: "codex", label: "Codex", checked: defaults.includes("codex") }
  ];

  return new Promise((res) => {
    // Không phải TTY (CI, pipe) → không hỏi, dùng defaults hoặc cả hai.
    if (!process.stdin.isTTY) {
      const picked = items.filter((i) => i.checked).map((i) => i.value);
      res(picked.length ? picked : ["claude", "codex"]);
      return;
    }

    let cursor = 0;
    let rendered = 0;

    const allChecked = () => items.every((i) => i.checked);
    const anyChecked = () => items.some((i) => i.checked);

    function render() {
      // Xóa các dòng đã vẽ lần trước.
      if (rendered > 0) process.stdout.write(`\x1b[${rendered}A`);
      const lines = [];
      lines.push(`${CYAN}◆${RESET}  ${BOLD}Cài JobScout cho nền tảng nào?${RESET}`);
      lines.push(`${DIM}│${RESET}  ${DIM}↑/↓ di chuyển · space chọn · a chọn tất cả · enter xác nhận${RESET}`);
      items.forEach((item, i) => {
        const box = item.checked ? `${GREEN}[+]${RESET}` : "[ ]";
        const pointer = i === cursor ? `${CYAN}❯${RESET}` : " ";
        const label = i === cursor ? `${BOLD}${item.label}${RESET}` : item.label;
        lines.push(`${DIM}│${RESET}  ${pointer} ${box} ${label}`);
      });
      const allBox = allChecked() ? `${GREEN}[+]${RESET}` : "[ ]";
      const allPointer = cursor === items.length ? `${CYAN}❯${RESET}` : " ";
      const allLabel = cursor === items.length ? `${BOLD}All${RESET}` : "All";
      lines.push(`${DIM}│${RESET}  ${allPointer} ${allBox} ${allLabel}`);
      lines.push(`${DIM}└${RESET}`);
      // Xóa cuối mỗi dòng để không sót ký tự cũ.
      process.stdout.write(lines.map((l) => `\x1b[2K${l}`).join("\n") + "\n");
      rendered = lines.length;
    }

    function cleanup() {
      process.stdin.setRawMode(false);
      process.stdin.pause();
      process.stdin.removeListener("keypress", onKey);
      process.stdout.write("\x1b[?25h"); // hiện lại con trỏ
    }

    function toggleCurrent() {
      if (cursor === items.length) {
        // Dòng "All": bật/tắt tất cả.
        const next = !allChecked();
        items.forEach((i) => (i.checked = next));
      } else {
        items[cursor].checked = !items[cursor].checked;
      }
    }

    function onKey(str, key) {
      if (!key) return;
      if (key.name === "up") {
        cursor = (cursor - 1 + (items.length + 1)) % (items.length + 1);
      } else if (key.name === "down") {
        cursor = (cursor + 1) % (items.length + 1);
      } else if (key.name === "space") {
        toggleCurrent();
      } else if (str === "a" || str === "A") {
        const next = !allChecked();
        items.forEach((i) => (i.checked = next));
      } else if (key.name === "return") {
        if (!anyChecked()) return; // cần chọn ít nhất một
        cleanup();
        log("");
        res(items.filter((i) => i.checked).map((i) => i.value));
        return;
      } else if (key.name === "escape" || (key.ctrl && key.name === "c")) {
        cleanup();
        log("");
        warn("Đã hủy.");
        process.exit(0);
      }
      render();
    }

    emitKeypressEvents(process.stdin);
    process.stdin.setRawMode(true);
    process.stdin.resume();
    process.stdout.write("\x1b[?25l"); // ẩn con trỏ
    render();
    process.stdin.on("keypress", onKey);
  });
}

// Skills cần cho Claude — bỏ find-jobs/job-collector/job-matcher (command + agents đã lo).
const CLAUDE_SKILLS = [
  "candidate-intake",
  "scoring-rubric",
  "job-schema",
  "bilingual-normalization",
  "fit-analyzer",
  "application-assistant"
];

function setupClaude() {
  heading("Claude Code");

  const dotClaude = join(CWD, ".claude");
  const agentsDest = join(dotClaude, "agents");
  const commandsDest = join(dotClaude, "commands");
  const skillsDest = join(dotClaude, "skills");
  const schemasDest = join(dotClaude, "schemas");

  [agentsDest, commandsDest, skillsDest, schemasDest].forEach(ensureDir);

  // Schemas (nguồn dùng chung, không rewrite nội dung JSON).
  const schemasSrc = join(PLUGIN_SRC, "schemas");
  copyDir(schemasSrc, schemasDest);
  ok("Copy .claude/schemas/ (profile, job, match)");

  // Agents — chạy context riêng cho bước tốn token.
  ["job-collector", "job-matcher"].forEach((name) => {
    copyFileRewrite(
      join(PLUGIN_SRC, "agents", `${name}.md`),
      join(agentsDest, `${name}.md`)
    );
  });
  ok("Copy .claude/agents/ (job-collector, job-matcher)");

  // Command /find-jobs.
  copyFileRewrite(
    join(PLUGIN_SRC, "commands", "find-jobs.md"),
    join(commandsDest, "find-jobs.md")
  );
  ok("Copy .claude/commands/find-jobs.md → slash command /find-jobs");

  // Skills.
  CLAUDE_SKILLS.forEach((name) => {
    copyFileRewrite(
      join(PLUGIN_SRC, "skills", name, "SKILL.md"),
      join(skillsDest, name, "SKILL.md")
    );
  });
  ok(`Copy .claude/skills/ (${CLAUDE_SKILLS.length} skills)`);

  return {
    label: "Claude Code",
    detail: `${CLAUDE_SKILLS.length} skills + 2 agents → .claude/`,
    steps: [`Trong Claude Code chạy: ${CYAN}/find-jobs path/to/CV.pdf${RESET}`]
  };
}

// Codex chỉ auto-discover skills trong skills/ — nên flatten mọi thứ (kể cả
// orchestrator find-jobs và 2 "agent" job-collector/job-matcher) thành skills.
const CODEX_SKILLS = [
  "find-jobs",
  "job-collector",
  "job-matcher",
  ...CLAUDE_SKILLS
];

function setupCodex() {
  heading("Codex CLI");

  const dotAgents = join(CWD, ".agents");
  const skillsDest = join(dotAgents, "skills");
  const schemasDest = join(dotAgents, "schemas");

  [skillsDest, schemasDest].forEach(ensureDir);

  // Schemas — file path để skill đọc runtime (Codex không auto-discover, chỉ đọc).
  copyDir(join(PLUGIN_SRC, "schemas"), schemasDest);
  ok("Copy .agents/schemas/ (profile, job, match)");

  // Toàn bộ skills (gồm orchestrator + collector + matcher).
  CODEX_SKILLS.forEach((name) => {
    copyFileRewrite(
      join(PLUGIN_SRC, "skills", name, "SKILL.md"),
      join(skillsDest, name, "SKILL.md"),
      ".agents/schemas/"
    );
  });
  ok(`Copy .agents/skills/ (${CODEX_SKILLS.length} skills)`);

  return {
    label: "Codex CLI",
    detail: `${CODEX_SKILLS.length} skills → .agents/`,
    steps: [
      `Chạy: ${CYAN}codex --search${RESET}  ${DIM}# bật web search${RESET}`,
      `Gọi skill ${CYAN}find-jobs${RESET} với đường dẫn CV`
    ]
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Hộp "ready to use" — hướng dẫn bước tiếp theo sau khi cài xong.
// ─────────────────────────────────────────────────────────────────────────────
const ANSI_RE = /\x1b\[[0-9;]*m/g;
function visibleLen(s) { return s.replace(ANSI_RE, "").length; }

function printReadyBox(results) {
  const lines = [];
  results.forEach((r) => {
    lines.push(`${GREEN}✓${RESET}  ${BOLD}${r.label}${RESET}  ${DIM}${r.detail}${RESET}`);
  });
  lines.push("");
  lines.push(`${DIM}Installed to:${RESET} ${CWD}`);
  lines.push("");
  lines.push(`${BOLD}Bước tiếp theo:${RESET}`);
  lines.push(`  1. Mở project ở folder này bằng AI agent của bạn`);
  let n = 2;
  results.forEach((r) => {
    r.steps.forEach((s) => {
      lines.push(`  ${n}. ${s}`);
      n += 1;
    });
  });
  lines.push("");
  lines.push(`${DIM}Repo: ${REPO_URL}${RESET}`);

  const inner = Math.max(...lines.map(visibleLen), visibleLen("JobScout đã sẵn sàng!")) + 2;
  const top = `┌─ ${BOLD}${GREEN}JobScout đã sẵn sàng!${RESET} ${"─".repeat(Math.max(0, inner - visibleLen("JobScout đã sẵn sàng!") - 3))}┐`;
  log("");
  log(top);
  log(`│${" ".repeat(inner)}│`);
  lines.forEach((l) => {
    const pad = inner - 1 - visibleLen(l);
    log(`│ ${l}${" ".repeat(Math.max(0, pad))}│`);
  });
  log(`│${" ".repeat(inner)}│`);
  log(`└${"─".repeat(inner)}┘`);
}

function runPlatforms(platforms) {
  const results = [];
  platforms.forEach((p) => {
    if (p === "claude") results.push(setupClaude());
    if (p === "codex") results.push(setupCodex());
  });
  printReadyBox(results);
}

async function runSetup(platform) {
  log(`${BOLD}🔧 JobScout Setup${RESET}`);

  if (platform === "all") {
    runPlatforms(["claude", "codex"]);
    return;
  }
  if (platform === "claude" || platform === "codex") {
    runPlatforms([platform]);
    return;
  }
  if (platform) {
    warn(`Platform "${platform}" không hợp lệ. Dùng: claude, codex, all`);
    process.exit(1);
  }

  // Không chỉ định platform → hỏi qua menu (mặc định gợi ý theo nền tảng phát hiện được).
  const detected = detectPlatforms();
  if (detected.length) info(`Phát hiện sẵn: ${detected.join(", ")}`);
  const picked = await selectPlatforms(detected);
  runPlatforms(picked);
}

if (!command || command === "help" || command === "--help" || command === "-h") {
  log(HELP);
} else if (command === "setup") {
  await runSetup(process.argv[3]);
} else {
  warn(`Lệnh "${command}" không tồn tại.`);
  log(HELP);
  process.exit(1);
}
