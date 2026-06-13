#!/usr/bin/env node

/**
 * Build Timeline for qially-me
 * 
 * This script:
 * 1. Builds QiTimeline (generates timeline.json and assets)
 * 2. Copies timeline assets to qially-me public directory
 * 3. Ensures timeline page can access the built assets
 */

import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const QITIMELINE_DIR = path.join(__dirname, '../../QiTimeline');
const QITIMELINE_DIST = path.join(QITIMELINE_DIR, 'dist');
const QIME_PUBLIC = path.join(__dirname, '../public');
const QIME_TIMELINE_DIR = path.join(QIME_PUBLIC, 'timeline');

// Check if QiTimeline exists
if (!fs.existsSync(QITIMELINE_DIR)) {
    console.warn('⚠️  QiTimeline directory not found at:', QITIMELINE_DIR);
    console.warn('⚠️  Skipping timeline build. Using existing timeline assets if available.');
    console.log('✅ Timeline build skipped (not critical)');
} else {
    console.log('🔄 Building QiTimeline...');
    
    // Step 1: Build QiTimeline
    try {
        process.chdir(QITIMELINE_DIR);
        execSync('node build-timeline.js', { stdio: 'inherit' });
        console.log('✅ QiTimeline built successfully');
    } catch (error) {
        console.error('❌ Failed to build QiTimeline:', error.message);
        console.warn('⚠️  Continuing build without timeline update...');
        // Don't exit - allow build to continue
    }
}

// Step 2: Ensure qially-me public/timeline directory exists
if (!fs.existsSync(QIME_PUBLIC)) {
    fs.mkdirSync(QIME_PUBLIC, { recursive: true });
}
if (!fs.existsSync(QIME_TIMELINE_DIR)) {
    fs.mkdirSync(QIME_TIMELINE_DIR, { recursive: true });
}

// Step 3: Copy timeline assets to qially-me public/timeline
const filesToCopy = [
    'timeline.json',
    'timeline-loader-json.js'
];

console.log('📦 Copying timeline assets to qially-me...');

filesToCopy.forEach(file => {
    const src = path.join(QITIMELINE_DIST, file);
    const dest = path.join(QIME_TIMELINE_DIR, file);
    
    if (fs.existsSync(src)) {
        fs.copyFileSync(src, dest);
        console.log(`  ✅ Copied ${file}`);
    } else {
        console.warn(`  ⚠️  File not found: ${src}`);
    }
});

// Step 4: Copy timeline CSS and JS (for embedding)
const assetsToCopy = [
    { src: path.join(QITIMELINE_DIR, 'styles.css'), dest: path.join(QIME_TIMELINE_DIR, 'timeline.css') },
    { src: path.join(QITIMELINE_DIR, 'script.js'), dest: path.join(QIME_TIMELINE_DIR, 'timeline.js') }
];

assetsToCopy.forEach(({ src, dest }) => {
    if (fs.existsSync(src)) {
        fs.copyFileSync(src, dest);
        console.log(`  ✅ Copied ${path.basename(src)} → ${path.basename(dest)}`);
    }
});

console.log('✅ Timeline assets ready for qially-me!');
console.log(`   Location: ${QIME_TIMELINE_DIR}`);

