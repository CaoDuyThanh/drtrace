#!/usr/bin/env node

/**
 * CLI entry point for drtrace init command
 * Usage: npx drtrace init [--project-root <path>]
 */

const yargs = require("yargs");
const { hideBin } = require("yargs/helpers");
const { runInitProject } = require("../init");

yargs(hideBin(process.argv))
  .command(
    "init",
    "Interactive DrTrace project initialization with config and templates",
    (yargs) =>
      yargs.option("project-root", {
        alias: "p",
        type: "string",
        description: "Project root directory (default: current directory)",
      }),
    async (argv) => {
      const exitCode = await runInitProject(argv["project-root"]);
      process.exit(exitCode);
    }
  )
  .demandCommand()
  .strict()
  .help()
  .alias("h", "help")
  .parse();
