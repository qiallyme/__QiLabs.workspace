const fs = require('fs');

// Read the JSON file
const conversations = JSON.parse(fs.readFileSync('conversations.json', 'utf8'));

// CSV headers matching gina_memory_rows.csv
const headers = ['id', 'user_id', 'role', 'content', 'app_context', 'tab_context', 'created_at'];

// Escape CSV content (handle quotes and newlines)
function escapeCSV(value) {
  if (value === null || value === undefined) {
    return '';
  }
  const str = String(value);
  // If contains comma, quote, or newline, wrap in quotes and escape quotes
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

// Format timestamp (convert Unix timestamp to ISO string if needed)
function formatTimestamp(timestamp) {
  if (!timestamp) return '';
  // If it's a Unix timestamp (number)
  if (typeof timestamp === 'number') {
    return new Date(timestamp * 1000).toISOString().replace('T', ' ').replace('Z', '+00');
  }
  // If it's already a string, return as is
  return String(timestamp);
}

// Extract messages from conversation mapping
function extractMessages(conversation) {
  const messages = [];
  const mapping = conversation.mapping || {};
  
  // Traverse the mapping to find all messages
  function traverse(nodeId, visited = new Set()) {
    if (visited.has(nodeId) || !mapping[nodeId]) return;
    visited.add(nodeId);
    
    const node = mapping[nodeId];
    if (node.message) {
      const msg = node.message;
      messages.push({
        id: msg.id || nodeId,
        user_id: conversation.owner?.id || conversation.owner || 'cody',
        role: msg.author?.role || (msg.author ? 'user' : 'assistant'),
        content: msg.content?.parts?.[0] || msg.content || '',
        app_context: conversation.title || '',
        tab_context: '',
        created_at: formatTimestamp(msg.create_time || conversation.create_time)
      });
    }
    
    // Traverse children
    if (node.children) {
      node.children.forEach(childId => traverse(childId, visited));
    }
  }
  
  // Start from root nodes
  Object.keys(mapping).forEach(nodeId => {
    const node = mapping[nodeId];
    if (!node.parent) {
      traverse(nodeId);
    }
  });
  
  return messages;
}

// Build CSV rows
const rows = [headers.join(',')];
let totalMessages = 0;

conversations.forEach(conversation => {
  const messages = extractMessages(conversation);
  messages.forEach(msg => {
    const row = [
      escapeCSV(msg.id),
      escapeCSV(msg.user_id),
      escapeCSV(msg.role),
      escapeCSV(msg.content),
      escapeCSV(msg.app_context),
      escapeCSV(msg.tab_context),
      escapeCSV(msg.created_at)
    ];
    rows.push(row.join(','));
    totalMessages++;
  });
});

// Write to CSV file
fs.writeFileSync('conversations.csv', rows.join('\n'));

console.log(`Converted ${conversations.length} conversations with ${totalMessages} total messages to conversations.csv`);

