import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import { loadRepoRules } from '../../packages/config/src/repoRules';

const ROOT_DIR = path.resolve(__dirname, '../..');

async function fixRules() {
    console.log('🛠️  Fixing Repo Rules...');
    const rules = loadRepoRules(ROOT_DIR);
    let fixes = 0;

    const allFiles = await glob('**/*', {
        cwd: ROOT_DIR,
        ignore: rules.ignore_globs,
        nodir: true, // Only fixing files automatically
    });

    for (const relPath of allFiles) {
        const fullPath = path.join(ROOT_DIR, relPath);
        const dirName = path.dirname(fullPath);
        const baseName = path.basename(relPath);

        let newName = baseName;

        // 1. Replace spaces with underscores
        if (newName.includes(' ')) {
            newName = newName.replace(/\s+/g, '_');
        }

        // 2. Normalize date prefixes (e.g. 2026_02_03 -> 2026-02-03)
        const dateMatch = newName.match(/^(\d{4})[-_](\d{2})[-_](\d{2})([-_])(.*)/);
        if (dateMatch) {
            const y = dateMatch[1];
            const m = dateMatch[2];
            const d = dateMatch[3];
            const rest = dateMatch[5];
            newName = `${y}-${m}-${d}_${rest}`;
        }

        // 3. Lowercase normalization (if not purely alphanumeric)
        if (!/^[a-z0-9_.-]+$/.test(newName)) {
            // Only lowercase if it doesn't break everything - being conservative here
            // newName = newName.toLowerCase(); 
        }

        if (newName !== baseName) {
            const newPath = path.join(dirName, newName);
            if (fs.existsSync(newPath)) {
                console.warn(`⚠️  Cannot fix ${relPath}: ${newName} already exists.`);
                continue;
            }
            fs.renameSync(fullPath, newPath);
            console.log(`✨ Renamed: ${baseName} -> ${newName}`);
            fixes++;
        }
    }

    console.log(`\n✅ Applied ${fixes} fixes.`);
}

fixRules().catch(err => {
    console.error('💥 Fix script failed:', err);
    process.exit(1);
});
