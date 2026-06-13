import fs from 'fs';
import path from 'path';

const ROOT_DIR = path.resolve(__dirname, '../..');

async function createMergePlan() {
    const args = process.argv.slice(2);
    const batchIndex = args.indexOf('--batch');

    if (batchIndex === -1 || !args[batchIndex + 1]) {
        console.error('Usage: tsx merge_plan.ts --batch <batch_name>');
        process.exit(1);
    }

    const batchName = args[batchIndex + 1];
    const isRoot = batchName === '.' || batchName === './' || batchName === '';
    const reportName = isRoot ? 'ROOT_INBOX' : batchName;

    const manifestPath = path.join(ROOT_DIR, 'content/_INBOX/_staging', isRoot ? '' : batchName, 'manifest.json');

    if (!fs.existsSync(manifestPath)) {
        console.error(`Manifest not found for ${reportName}. Run audit first.`);
        process.exit(1);
    }

    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    const inventory = manifest.inventory || [];

    console.log(`🗺️  Generating Merge Plan for Batch: ${reportName}...`);

    // Grouping by basename similarity (crude heuristic)
    const objects: Record<string, any[]> = {};

    inventory.forEach((item: any) => {
        const ext = path.extname(item.path);
        const nameWithoutExt = path.basename(item.path, ext);
        // Simple grouping: files sharing the same base name (ignoring dates/versions best effort)
        const coreName = nameWithoutExt.replace(/^\d{4}-\d{2}-\d{2}_/, '').replace(/_v\d+$/, '');

        if (!objects[coreName]) objects[coreName] = [];
        objects[coreName].push(item);
    });

    const mergePlan = Object.entries(objects).map(([name, files]) => ({
        object_name: name,
        primary_asset: files.find(f => f.ext === '.pdf') || files[0],
        attachments: files,
    }));

    const reportDir = path.join(ROOT_DIR, 'content/_INBOX/_reports');
    fs.writeFileSync(path.join(reportDir, `${reportName}_merge_plan.json`), JSON.stringify(mergePlan, null, 2));

    console.log(`✅ Merge plan created with ${mergePlan.length} suggested objects.`);
}

createMergePlan().catch(err => {
    console.error('💥 Merge plan script failed:', err);
    process.exit(1);
});
