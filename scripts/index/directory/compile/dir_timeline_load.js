// Timeline Markdown File Loader
// This script reads .md files from the events/ folder and parses them

let timelineEvents = [];

// Parse YAML front matter from markdown
function parseFrontMatter(content) {
    const frontMatterRegex = /^---\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)$/;
    const match = content.match(frontMatterRegex);
    
    if (!match) {
        console.error('No front matter found in file');
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

// Load all events from markdown files
async function loadEventsFromMarkdown() {
    try {
        // Fetch the index file
        const indexResponse = await fetch('events/index.json');
        const fileList = await indexResponse.json();
        
        // Load each markdown file
        const promises = fileList.map(async (filename) => {
            try {
                const response = await fetch(`events/${filename}`);
                const content = await response.text();
                const parsed = parseFrontMatter(content);
                
                if (parsed) {
                    return {
                        id: filename.replace('.md', ''),
                        date: parsed.frontMatter.date,
                        title: parsed.frontMatter.title,
                        category: parsed.frontMatter.category,
                        critical: parsed.frontMatter.critical || false,
                        tags: parsed.frontMatter.tags || [],
                        description: parsed.content
                    };
                }
            } catch (error) {
                console.error(`Error loading ${filename}:`, error);
                return null;
            }
        });
        
        const results = await Promise.all(promises);
        timelineEvents = results.filter(event => event !== null);
        
        console.log(`Loaded ${timelineEvents.length} events from markdown files`);
        return timelineEvents;
        
    } catch (error) {
        console.error('Error loading timeline events:', error);
        return [];
    }
}

// Initialize - load events when page loads
async function initializeTimeline() {
    await loadEventsFromMarkdown();
    
    // Trigger custom event so the main script knows events are loaded
    window.dispatchEvent(new CustomEvent('timelineEventsLoaded', { 
        detail: { events: timelineEvents } 
    }));
}

// Start loading when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeTimeline);
} else {
    initializeTimeline();
}

