#!/usr/bin/env node

import { existsSync, mkdirSync, cpSync, readFileSync, writeFileSync } from "node:fs";
import { resolve, join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PKG_ROOT = resolve(__dirname, "..");
const PLUGIN_SRC = join(PKG_ROOT, "job-matching-plugin");
const CHATGPT_SRC = join(PKG_ROOT, "chatgpt");
const CWD = process.cwd();

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
${BOLD}job-matching${RESET} — AI job matching setup CLI

${BOLD}Usage:${RESET}
  npx job-matching ${CYAN}<command>${RESET}

${BOLD}Commands:${RESET}
  ${CYAN}setup${RESET}           Auto-detect platform & install (recommended)
  ${CYAN}setup claude${RESET}    Setup for Claude Code
  ${CYAN}setup codex${RESET}     Setup for Codex CLI
  ${CYAN}setup chatgpt${RESET}   Setup for ChatGPT (copy files to configure Custom GPT)
  ${CYAN}setup all${RESET}       Setup for all platforms

${BOLD}Examples:${RESET}
  ${DIM}npx job-matching setup          ${RESET}# auto-detect
  ${DIM}npx job-matching setup claude    ${RESET}# Claude Code only
  ${DIM}npx job-matching setup chatgpt   ${RESET}# ChatGPT only
`;

function copyDir(src, dest) {
  cpSync(src, dest, { recursive: true });
}

function ensureDir(dir) {
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
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

function setupClaude() {
  heading("Claude Code");

  const marketplaceDest = join(CWD, ".claude-plugin");
  const pluginDest = join(CWD, "job-matching-plugin");

  ensureDir(marketplaceDest);

  const marketplace = {
    name: "jobmatching-marketplace",
    owner: { name: "JobMatching" },
    metadata: {
      description: "Marketplace chứa plugin Job Matching — tìm job phù hợp với target + CV.",
      version: "1.2.0"
    },
    plugins: [
      {
        name: "job-matching",
        source: "./job-matching-plugin",
        description: "Tìm và xếp hạng job phù hợp nhất với target + CV. Song ngữ Việt–Anh.",
        version: "1.2.0"
      }
    ]
  };

  writeFileSync(
    join(marketplaceDest, "marketplace.json"),
    JSON.stringify(marketplace, null, 2) + "\n"
  );
  ok("Tạo .claude-plugin/marketplace.json");

  copyDir(PLUGIN_SRC, pluginDest);
  ok("Copy job-matching-plugin/ (skills, schemas, agents, commands)");

  log("");
  info("Mở Claude Code terminal rồi chạy:");
  log(`   ${CYAN}/plugin marketplace add .${RESET}`);
  log(`   ${CYAN}/plugin install job-matching${RESET}`);
  log(`   ${CYAN}/find-jobs path/to/CV.pdf${RESET}`);
}

function setupCodex() {
  heading("Codex CLI");

  const pluginDest = join(CWD, "job-matching-plugin");
  copyDir(PLUGIN_SRC, pluginDest);
  ok("Copy job-matching-plugin/ (skills, schemas, .codex-plugin)");

  log("");
  info("Chạy Codex:");
  log(`   ${CYAN}codex --search${RESET}  ${DIM}# bật web search${RESET}`);
  log(`   Gọi skill ${CYAN}find-jobs${RESET} với đường dẫn CV.`);
}

function setupChatgpt() {
  heading("ChatGPT");

  const dest = join(CWD, "job-matching-chatgpt");
  ensureDir(dest);

  const instrSrc = join(CHATGPT_SRC, "GPT-INSTRUCTIONS.md");
  const instrDest = join(dest, "GPT-INSTRUCTIONS.md");
  cpSync(instrSrc, instrDest);
  ok("Copy GPT-INSTRUCTIONS.md");

  const knowledgeSrc = join(CHATGPT_SRC, "knowledge");
  if (existsSync(knowledgeSrc)) {
    const knowledgeDest = join(dest, "knowledge");
    copyDir(knowledgeSrc, knowledgeDest);
    ok("Copy knowledge/ (skills + schemas)");
  }

  log("");
  info("Tạo Custom GPT:");
  log(`   1. Vào ${CYAN}chatgpt.com/gpts/editor${RESET} → Create`);
  log(`   2. Instructions: dán nội dung ${CYAN}${instrDest}${RESET}`);
  log(`   3. Knowledge: kéo-thả tất cả file trong ${CYAN}${join(dest, "knowledge")}${RESET}`);
  log(`   4. Bật ${CYAN}Web Search${RESET} → Save → Publish`);
}

function runSetup(platform) {
  log(`${BOLD}🔧 JobMatching Setup${RESET}`);

  if (!platform) {
    const detected = detectPlatforms();
    if (detected.length > 0) {
      info(`Phát hiện: ${detected.join(", ")}`);
      detected.forEach((p) => {
        if (p === "claude") setupClaude();
        if (p === "codex") setupCodex();
      });
    } else {
      info("Không phát hiện Claude Code / Codex. Setup cho tất cả nền tảng.");
      setupClaude();
      setupCodex();
      setupChatgpt();
    }
  } else if (platform === "claude") {
    setupClaude();
  } else if (platform === "codex") {
    setupCodex();
  } else if (platform === "chatgpt") {
    setupChatgpt();
  } else if (platform === "all") {
    setupClaude();
    setupCodex();
    setupChatgpt();
  } else {
    warn(`Platform "${platform}" không hợp lệ. Dùng: claude, codex, chatgpt, all`);
    process.exit(1);
  }

  heading("Xong!");
  log(`Repo: ${DIM}https://github.com/hieutrong512/JobMatching${RESET}`);
}

if (!command || command === "help" || command === "--help" || command === "-h") {
  log(HELP);
} else if (command === "setup") {
  runSetup(process.argv[3]);
} else {
  warn(`Lệnh "${command}" không tồn tại.`);
  log(HELP);
  process.exit(1);
}
