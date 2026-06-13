#!/usr/bin/env node

/**
 * Build Timeline JSON from Markdown Files
 * 
 * This script reads timeline events from the QsKb source location,
 * parses their YAML front matter, and generates a timeline.json file
 * in the public directory for the React app to consume.
 * 
 * Source: 2_QsKb/2.30_LIFE/2.30.10_QiTimeline/events/
 * Output: public/timeline.json
 * 
 * Usage: node scripts/build-timeline.js
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Paths - Calculate relative to QiOne root
// Script is at: 5_Apps/5.30_live/QiSite/qially-me/subs/713.qially.me/scripts/build-timeline.js
// Need to go to: 2_QsKb/2.30_LIFE/2.30.10_QiTimeline/entries/
// Go up 7 levels from scripts/ to reach QiOne root
let currentDir = __dirname;
for (let i = 0; i < 7; i++) {
    currentDir = path.dirname(currentDir);
}
const QIONE_ROOT = currentDir;

const QSKB_ROOT = path.join(QIONE_ROOT, '2_QsKb', '2.30_LIFE', '2.30.10_QiTimeline');
const EVENTS_DIR = path.join(QSKB_ROOT, 'entries');
const PUBLIC_DIR = path.join(__dirname, '../public');
const OUTPUT_FILE = path.join(PUBLIC_DIR, 'timeline.json');

// Life Stages Configuration
const LIFE_STAGES = {
    'birth-infancy': { label: 'Birth & Infancy', order: 1 },
    'early-childhood': { label: 'Early Childhood', order: 2 },
    'elementary-years': { label: 'Elementary Years', order: 3 },
    'adolescence': { label: 'Adolescence', order: 4 },
    'early-adulthood': { label: 'Early Adulthood', order: 5 },
    'young-professional': { label: 'Young Professional', order: 6 },
    'established-career': { label: 'Established Career', order: 7 },
    'prime-years': { label: 'Prime Years', order: 8 },
    'retirement-legacy': { label: 'Retirement & Legacy', order: 9 }
};

// Parse YAML front matter from markdown content
function parseFrontMatter(content) {
    const frontMatterRegex = /^---\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)$/;
    const match = content.match(frontMatterRegex);
    
    if (!match) {
        return null;
    }
    
    const frontMatter = match[1];
    const body = match[2].trim();
    
    // Parse YAML (simple parser for our use case)
    const data = {};
    const lines = frontMatter.split('\n');
    let currentKey = null;
    let currentArray = null;
    
    lines.forEach(line => {
        line = line.trim();
        if (!line) return;
        
        // Check for array items
        if (line.startsWith('- ')) {
            if (currentArray) {
                currentArray.push(line.substring(2).trim());
            }
            return;
        }
        
        // Check for key-value pairs
        const colonIndex = line.indexOf(':');
        if (colonIndex > -1) {
            const key = line.substring(0, colonIndex).trim();
            let value = line.substring(colonIndex + 1).trim();
            
            // Remove quotes if present
            if ((value.startsWith('"') && value.endsWith('"')) ||
                (value.startsWith("'") && value.endsWith("'"))) {
                value = value.slice(1, -1);
            }
            
            if (value === '') {
                // This is an array key
                currentKey = key;
                currentArray = [];
                data[key] = currentArray;
            } else {
                // Regular key-value
                currentKey = null;
                currentArray = null;
                
                // Parse boolean
                if (value === 'true') {
                    data[key] = true;
                } else if (value === 'false') {
                    data[key] = false;
                } else {
                    data[key] = value;
                }
            }
        }
    });
    
    return {
        frontMatter: data,
        content: body
    };
}

// Main build function
function buildTimeline() {
    console.log('🔨 Building timeline from QsKb source...\n');
    
    // Check if source directory exists
    if (!fs.existsSync(EVENTS_DIR)) {
        console.error(`❌ Error: Source directory not found: ${EVENTS_DIR}`);
        console.error('   Make sure the QsKb path is correct.');
        process.exit(1);
    }
    
    // Create public directory if it doesn't exist
    if (!fs.existsSync(PUBLIC_DIR)) {
        fs.mkdirSync(PUBLIC_DIR, { recursive: true });
        console.log('📁 Created public/ directory\n');
    }
    
    // Read all markdown files
    const files = fs.readdirSync(EVENTS_DIR)
        .filter(file => file.endsWith('.md') && !file.startsWith('_'));
    
    console.log(`📂 Found ${files.length} markdown file(s) in source\n`);
    
    // Parse each file
    const events = [];
    let successCount = 0;
    let errorCount = 0;
    
    files.forEach(filename => {
        try {
            const filePath = path.join(EVENTS_DIR, filename);
            const content = fs.readFileSync(filePath, 'utf8');
            const parsed = parseFrontMatter(content);
            
            if (parsed) {
                const event = {
                    id: filename.replace('.md', ''),
                    date: parsed.frontMatter.date,
                    title: parsed.frontMatter.title,
                    category: parsed.frontMatter.category,
                    life_stage: parsed.frontMatter.life_stage || null,
                    critical: parsed.frontMatter.critical || false,
                    tags: parsed.frontMatter.tags || [],
                    description: parsed.content,
                    slug: parsed.frontMatter.slug || filename.replace('.md', '').toLowerCase().replace(/\s+/g, '-')
                };
                
                // Validate required fields
                if (!event.date || !event.title || !event.category) {
                    console.log(`  ⚠ ${filename} - Missing required fields (date, title, or category)`);
                    errorCount++;
                    return;
                }
                
                events.push(event);
                console.log(`  ✓ ${filename}`);
                successCount++;
            } else {
                console.log(`  ✗ ${filename} - Invalid front matter`);
                errorCount++;
            }
        } catch (error) {
            console.log(`  ✗ ${filename} - ${error.message}`);
            errorCount++;
        }
    });
    
    // Sort events by date (newest first)
    events.sort((a, b) => new Date(b.date) - new Date(a.date));
    
    // Add life stage labels
    events.forEach(event => {
        if (event.life_stage && LIFE_STAGES[event.life_stage]) {
            event.life_stage_label = LIFE_STAGES[event.life_stage].label;
            event.life_stage_order = LIFE_STAGES[event.life_stage].order;
        }
    });
    
    // Write JSON file
    fs.writeFileSync(OUTPUT_FILE, JSON.stringify(events, null, 2), 'utf8');
    
    console.log('\n' + '='.repeat(50));
    console.log(`✅ Successfully built timeline.json`);
    console.log(`   Total events: ${events.length}`);
    console.log(`   Success: ${successCount}`);
    if (errorCount > 0) {
        console.log(`   Errors: ${errorCount}`);
    }
    console.log(`   Output: ${OUTPUT_FILE}`);
    console.log('='.repeat(50) + '\n');
    
    // Print statistics
    const categories = {};
    const criticalCount = events.filter(e => e.critical).length;
    const lifeStages = {};
    
    events.forEach(event => {
        categories[event.category] = (categories[event.category] || 0) + 1;
        if (event.life_stage) {
            lifeStages[event.life_stage] = (lifeStages[event.life_stage] || 0) + 1;
        }
    });
    
    console.log('📊 Statistics:');
    console.log(`   Critical events: ${criticalCount}`);
    console.log('   By category:');
    Object.keys(categories).sort().forEach(cat => {
        console.log(`     - ${cat}: ${categories[cat]}`);
    });
    if (Object.keys(lifeStages).length > 0) {
        console.log('   By life stage:');
        Object.keys(lifeStages).sort((a, b) => 
            LIFE_STAGES[a]?.order - LIFE_STAGES[b]?.order
        ).forEach(stage => {
            console.log(`     - ${LIFE_STAGES[stage].label}: ${lifeStages[stage]}`);
        });
    }
    console.log('');
}

// Run the build
try {
    buildTimeline();
} catch (error) {
    console.error('❌ Build failed:', error.message);
    process.exit(1);
}

