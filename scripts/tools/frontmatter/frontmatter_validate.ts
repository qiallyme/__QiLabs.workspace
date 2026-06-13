// validate-eos-frontmatter.ts
import fs from "fs";
import path from "path";
import matter from "gray-matter";
import Ajv from "ajv";

const ajv = new Ajv({ allErrors: true });

// Load schema
// Resolve schema path relative to script location or cwd
const rootDir = process.cwd();
const schemaPath = path.join(rootDir, "eos_frontmatter.schema.json");
if (!fs.existsSync(schemaPath)) {
  console.error(`❌ Schema not found at: ${schemaPath}`);
  process.exit(1);
}
const schema = JSON.parse(fs.readFileSync(schemaPath, "utf8"));
const validate = ajv.compile(schema);

// Helper: get all EOS files (0.00.*)
function getEosFiles(rootDir: string): string[] {
  const files: string[] = [];
  function walk(dir: string) {
    for (const entry of fs.readdirSync(dir)) {
      const full = path.join(dir, entry);
      const stat = fs.statSync(full);
      if (stat.isDirectory()) {
        walk(full);
      } else if (
        entry.endsWith(".md") &&
        entry.startsWith("0.00.")
      ) {
        files.push(full);
      }
    }
  }
  walk(rootDir);
  return files;
}

function validateFile(filePath: string): string[] {
  const raw = fs.readFileSync(filePath, "utf8");
  const parsed = matter(raw);

  // Front matter is YAML; parsed.data is already JS object
  const data = parsed.data;

  const ok = validate(data);
  const errors: string[] = [];

  if (!ok && validate.errors) {
    for (const err of validate.errors) {
      errors.push(
        `${err.instancePath || "(root)"} ${err.message || ""}`.trim()
      );
    }
  }

  // Additional custom checks
  // filename ↔ qi_decimal ↔ file_name
  const fileBase = path.basename(filePath, ".md");
  const expectedPrefix = data.qi_decimal;
  if (!fileBase.startsWith(expectedPrefix + "_")) {
    errors.push(
      `filename '${fileBase}' does not start with qi_decimal '${expectedPrefix}_'`
    );
  }

  if (data.file_name !== fileBase) {
    errors.push(
      `file_name '${data.file_name}' does not match actual name '${fileBase}'`
    );
  }

  // Required EOS tag presence
  const tags: string[] = Array.isArray(data.tags) ? data.tags : [];
  const requiredTags = ["realm-eos"]; // realm-eos is mandatory for all EOS files
  for (const t of requiredTags) {
    if (!tags.includes(t)) {
      errors.push(`missing required tag '${t}'`);
    }
  }

  return errors;
}

function main() {
  const root = process.argv[2] || process.cwd();
  const files = getEosFiles(root);

  let hasErrors = false;

  for (const f of files) {
    const errs = validateFile(f);
    if (errs.length > 0) {
      hasErrors = true;
      console.log(`❌ ${f}`);
      for (const e of errs) {
        console.log(`   - ${e}`);
      }
    } else {
      console.log(`✅ ${f}`);
    }
  }

  if (hasErrors) {
    process.exitCode = 1;
  } else {
    process.exitCode = 0;
  }
}

main();

