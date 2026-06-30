import { execSync } from 'child_process';
import path from 'path';
import fs from 'fs';

const ROOT_DIR = path.resolve(__dirname, '../..');

/**
 * Inbox Orchestrator
 * Challs audit -> fix -> pdf -> dedup -> merge-plan -> normalize
 */

async function runInboxPipeline() {
    const args = process.argv.slice(2);
    const batchIndex = args.indexOf('--batch');
    const apply = args.includes('--apply');

    const stagingPath = path.join(ROOT_DIR, 'content/_INBOX/_staging');
    let batches: string[] = [];

    if (batchIndex !== -1 && args[batchIndex + 1]) {
        batches = [args[batchIndex + 1]];
    } else {
        // Auto-discover batches (subdirectories in _staging)
        if (!fs.existsSync(stagingPath)) {
            console.log('📭 Inbox directory does not exist.');
            return;
        }

        const entries = fs.readdirSync(stagingPath, { withFileTypes: true });

        // 1. Subdirectories are separate batches
        batches = entries
            .filter(e => e.isDirectory() && !e.name.startsWith('_') && !e.name.startsWith('.'))
            .map(e => e.name);

        // 2. Files in the root of _staging are a "root" batch
        const hasRootFiles = entries.some(e => e.isFile() && !e.name.startsWith('.') && e.name !== 'manifest.json');
        if (hasRootFiles) {
            batches.push('.');
        }
    }

    if (batches.length === 0) {
        console.log('📭 Inbox is empty. Nothing to process.');
        return;
    }

    const applyFlag = apply ? '--apply' : '';

    for (const batchName of batches) {
        const displayName = batchName === '.' ? 'ROOT_INBOX' : batchName;
        console.log(`\n==================================================`);
        console.log(`🚀 Processing Inbox: ${displayName}`);
        console.log(`==================================================\n`);

        const steps = [
            { name: 'Audit', cmd: `npm run inbox:audit -- --batch "${batchName}"` },
            { name: 'Fix Names', cmd: `npm run inbox:fix -- --batch "${batchName}" ${applyFlag}` },
            { name: 'Process PDFs', cmd: `npm run inbox:pdf -- --batch "${batchName}" ${applyFlag}` },
            { name: 'Detect Duplicates', cmd: `npm run inbox:dedup -- --batch "${batchName}"` },
            { name: 'Create Merge Plan', cmd: `npm run inbox:merge-plan -- --batch "${batchName}"` },
            { name: 'Normalize', cmd: `npm run inbox:normalize -- --batch "${batchName}" ${applyFlag}` }
        ];

        for (const step of steps) {
            console.log(`\n--- STEP: ${step.name} ---`);
            try {
                execSync(step.cmd, { stdio: 'inherit' });
            } catch (err) {
                console.error(`\n❌ Step "${step.name}" failed for batch "${displayName}". Skipping to next.`);
                break; // Move to next batch
            }
        }

        console.log(`\n✅ Finished batch: ${displayName}`);
    }

    if (!apply) {
        console.log(`\n💡 Note: This was a SUGGEST-ONLY run. Re-run with --apply to finalize changes.`);
    }
}

runInboxPipeline().catch(err => {
    console.error('💥 Pipeline failed:', err);
    process.exit(1);
});
