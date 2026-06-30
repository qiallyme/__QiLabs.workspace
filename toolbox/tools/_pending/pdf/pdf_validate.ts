import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import { loadRepoRules } from '../../packages/config/src/repoRules';

const ROOT_DIR = path.resolve(__dirname, '../..');

async function validatePdfs() {
    console.log('📄 Validating PDF Assets...');
    const rules = loadRepoRules(ROOT_DIR);
    const issues: any[] = [];

    const pdfFiles = await glob(rules.pdf.scan_paths.map(p => path.join(p, '**/*.pdf')), {
        cwd: ROOT_DIR,
    });

    for (const relPath of pdfFiles) {
        const fullPath = path.join(ROOT_DIR, relPath);
        const stats = fs.statSync(fullPath);
        const sizeMb = stats.size / (1024 * 1024);

        // 1. Size Check
        if (sizeMb > rules.pdf.max_mb) {
            issues.push({
                path: relPath,
                type: 'PDF_MAX_SIZE',
                message: `Size (${sizeMb.toFixed(2)} MB) exceeds limit of ${rules.pdf.max_mb} MB.`
            });
        }

        // 2. OCR Detection (Basic Heuristic)
        // We look for common 'text' objects in the PDF binary
        const buffer = fs.readFileSync(fullPath);
        const content = buffer.toString('utf8', 0, 10000); // Check first 10KB
        const hasTextLayer = content.includes('Font') || content.includes('Type1') || content.includes('TrueType');

        if (!hasTextLayer && rules.pdf.require_ocr) {
            issues.push({
                path: relPath,
                type: 'PDF_REQUIRE_OCR',
                message: `Likely missing text layer (No fonts found in header).`
            });
        }
    }

    if (issues.length === 0) {
        console.log('✅ All PDFs meet quality standards.');
    } else {
        console.log(`\n❌ Found ${issues.length} PDF issues:\n`);
        issues.forEach(i => {
            console.log(`⚠️  [${i.type}] ${i.path}`);
            console.log(`   └─ ${i.message}`);
        });
    }
}

validatePdfs().catch(err => {
    console.error('💥 PDF validation failed:', err);
    process.exit(1);
});
