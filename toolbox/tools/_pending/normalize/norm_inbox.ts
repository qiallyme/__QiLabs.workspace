import fs from 'fs';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';

const ROOT_DIR = path.resolve(__dirname, '../..');

async function normalizeInbox() {
    const args = process.argv.slice(2);
    const batchIndex = args.indexOf('--batch');
    const apply = args.includes('--apply');

    if (batchIndex === -1 || !args[batchIndex + 1]) {
        console.error('Usage: tsx normalize_inbox.ts --batch <batch_name> [--apply]');
        process.exit(1);
    }

    const batchName = args[batchIndex + 1];
    const isRoot = batchName === '.' || batchName === './' || batchName === '';
    const reportName = isRoot ? 'ROOT_INBOX' : batchName;

    const mergePlanPath = path.join(ROOT_DIR, 'content/_INBOX/_reports', `${reportName}_merge_plan.json`);
    const batchStagingPath = path.join(ROOT_DIR, 'content/_INBOX/_staging', isRoot ? '' : batchName);
    const processedDirPath = path.join(ROOT_DIR, 'content/_INBOX/_processed', reportName, 'objects');

    if (!fs.existsSync(mergePlanPath)) {
        console.error(`Merge plan not found for ${reportName}. Run merge-plan first.`);
        process.exit(1);
    }

    const mergePlan = JSON.parse(fs.readFileSync(mergePlanPath, 'utf8'));
    console.log(`📦 Normalizing Batch: ${reportName}${apply ? ' (APPLY MODE)' : ' (SUGGEST MODE)'}...`);

    const log: any[] = [];

    for (const obj of mergePlan) {
        const objSlug = obj.object_name.toLowerCase().replace(/[^a-z0-9]/g, '_');
        const objDir = path.join(processedDirPath, objSlug);

        const frontMatter = {
            dna_id: uuidv4(),
            canonical_name: obj.object_name,
            title: obj.object_name,
            type: obj.primary_asset.type,
            module: 'inbox',
            visibility: 'internal',
            status: 'draft',
            created: new Date().toISOString().split('T')[0],
            updated: new Date().toISOString().split('T')[0],
        };

        if (apply) {
            fs.mkdirSync(path.join(objDir, 'assets'), { recursive: true });

            // Create index.md
            const fmContent = `---\n${Object.entries(frontMatter).map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join('\n')}\n---\n\n# ${obj.object_name}\n`;
            fs.writeFileSync(path.join(objDir, 'index.md'), fmContent);

            // Copy assets (if they still exist in staging, or look in processed if PDF was moved)
            obj.attachments.forEach((file: any) => {
                const source = path.join(batchStagingPath, file.path);
                if (fs.existsSync(source)) {
                    fs.copyFileSync(source, path.join(objDir, 'assets', path.basename(file.path)));
                }
            });

            console.log(`✨ Created Object: ${objSlug}`);
        } else {
            console.log(`🔍 [SUGGEST] New Object: ${objSlug} (DNA: ${frontMatter.dna_id})`);
        }

        log.push({ slug: objSlug, frontMatter });
    }

    const reportDir = path.join(ROOT_DIR, 'content/_INBOX/_reports');
    fs.writeFileSync(path.join(reportDir, `${reportName}_normalize_log.json`), JSON.stringify(log, null, 2));

    console.log(`\n✅ Finished normalization for batch ${reportName}.`);
}

normalizeInbox().catch(err => {
    console.error('💥 Normalization script failed:', err);
    process.exit(1);
});
