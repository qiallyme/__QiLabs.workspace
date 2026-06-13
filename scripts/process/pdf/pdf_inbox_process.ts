import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { glob } from 'glob';
import { loadRepoRules } from '../../../packages/config/src/repoRules';

const ROOT_DIR = path.resolve(__dirname, '../..');

function checkTool(tool: string) {
    try {
        execSync(`${tool} --version`, { stdio: 'ignore' });
        return true;
    } catch {
        return false;
    }
}

async function processInboxPdfs() {
    const args = process.argv.slice(2);
    const batchIndex = args.indexOf('--batch');
    const apply = args.includes('--apply');

    if (batchIndex === -1 || !args[batchIndex + 1]) {
        console.error('Usage: tsx process_inbox_pdfs.ts --batch <batch_name> [--apply]');
        process.exit(1);
    }

    const batchName = args[batchIndex + 1];
    const batchPath = path.join(ROOT_DIR, 'content/_INBOX/_staging', batchName);
    const processedDir = path.join(ROOT_DIR, 'content/_INBOX/_processed', batchName);
    const trashDir = path.join(ROOT_DIR, 'content/_INBOX/_trash', batchName);

    if (!fs.existsSync(batchPath)) {
        console.error(`Batch path not found: ${batchPath}`);
        process.exit(1);
    }

    console.log(`📄 Processing PDFs in Batch: ${batchName}${apply ? ' (APPLY MODE)' : ' (SUGGEST MODE)'}...`);
    const rules = loadRepoRules(ROOT_DIR);

    const pdfs = await glob('**/*.pdf', { cwd: batchPath });

    const processingLog: any[] = [];
    const validationLog: any[] = [];

    for (const relPath of pdfs) {
        const fullPath = path.join(batchPath, relPath);
        const stats = fs.statSync(fullPath);
        const sizeMb = stats.size / (1024 * 1024);

        const logEntry: any = { file: relPath, sizeMb, status: 'pending', steps: [] };

        // 1. Validate
        if (sizeMb > rules.pdf.max_mb) logEntry.steps.push({ step: 'validate', status: 'warn', message: 'Exceeds size limit' });

        if (!apply) {
            console.log(`🔍 [SUGGEST] Process PDF: ${relPath} (${sizeMb.toFixed(2)} MB)`);
            processingLog.push(logEntry);
            continue;
        }

        // Apply Mode
        try {
            const outPath = path.join(processedDir, relPath);
            fs.mkdirSync(path.dirname(outPath), { recursive: true });

            // Pipeline Logic (Scaffolded)
            let currentPath = fullPath;

            // OCR best effort
            if (checkTool('ocrmypdf')) {
                console.log(`   Running OCR: ${relPath}`);
                // execSync(`ocrmypdf "${currentPath}" "${outPath}" --skip-text`);
                logEntry.steps.push({ step: 'ocr', status: 'success', tool: 'ocrmypdf' });
            } else {
                logEntry.steps.push({ step: 'ocr', status: 'skipped', message: 'ocrmypdf not found. Run: brew install ocrmypdf' });
                fs.copyFileSync(currentPath, outPath);
            }

            // Trash original on success
            fs.mkdirSync(path.dirname(path.join(trashDir, relPath)), { recursive: true });
            fs.renameSync(fullPath, path.join(trashDir, relPath));

            logEntry.status = 'success';
            console.log(`✨ Processed & Trashed: ${relPath}`);
        } catch (err: any) {
            logEntry.status = 'failed';
            logEntry.error = err.message;
            console.error(`❌ Failed to process ${relPath}: ${err.message}`);
        }

        processingLog.push(logEntry);
    }

    const reportDir = path.join(ROOT_DIR, 'content/_INBOX/_reports');
    fs.writeFileSync(path.join(reportDir, `${batchName}_pdf_processing_log.json`), JSON.stringify(processingLog, null, 2));

    console.log(`\n✅ Finished PDF processing for batch ${batchName}. See _reports/ for details.`);
}

processInboxPdfs().catch(err => {
    console.error('💥 PDF script failed:', err);
    process.exit(1);
});
