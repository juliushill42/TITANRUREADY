/**
 * Genesis Key Generation Script
 * Generates 25 Genesis Keys for TitanU OS operators
 * 
 * Usage: node scripts/generate_genesis_keys.js
 */

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

// Configuration
const TOTAL_KEYS = 25;
const OUTPUT_DIR = path.join(__dirname, '..', 'titanu-os');
const CSV_FILE = path.join(OUTPUT_DIR, 'genesis_keys_master.csv');
const JSON_FILE = path.join(OUTPUT_DIR, 'genesis_keys_hashes.json');

// Pre-existing keys (001 and 002 - DO NOT CHANGE)
const EXISTING_KEYS = {
  '001': 'TITANU-GENESIS-001-CRWWPZ',
  '002': 'TITANU-GENESIS-002-YNBITT'
};

// Pre-assigned info for existing keys
const PRE_ASSIGNED = {
  '001': { status: 'Pre-assigned', assignedTo: 'You' },
  '002': { status: 'Pre-assigned', assignedTo: 'Partner' }
};

/**
 * Generate a cryptographically random 6-character alphanumeric code
 * @returns {string} 6-character uppercase alphanumeric code
 */
function generateRandomCode() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let code = '';
  const randomBytes = crypto.randomBytes(6);
  for (let i = 0; i < 6; i++) {
    code += chars[randomBytes[i] % chars.length];
  }
  return code;
}

/**
 * Generate a Genesis Key for a given operator number
 * @param {number} operatorNum - Operator number (1-25)
 * @returns {string} Genesis key in format TITANU-GENESIS-XXX-YYYYYY
 */
function generateGenesisKey(operatorNum) {
  const paddedNum = operatorNum.toString().padStart(3, '0');
  
  // Use existing keys for 001 and 002
  if (EXISTING_KEYS[paddedNum]) {
    return EXISTING_KEYS[paddedNum];
  }
  
  const randomCode = generateRandomCode();
  return `TITANU-GENESIS-${paddedNum}-${randomCode}`;
}

/**
 * Compute SHA-256 hash of a string
 * @param {string} text - Text to hash
 * @returns {string} Hex-encoded SHA-256 hash
 */
function computeHash(text) {
  return crypto.createHash('sha256').update(text).digest('hex');
}

/**
 * Get tier based on operator number
 * @param {number} operatorNum - Operator number
 * @returns {string} "VIP" for 1-10, "Early" for 11-25
 */
function getTier(operatorNum) {
  return operatorNum <= 10 ? 'VIP' : 'Early';
}

/**
 * Get current date in YYYY-MM-DD format
 * @returns {string} Current date
 */
function getCurrentDate() {
  return new Date().toISOString().split('T')[0];
}

/**
 * Main generation function
 */
function generateAllKeys() {
  console.log('='.repeat(60));
  console.log('TitanU OS Genesis Key Generator');
  console.log('='.repeat(60));
  console.log('');
  
  const keys = [];
  const hashes = {};
  const currentDate = getCurrentDate();
  
  // Generate all 25 keys
  for (let i = 1; i <= TOTAL_KEYS; i++) {
    const paddedNum = i.toString().padStart(3, '0');
    const key = generateGenesisKey(i);
    const hash = computeHash(key);
    const tier = getTier(i);
    
    // Determine status and assignment
    let status = 'Available';
    let assignedTo = '';
    let dateAssigned = '';
    
    if (PRE_ASSIGNED[paddedNum]) {
      status = PRE_ASSIGNED[paddedNum].status;
      assignedTo = PRE_ASSIGNED[paddedNum].assignedTo;
      dateAssigned = currentDate;
    }
    
    keys.push({
      operatorNumber: paddedNum,
      genesisKey: key,
      sha256Hash: hash,
      status: status,
      assignedTo: assignedTo,
      email: '',
      dateAssigned: dateAssigned,
      tier: tier
    });
    
    hashes[paddedNum] = hash;
    
    // Console output
    console.log(`${paddedNum}: ${key}`);
    console.log(`    Hash: ${hash}`);
    console.log(`    Tier: ${tier} | Status: ${status}${assignedTo ? ` | Assigned: ${assignedTo}` : ''}`);
    console.log('');
  }
  
  // Ensure output directory exists
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }
  
  // Generate CSV
  const csvHeader = 'Operator Number,Genesis Key,SHA256 Hash,Status,Assigned To,Email,Date Assigned,Tier';
  const csvRows = keys.map(k => 
    `${k.operatorNumber},${k.genesisKey},${k.sha256Hash},${k.status},${k.assignedTo},${k.email},${k.dateAssigned},${k.tier}`
  );
  const csvContent = [csvHeader, ...csvRows].join('\n');
  
  fs.writeFileSync(CSV_FILE, csvContent, 'utf8');
  console.log('='.repeat(60));
  console.log(`CSV file created: ${CSV_FILE}`);
  
  // Generate JSON hash registry
  fs.writeFileSync(JSON_FILE, JSON.stringify(hashes, null, 2), 'utf8');
  console.log(`JSON hash registry created: ${JSON_FILE}`);
  
  // Generate JavaScript code for VALID_KEY_HASHES
  console.log('');
  console.log('='.repeat(60));
  console.log('VALID_KEY_HASHES for genesisKey.js:');
  console.log('='.repeat(60));
  console.log('const VALID_KEY_HASHES = {');
  Object.entries(hashes).forEach(([num, hash]) => {
    console.log(`  '${num}': '${hash}',`);
  });
  console.log('};');
  
  // Generate copy-paste ready key list
  console.log('');
  console.log('='.repeat(60));
  console.log('COMPLETE KEY LIST (Copy-Paste Ready):');
  console.log('='.repeat(60));
  keys.forEach(k => {
    console.log(`${k.operatorNumber}: ${k.genesisKey} [${k.tier}]`);
  });
  
  console.log('');
  console.log('='.repeat(60));
  console.log('Generation complete!');
  console.log(`Total keys generated: ${TOTAL_KEYS}`);
  console.log(`VIP tier (001-010): 10 keys`);
  console.log(`Early tier (011-025): 15 keys`);
  console.log(`Pre-assigned: 2 keys (001, 002)`);
  console.log(`Available: ${TOTAL_KEYS - 2} keys`);
  console.log('='.repeat(60));
  
  return { keys, hashes };
}

// Run the generator
generateAllKeys();