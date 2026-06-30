import fs from 'fs';
import path from 'path';

const ROOT_DIR = path.resolve(__dirname, '../..');

async function dedupDetect() {
    const args = process.argv.slice(2);
    const batchIndex = args.indexOf('--batch');

    if (batchIndex === -1 || !args[batchIndex + 1]) {
        console.error('Usage: tsx dedup_detect.ts --batch <batch_name>');
        process.exit(1);
    }

    const batchName = args[batchIndex + 1];
    const isRoot = batchName === '.' || batchName === './' || batchName === '';
    const reportName = isRoot ? 'ROOT_INBOX' : batchName;

    const manifestPath = path.join(ROOT_DIR, 'content/_INBOX/_staging', isRoot ? '' : batchName, 'manifest.json');

    if (!fs.existsSync(manifestPath)) {
        console.error(`Manifest not found. Run audit first: npm run inbox:audit -- --batch "${batchName}"`);
        process.exit(1);
    }

    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    const inventory = manifest.inventory || [];

    console.log(`👯 Detecting Duplicates in Batch: ${reportName}...`);

    const exactDuplicates: any[] = [];
    const seenHashes: Record<string, string[]> = {};

    inventory.forEach((item: any) => {
        if (!seenHashes[item.sha256]) {
            seenHashes[item.sha256] = [];
        }
        seenHashes[item.sha256].push(item.path);
    });

    for (const [hash, paths] of Object.entries(seenHashes)) {
        if (paths.length > 1) {
            exactDuplicates.push({ hash, paths });
        }
    }

    const reportDir = path.join(ROOT_DIR, 'content/_INBOX/_reports');
    fs.writeFileSync(path.join(reportDir, `${reportName}_duplicates_exact.json`), JSON.stringify(exactDuplicates, null, 2));
    fs.writeFileSync(path.join(reportDir, `${reportName}_duplicates_near.json`), JSON.stringify([], null, 2)); // Stub

    console.log(`✅ Detected ${exactDuplicates.length} exact duplicate groups.`);
}

dedupDetect().catch(err => {
    console.error('💥 Dedup script failed:', err);
    process.exit(1);
});
