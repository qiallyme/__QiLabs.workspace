import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { glob } from 'glob';
import { loadRepoRules } from '../../packages/config/src/repoRules';
import { RulesRegistry } from '../../packages/config/src/rulesRegistry';

const ROOT_DIR = path.resolve(__dirname, '../..');

async function auditInbox() {
    const args = process.argv.slice(2);
    const batchIndex = args.indexOf('--batch');
    if (batchIndex === -1 || !args[batchIndex + 1]) {
        console.error('Usage: tsx audit_inbox.ts --batch <path_relative_to_inbox_staging>');
        process.exit(1);
    }

    const batchName = args[batchIndex + 1];
    const isRoot = batchName === '.' || batchName === './' || batchName === '';
    const reportName = isRoot ? 'ROOT_INBOX' : batchName;
    const batchPath = path.join(ROOT_DIR, 'content/_INBOX/_staging', isRoot ? '' : batchName);

    if (!fs.existsSync(batchPath)) {
        console.error(`Batch path not found: ${batchPath}`);
        process.exit(1);
    }

    console.log(`🔍 Auditing Inbox Batch: ${reportName}...`);
    const rules = loadRepoRules(ROOT_DIR);

    // If root, only audit files in staging root to avoid double-processing sub-batches
    const globPattern = isRoot ? '*' : '**/*';
    const files = await glob(globPattern, {
        cwd: batchPath,
        nodir: true,
        ignore: rules.ignore_globs,
    });

    const inventory: any[] = [];
    const violations: any[] = [];

    for (const relPath of files) {
        const fullPath = path.join(batchPath, relPath);
        const stats = fs.statSync(fullPath);
        const buffer = fs.readFileSync(fullPath);
        const sha256 = crypto.createHash('sha256').update(buffer).digest('hex');
        const ext = path.extname(relPath).toLowerCase();
        const baseName = path.basename(relPath);

        const entry = {
            path: relPath,
            size: stats.size,
            sha256,
            ext,
            type: classifyType(ext),
        };
        inventory.push(entry);

        // Check violations
        if (baseName.includes(' ')) {
            violations.push({ path: relPath, rule: 'FILE_NO_SPACES', message: 'Contains spaces.' });
        }
        if (!/^[a-z0-9_.-]+$/.test(baseName.toLowerCase())) {
            violations.push({ path: relPath, rule: 'FILE_ILLEGAL_CHARS', message: 'Contains illegal characters.' });
        }
        if (path.basename(baseName, ext).length > rules.filename.max_base_len) {
            violations.push({ path: relPath, rule: 'FILE_LENGTH_LIMIT', message: `Too long (${path.basename(baseName, ext).length} chars).` });
        }
    }

    // Reports
    const reportDir = path.join(ROOT_DIR, 'content/_INBOX/_reports');
    if (!fs.existsSync(reportDir)) fs.mkdirSync(reportDir, { recursive: true });

    const jsonReport = {
        batch: reportName,
        timestamp: new Date().toISOString(),
        counts: {
            total_files: inventory.length,
            violations: violations.length,
        },
        inventory,
        violations,
    };

    fs.writeFileSync(path.join(reportDir, `${reportName}_audit.json`), JSON.stringify(jsonReport, null, 2));

    let mdReport = `# Audit Report: ${reportName}\n\n`;
    mdReport += `**Timestamp:** ${jsonReport.timestamp}\n`;
    mdReport += `**Total Files:** ${jsonReport.counts.total_files}\n`;
    mdReport += `**Violations:** ${jsonReport.counts.violations}\n\n`;

    if (violations.length > 0) {
        mdReport += `## Violations\n\n`;
        violations.forEach(v => {
            mdReport += `- **${v.path}**: ${v.message} (${v.rule})\n`;
        });
    } else {
        mdReport += `✅ No rule violations detected.\n`;
    }

    fs.writeFileSync(path.join(reportDir, `${reportName}_audit.md`), mdReport);

    // Manifest
    const manifestPath = path.join(batchPath, 'manifest.json');
    const existingManifest = fs.existsSync(manifestPath) ? JSON.parse(fs.readFileSync(manifestPath, 'utf8')) : {};
    const updatedManifest = {
        ...existingManifest,
        batch: batchName,
        last_audit: jsonReport.timestamp,
        inventory,
    };
    fs.writeFileSync(manifestPath, JSON.stringify(updatedManifest, null, 2));

    console.log(`✅ Audit complete. Reports written to _reports/${batchName}_audit.json/md`);
}

function classifyType(ext: string): string {
    const types: Record<string, string[]> = {
        pdf: ['.pdf'],
        image: ['.jpg', '.jpeg', '.png', '.webp', '.tiff'],
        video: ['.mp4', '.mov', '.avi'],
        doc: ['.docx', '.doc', '.xlsx'],
        text: ['.txt', '.md', '.mdx'],
    };
    for (const [type, exts] of Object.entries(types)) {
        if (exts.includes(ext)) return type;
    }
    return 'unknown';
}

auditInbox().catch(err => {
    console.error('💥 Audit script failed:', err);
    process.exit(1);
});
