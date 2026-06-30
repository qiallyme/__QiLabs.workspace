import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import matter from 'gray-matter';
import { v4 as uuidv4 } from 'uuid';
import crypto from 'crypto';
import * as dotenv from 'dotenv';
import { createClient } from '@supabase/supabase-js';

// Load environment variables
dotenv.config();

const ROOT_DIR = path.resolve(__dirname, '../..');
const INDEX_DIR = path.join(ROOT_DIR, 'content/.index');
const INDEX_FILE = path.join(INDEX_DIR, 'content_index.json');
const LOG_FILE = path.join(ROOT_DIR, 'logs/scripts.log');

function logAction(action: string, targetPath: string, details: string = '') {
    const timestamp = new Date().toISOString();
    const entry = `[${timestamp}] [INDEXER] ${action.padEnd(10)} | ${targetPath} ${details}\n`;
    const logDir = path.dirname(LOG_FILE);
    if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
    fs.appendFileSync(LOG_FILE, entry);
}

// Configuration for mapping paths to modules/visibility
const PATH_CONFIG = [
    { pattern: 'content/Vault-Public/QSaysIt-Blog', module: 'qsaysit', visibility: 'public', type: 'blog' },
    { pattern: 'content/Vault-Public/QSaysIt-Docs', module: 'qsaysit', visibility: 'public', type: 'doc' },
    { pattern: 'apps/private/qivault-docs', module: 'qivault-docs', visibility: 'private', type: 'doc' },
    { pattern: 'apps/internal/care-portal', module: 'care-portal', visibility: 'internal', type: 'kb' },
    { pattern: 'apps/internal/qially-me', module: 'qially', visibility: 'internal', type: 'blog' },
];

const EXEMPT_FILES = ['README.md', 'TODO.md', 'MIGRATION_PLAN.md'];

function getTodayISO() {
    return new Date().toISOString().split('T')[0];
}

function computeHash(content: string) {
    return crypto.createHash('sha256').update(content).digest('hex');
}

function inferCanonicalName(filePath: string, body: string) {
    // 1. Prefer H1
    const h1Match = body.match(/^#\s+(.+)$/m);
    if (h1Match) return h1Match[1].trim();

    // 2. Nearest directory name
    const dirName = path.basename(path.dirname(filePath));
    return dirName.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

async function indexContent() {
    console.log('🏗️ Starting Content Indexing...');
    logAction('START', 'indexing', 'Global sweep initiated');

    const files = await glob(['content/**/*.{md,mdx}', 'apps/**/src/content/**/*.{md,mdx}'], {
        cwd: ROOT_DIR,
        ignore: ['**/node_modules/**', '**/.next/**', '**/dist/**'],
    });

    const indexData: any[] = [];
    const today = getTodayISO();

    for (const relPath of files) {
        const fileName = path.basename(relPath);
        if (EXEMPT_FILES.includes(fileName)) continue;

        const fullPath = path.join(ROOT_DIR, relPath);
        const fileSource = fs.readFileSync(fullPath, 'utf8');
        const { data: existingFm, content: body } = matter(fileSource);

        let hasChanged = false;
        const fm = { ...existingFm };

        // 1. DNA ID
        if (!fm.dna_id) {
            fm.dna_id = uuidv4();
            hasChanged = true;
        }

        // 2. Canonical Name
        if (!fm.canonical_name) {
            fm.canonical_name = inferCanonicalName(fullPath, body);
            hasChanged = true;
        }

        // 3. Title
        if (!fm.title) {
            fm.title = fm.canonical_name;
            hasChanged = true;
        }

        // 4. Path-based inferrence
        const config = PATH_CONFIG.find(c => relPath.replace(/\\/g, '/').includes(c.pattern));
        if (config) {
            if (!fm.module) { fm.module = config.module; hasChanged = true; }
            if (!fm.visibility) { fm.visibility = config.visibility; hasChanged = true; }
            if (!fm.type) { fm.type = config.type; hasChanged = true; }
        }

        // 5. Defaults & Date Normalization
        const formatDate = (d: any) => {
            if (!d) return today;
            if (d instanceof Date) return d.toISOString().split('T')[0];
            if (typeof d === 'string') return d.split('T')[0];
            return today;
        };

        const createdBefore = fm.created;
        const updatedBefore = fm.updated;
        fm.created = formatDate(fm.created);
        fm.updated = formatDate(fm.updated);

        if (fm.created !== createdBefore || fm.updated !== updatedBefore) hasChanged = true;

        if (!fm.status) { fm.status = 'draft'; hasChanged = true; }
        if (!fm.tags) { fm.tags = []; hasChanged = true; }
        if (!fm.version) { fm.version = 1; hasChanged = true; }

        if (hasChanged) {
            fm.updated = today;
            const newFileContent = matter.stringify(body, fm);
            fs.writeFileSync(fullPath, newFileContent);
            console.log(`✨ Healed: ${relPath}`);
            logAction('HEALED', relPath, `DNA: ${fm.dna_id}`);
        }

        indexData.push({
            ...fm,
            source_path: relPath,
            content_hash: computeHash(body),
        });
    }

    // Write local index
    if (!fs.existsSync(INDEX_DIR)) fs.mkdirSync(INDEX_DIR, { recursive: true });
    fs.writeFileSync(INDEX_FILE, JSON.stringify(indexData, null, 2));
    console.log(`✅ Local index written to ${INDEX_FILE}`);

    // Optional Supabase Sync
    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (supabaseUrl && supabaseKey) {
        console.log('☁️ Syncing to Supabase...');
        const supabase = createClient(supabaseUrl, supabaseKey);

        for (const record of indexData) {
            const { error } = await supabase
                .from('content_index')
                .upsert({
                    dna_id: record.dna_id,
                    canonical_name: record.canonical_name,
                    module: record.module,
                    type: record.type,
                    title: record.title,
                    slug: record.slug || null,
                    visibility: record.visibility,
                    status: record.status,
                    tags: record.tags,
                    version: record.version,
                    source_path: record.source_path,
                    content_hash: record.content_hash,
                    indexed_at: new Date().toISOString()
                }, { onConflict: 'dna_id' });

            if (error) {
                console.error(`❌ Error syncing ${record.dna_id}:`, error.message);
                logAction('SYNC_ERR', record.source_path, error.message);
            } else {
                logAction('SYNCED', record.source_path, `DNA: ${record.dna_id}`);
            }
        }
        console.log('✅ Supabase sync complete.');
    } else {
        console.log('⏩ Skipping Supabase sync (env vars missing).');
    }
}

indexContent().catch(err => {
    console.error('💥 Indexing failed:', err);
    process.exit(1);
});
