import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import { loadRepoRules } from '../../packages/config/src/repoRules';

const ROOT_DIR = path.resolve(__dirname, '../..');

async function fixInboxNames() {
    const args = process.argv.slice(2);
    const batchIndex = args.indexOf('--batch');
    const apply = args.includes('--apply');

    if (batchIndex === -1 || !args[batchIndex + 1]) {
        console.error('Usage: tsx fix_inbox_names.ts --batch <batch_name> [--apply]');
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

    console.log(`🛠️  Fixing Names in Batch: ${reportName}${apply ? ' (APPLY MODE)' : ' (SUGGEST MODE)'}...`);
    const rules = loadRepoRules(ROOT_DIR);

    const files = await glob('**/*', {
        cwd: batchPath,
        nodir: true,
        ignore: rules.ignore_globs,
    });

    const fixLog: any[] = [];

    for (const relPath of files) {
        const fullPath = path.join(batchPath, relPath);
        const baseName = path.basename(relPath);

        let newName = baseName;

        // 1. Replace spaces with underscores
        if (newName.includes(' ')) {
            newName = newName.replace(/\s+/g, '_');
        }

        // 2. Date normalization (e.g., 2026_02_03 -> 2026-02-03)
        const dateMatch = newName.match(/^(\d{4})[_-](\d{2})[_-](\d{2})(.*)/);
        if (dateMatch) {
            const y = dateMatch[1];
            const m = dateMatch[2];
            const d = dateMatch[3];
            const rest = dateMatch[4];
            // Normalize separator to dash for dates
            newName = `${y}-${m}-${d}${rest.startsWith('_') || rest.startsWith('-') ? rest : '_' + rest}`;
        }

        // 3. Lowercase normalization (conservative)
        if (!/^[a-z0-9_.-]+$/.test(newName)) {
            // newName = newName.toLowerCase(); 
        }

        if (newName !== baseName) {
            fixLog.push({ original: baseName, suggested: newName, path: relPath });

            if (apply) {
                const newPath = path.join(path.dirname(fullPath), newName);
                if (fs.existsSync(newPath)) {
                    console.warn(`⚠️  Cannot rename ${baseName} to ${newName}: Collision.`);
                } else {
                    fs.renameSync(fullPath, newPath);
                    console.log(`✨ Renamed: ${baseName} -> ${newName}`);
                }
            } else {
                console.log(`💡 Suggest: ${baseName} -> ${newName}`);
            }
        }
    }

    const reportDir = path.join(ROOT_DIR, 'content/_INBOX/_reports');
    fs.writeFileSync(path.join(reportDir, `${reportName}_fix_log.json`), JSON.stringify(fixLog, null, 2));

    console.log(`\n✅ Processed ${files.length} files. ${fixLog.length} fixes ${apply ? 'applied' : 'suggested'}.`);
}

fixInboxNames().catch(err => {
    console.error('💥 Fix script failed:', err);
    process.exit(1);
});
