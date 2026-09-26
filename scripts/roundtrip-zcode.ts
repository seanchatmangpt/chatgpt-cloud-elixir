#!/usr/bin/env bun
/**
 * Deterministic CONSTRUCT fixture for the cross-repository round-trip court.
 *
 * This is not a replacement worker. It imports zcode-cli's production
 * runGallWork orchestrator from an exact pinned checkout and substitutes only
 * the model coding turn. Claim/heartbeat/persist/git-head/close all execute
 * through production zcode against a real XaaS HTTP fabric.
 */
import { execFile } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const zcodeRepo = process.env.ZCODE_REPO?.trim();
if (!zcodeRepo) throw new Error("ZCODE_REPO is required");

const gallWorkUrl = pathToFileURL(resolve(zcodeRepo, "src/gall-work.ts")).href;
const { runGallWork } = await import(gallWorkUrl) as typeof import("../../zcode-cli/src/gall-work.ts");

const exitCode = await runGallWork(process.argv.slice(2), {
  env: process.env,
  construct: async (request, _prompt, onHeartbeat) => {
    const started = Date.now();

    // Exercise the real lease renewal edge before consequence.
    await onHeartbeat();

    const artifact = join(request.cwd, "CHATGPT_ROUNDTRIP_RECEIPT.txt");
    await writeFile(
      artifact,
      [
        "chatgpt-cloud-elixir round-trip court",
        `epoch=${request.epochId}`,
        `worker=${request.workerId}`,
        "construct=deterministic-fixture",
        ""
      ].join("\n"),
      "utf8"
    );

    await execFileAsync("git", ["add", "CHATGPT_ROUNDTRIP_RECEIPT.txt"], { cwd: request.cwd });
    await execFileAsync(
      "git",
      [
        "-c", "user.name=ChatGPT Roundtrip Court",
        "-c", "user.email=roundtrip-court@localhost",
        "commit", "-m", "test: execute ChatGPT XaaS zcode round trip"
      ],
      { cwd: request.cwd }
    );

    return {
      exitCode: 0,
      signal: null,
      outputTail: "deterministic construct committed CHATGPT_ROUNDTRIP_RECEIPT.txt",
      durationMs: Date.now() - started
    };
  }
});

process.exitCode = exitCode;
