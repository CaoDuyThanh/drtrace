/**
 * Comprehensive tests for DrTrace JavaScript Config Schema and Init
 */

import * as fs from "fs";
import * as path from "path";
import { ConfigSchema, DrTraceConfig } from "../src/config-schema";
import { ProjectInitializer } from "../src/init";
import * as os from "os";

describe("ConfigSchema", () => {
  describe("getDefaultConfig", () => {
    it("should generate default config with required fields", () => {
      const config = ConfigSchema.getDefaultConfig({
        project_name: "test-app",
        application_id: "test-app-123",
      });

      expect(config.project_name).toBe("test-app");
      expect(config.application_id).toBe("test-app-123");
      expect(config.language).toBe("javascript");
      expect(config.daemon_url).toBe("http://localhost:8001");
      expect(config.enabled).toBe(true);
      expect(config.created_at).toBeDefined();
    });

    it("should accept custom values", () => {
      const config = ConfigSchema.getDefaultConfig({
        project_name: "my-project",
        application_id: "my-app",
        language: "python",
        daemon_url: "http://prod:8001",
        enabled: false,
        environments: ["production", "staging"],
        agent_enabled: true,
        agent_framework: "langchain",
      });

      expect(config.language).toBe("python");
      expect(config.daemon_url).toBe("http://prod:8001");
      expect(config.enabled).toBe(false);
      expect(config.environments).toEqual(["production", "staging"]);
      expect(config.agent?.enabled).toBe(true);
      expect(config.agent?.framework).toBe("langchain");
    });
  });

  describe("validate", () => {
    it("should require project_name", () => {
      const config: any = { application_id: "test" };
      expect(() => ConfigSchema.validate(config)).toThrow(
        "Missing required field: project_name"
      );
    });

    it("should require application_id", () => {
      const config: any = { project_name: "test" };
      expect(() => ConfigSchema.validate(config)).toThrow(
        "Missing required field: application_id"
      );
    });

    it("should accept valid environments", () => {
      const config = ConfigSchema.getDefaultConfig({
        project_name: "test",
        application_id: "test",
        environments: ["development", "production"],
      });
      expect(() => ConfigSchema.validate(config)).not.toThrow();
    });

    it("should reject invalid environments", () => {
      const config = ConfigSchema.getDefaultConfig({
        project_name: "test",
        application_id: "test",
        environments: ["development", "invalid-env"] as any,
      });
      expect(() => ConfigSchema.validate(config)).toThrow(
        "Invalid environment"
      );
    });
  });

  describe("save and load", () => {
    it("should save and load config files", () => {
      const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "drtrace-test-"));
      const configPath = path.join(tmpDir, "config.json");

      const original = ConfigSchema.getDefaultConfig({
        project_name: "test-app",
        application_id: "test-app",
      });

      ConfigSchema.save(original, configPath);
      expect(fs.existsSync(configPath)).toBe(true);

      const loaded = ConfigSchema.load(configPath);
      expect(loaded.project_name).toBe(original.project_name);
      expect(loaded.application_id).toBe(original.application_id);

      // Cleanup
      fs.rmSync(tmpDir, { recursive: true });
    });

    it("should throw on nonexistent file", () => {
      expect(() => ConfigSchema.load("/nonexistent/path/config.json")).toThrow(
        "Config file not found"
      );
    });
  });
});

describe("ProjectInitializer", () => {
  it("should initialize with custom project root", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "drtrace-test-"));
    const initializer = new ProjectInitializer(tmpDir);

    expect((initializer as any).projectRoot).toBe(tmpDir);
    expect((initializer as any).drtraceDir).toBe(path.join(tmpDir, "_drtrace"));

    fs.rmSync(tmpDir, { recursive: true });
  });

  it("should create directory structure", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "drtrace-test-"));
    const initializer = new ProjectInitializer(tmpDir);

    (initializer as any).createDirectoryStructure();

    expect(fs.existsSync(path.join(tmpDir, "_drtrace"))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, "_drtrace", "agents"))).toBe(true);

    fs.rmSync(tmpDir, { recursive: true });
  });

  it("should generate environment configs", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "drtrace-test-"));
    const initializer = new ProjectInitializer(tmpDir);

    (initializer as any).createDirectoryStructure();

    const config = ConfigSchema.getDefaultConfig({
      project_name: "test",
      application_id: "test",
      environments: ["development", "production"],
    });

    (initializer as any).generateEnvironmentConfigs(config);

    expect(
      fs.existsSync(path.join(tmpDir, "_drtrace", "config.development.json"))
    ).toBe(true);
    expect(
      fs.existsSync(path.join(tmpDir, "_drtrace", "config.production.json"))
    ).toBe(true);

    fs.rmSync(tmpDir, { recursive: true });
  });

  it("should generate .env.example", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "drtrace-test-"));
    const initializer = new ProjectInitializer(tmpDir);

    (initializer as any).createDirectoryStructure();

    const config = ConfigSchema.getDefaultConfig({
      project_name: "test",
      application_id: "test-app-123",
    });

    (initializer as any).generateEnvExample(config);

    const envFile = path.join(tmpDir, "_drtrace", ".env.example");
    expect(fs.existsSync(envFile)).toBe(true);

    const content = fs.readFileSync(envFile, "utf-8");
    expect(content).toContain("DRTRACE_APPLICATION_ID=test-app-123");
    expect(content).toContain("DRTRACE_DAEMON_URL=http://localhost:8001");

    fs.rmSync(tmpDir, { recursive: true });
  });

  it("should generate README", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "drtrace-test-"));
    const initializer = new ProjectInitializer(tmpDir);

    (initializer as any).createDirectoryStructure();
    (initializer as any).generateReadme();

    const readmeFile = path.join(tmpDir, "_drtrace", "README.md");
    expect(fs.existsSync(readmeFile)).toBe(true);

    const content = fs.readFileSync(readmeFile, "utf-8");
    expect(content).toContain("DrTrace Configuration Guide");

    fs.rmSync(tmpDir, { recursive: true });
  });
});
