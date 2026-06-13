import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import { loadRepoRules } from '../../packages/config/src/repoRules';
import { RulesRegistry } from '../../packages/config/src/rulesRegistry';

const ROOT_DIR = path.resolve(__dirname, '../..');

async function auditRepo() {
    console.log('🔍 Auditing Monorepo Rules...');
    const rules = loadRepoRules(ROOT_DIR);
    const issues: any[] = [];

    const allFiles = await glob('**/*', {
        cwd: ROOT_DIR,
        ignore: rules.ignore_globs,
        nodir: false,
    });

    for (const relPath of allFiles) {
        const fullPath = path.join(ROOT_DIR, relPath);
        const stats = fs.statSync(fullPath);
        const isDir = stats.isDirectory();
        const baseName = path.basename(relPath);

        if (isDir) {
            // Skip root layer folders as per user instruction
            if (!relPath.includes('/') && !relPath.includes('\\')) continue;

            // Folder Rules
            const folderRegex = new RegExp(rules.foldername.allowed_regex);
            const isValid = folderRegex.test(baseName);
            const hasOverride = rules.foldername.overrides.find(o => {
                const cleanPattern = o.pattern.replace(/\*\*/g, '').replace(/\//g, '');
                return baseName.toLowerCase() === cleanPattern.toLowerCase();
            });

            if (!isValid && !hasOverride) {
                issues.push({
                    path: relPath,
                    rule: RulesRegistry.NAMING_FOLDER_CAPITALIZED,
                    message: `Folder '${baseName}' does not match ${rules.foldername.capitalization} format.`
                });
            }
        } else {
            // File Rules
            const ext = path.extname(baseName);
            const nameWithoutExt = path.basename(baseName, ext);

            // 1. No Spaces
            if (baseName.includes(' ')) {
                issues.push({
                    path: relPath,
                    rule: RulesRegistry.FILE_NO_SPACES,
                    message: `File '${baseName}' contains spaces.`
                });
            }

            // 2. Lowercase Alphanum
            if (!/^[a-z0-9_.-]+$/.test(baseName)) {
                issues.push({
                    path: relPath,
                    rule: RulesRegistry.FILE_LOWERCASE_ALPHANUM,
                    message: `File '${baseName}' has invalid characters (must be lowercase, _, -).`
                });
            }

            // 3. Length Limit
            if (nameWithoutExt.length > rules.filename.max_base_len) {
                issues.push({
                    path: relPath,
                    rule: RulesRegistry.FILE_LENGTH_LIMIT,
                    message: `Filename '${nameWithoutExt}' is too long (${nameWithoutExt.length} > ${rules.filename.max_base_len}).`
                });
            }

            // 4. Date Prefix for Content
            if (relPath.startsWith('content')) {
                const dateMatch = nameWithoutExt.match(/^(\d{4})[-_](\d{2})[-_](\d{2})/);
                if (dateMatch) {
                    const formatted = `${dateMatch[1]}-${dateMatch[2]}-${dateMatch[3]}`;
                    if (!nameWithoutExt.startsWith(formatted + '_')) {
                        issues.push({
                            path: relPath,
                            rule: RulesRegistry.DATE_PREFIX_FORMAT,
                            message: `File '${baseName}' should use '${formatted}_' prefix.`
                        });
                    }
                } else if (rules.dates.content_prefix_required && !baseName.startsWith('index')) {
                    // Only warn if prefix is missing entirely and it's not an index file
                    // issues.push({ path: relPath, rule: RulesRegistry.DATE_PREFIX_FORMAT, message: 'Missing date prefix.'});
                }
            }
        }
    }

    // Report
    if (issues.length === 0) {
        console.log('✅ All rules passed!');
    } else {
        console.log(`\n❌ Found ${issues.length} issues:\n`);
        issues.forEach(i => {
            const label = i.rule.severity === 'error' ? '❌' : '⚠️';
            console.log(`${label} [${i.rule.id}] ${i.path}`);
            console.log(`   └─ ${i.message}`);
        });

        const errors = issues.filter(i => i.rule.severity === 'error');
        if (errors.length > 0) process.exit(1);
    }
}

auditRepo().catch(err => {
    console.error('💥 Audit failed:', err);
    process.exit(1);
});
