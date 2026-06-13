#!/usr/bin/env node

/**
 * Build Timeline JSON from Markdown Files
 * 
 * This script reads all .md files from the events/ directory,
 * parses their YAML front matter, and generates a timeline.json file.
 * 
 * Usage: node build-timeline.js
 */

const fs = require('fs');
const path = require('path');

const EVENTS_DIR = path.join(__dirname, 'events');
const DIST_DIR = path.join(__dirname, 'dist');
const OUTPUT_FILE = path.join(DIST_DIR, 'timeline.json');

// Files to copy to dist
const FILES_TO_COPY = [
    'index.html',
    'styles.css',
    'script.js',
    'timeline-loader-json.js'
];

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
            const value = line.substring(colonIndex + 1).trim();
            
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
    console.log('🔨 Building timeline from markdown files...\n');
    
    // Create dist directory if it doesn't exist
    if (!fs.existsSync(DIST_DIR)) {
        fs.mkdirSync(DIST_DIR, { recursive: true });
        console.log('📁 Created dist/ directory\n');
    }
    
    // Copy necessary files to dist
    console.log('📋 Copying files to dist/...');
    FILES_TO_COPY.forEach(file => {
        const srcPath = path.join(__dirname, file);
        const destPath = path.join(DIST_DIR, file);
        if (fs.existsSync(srcPath)) {
            fs.copyFileSync(srcPath, destPath);
            console.log(`  ✓ ${file}`);
        } else {
            console.log(`  ⚠ ${file} not found, skipping`);
        }
    });
    console.log('');
    
    // Check if events directory exists
    if (!fs.existsSync(EVENTS_DIR)) {
        console.error('❌ Error: events/ directory not found!');
        process.exit(1);
    }
    
    // Read all markdown files
    const files = fs.readdirSync(EVENTS_DIR)
        .filter(file => file.endsWith('.md') && !file.startsWith('_'));
    
    console.log(`📂 Found ${files.length} markdown file(s)\n`);
    
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
                    critical: parsed.frontMatter.critical || false,
                    tags: parsed.frontMatter.tags || [],
                    description: parsed.content
                };
                
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
    
    events.forEach(event => {
        categories[event.category] = (categories[event.category] || 0) + 1;
    });
    
    console.log('📊 Statistics:');
    console.log(`   Critical events: ${criticalCount}`);
    console.log('   By category:');
    Object.keys(categories).sort().forEach(cat => {
        console.log(`     - ${cat}: ${categories[cat]}`);
    });
    console.log('');
}

// Run the build
try {
    buildTimeline();
} catch (error) {
    console.error('❌ Build failed:', error.message);
    process.exit(1);
}

