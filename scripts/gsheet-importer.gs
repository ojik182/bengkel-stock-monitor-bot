/**
 * Google Apps Script - CSV Import untuk Bengkel Stock Monitor
 * 
 * CARA PENGGUNAAN:
 * 1. Buka Google Sheets "Bengkel Stock Monitor"
 * 2. Buka Extensions > Apps Script
 * 3. Hapus semua kode default, paste seluruh kode ini
 * 4. Save project (Ctrl+S)
 * 5. Buat trigger: Edit > Triggers > Add Trigger > importFromCSV (time-driven, every hour)
 * 6. Untuk import manual: Run > importFromCSV
 * 
 * FORMAT CSV YANG DITERIMA:
 * - Header harus sesuai dengan export dari sistem internal
 * - Kolom lokasi: "Physical Locations / DXK / Stock" atau "Physical Locations / DXK / Stock / DXK-POSSV02 POS Service Sandai"
 * - Angka Indonesia: 123.456,78 (titik = ribuan, koma = desimal)
 */

const SHEET_ID = 'YOUR_SPREADSHEET_ID_HERE'; // Ganti dengan spreadsheet ID kamu

// Nama sheet
const SHEETS = {
  PARTS: 'Parts',
  LOCATIONS: 'Locations',
  INVENTORY: 'Inventory',
  TRANSACTIONS: 'Transactions'
};

// Mapping lokasi
const LOCATION_MAPPING = {
  'Physical Locations / DXK / Stock': 'DXK-UTAMA',
  'Physical Locations / DXK / Stock / DXK-POSSV02 POS Service Sandai': 'DXK-SANDAI'
};

/**
 * Parse angka format Indonesia ke float
 * Contoh: "19.087.395,42" -> 19087395.42
 */
function parseIndonesianNumber(value) {
  if (!value || value === '') return 0;
  
  // Hapus semua titik (separator ribuan)
  let cleaned = value.toString().replace(/\./g, '');
  
  // Ganti koma dengan titik untuk desimal
  cleaned = cleaned.replace(',', '.');
  
  // Parse dan bulatkan ke 2 desimal
  const parsed = parseFloat(cleaned);
  return isNaN(parsed) ? 0 : Math.round(parsed * 100) / 100;
}

/**
 * Generate UUID sederhana
 */
function generateId() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Main function untuk import CSV
 * Dipanggil manual atau oleh trigger
 */
function importFromCSV() {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  
  // Dapatkan sheet
  const partsSheet = ss.getSheetByName(SHEETS.PARTS);
  const locationsSheet = ss.getSheetByName(SHEETS.LOCATIONS);
  const inventorySheet = ss.getSheetByName(SHEETS.INVENTORY);
  
  // Clear existing data (kecuali header)
  if (partsSheet.getLastRow() > 1) partsSheet.getRange(2, 1, partsSheet.getLastRow() - 1, partsSheet.getMaxColumns()).clearContent();
  if (locationsSheet.getLastRow() > 1) locationsSheet.getRange(2, 1, locationsSheet.getLastRow() - 1, locationsSheet.getMaxColumns()).clearContent();
  if (inventorySheet.getLastRow() > 1) inventorySheet.getRange(2, 1, inventorySheet.getLastRow() - 1, inventorySheet.getMaxColumns()).clearContent();
  
  // Setup headers
  setupHeaders(ss);
  
  // Parse CSV dari file yang diupload
  const csvContent = getCSVContent();
  if (!csvContent) {
    Logger.log('No CSV file found. Please upload a CSV file first.');
    return;
  }
  
  const rows = parseCSVRows(csvContent);
  
  // Proses setiap baris
  const partsMap = new Map();
  const locationsSet = new Set();
  const inventoryData = [];
  
  rows.forEach((row, index) => {
    try {
      const locationKey = row['Lokasi'];
      const locationId = LOCATION_MAPPING[locationKey] || detectLocation(locationKey);
      const partNumber = row['Kode Product'];
      const category = row['Kategori'];
      const name = row['Nama Barang'];
      const unitPrice = parseIndonesianNumber(row['Harga Satuan']);
      const qtyAvailable = parseIndonesianNumber(row['Quantity Available']);
      const ranking = row['Rangking part'] || 'E';
      
      // Collect unique locations
      if (locationId) {
        locationsSet.add(locationId);
      }
      
      // Collect parts (deduplicate by part_number)
      if (partNumber && !partsMap.has(partNumber)) {
        partsMap.set(partNumber, {
          part_id: generateId(),
          part_number: partNumber,
          name: name,
          category: category,
          unit_price: unitPrice,
          ranking: ranking
        });
      }
      
      // Collect inventory
      if (partNumber && locationId) {
        const part = partsMap.get(partNumber);
        inventoryData.push({
          location_id: locationId,
          part_id: part.part_id,
          qty_available: qtyAvailable,
          last_updated: new Date().toISOString()
        });
      }
    } catch (e) {
      Logger.log(`Error processing row ${index + 1}: ${e}`);
    }
  });
  
  // Write to Sheets
  writeParts(ss, Array.from(partsMap.values()));
  writeLocations(ss, Array.from(locationsSet));
  writeInventory(ss, inventoryData);
  
  Logger.log(`Import complete: ${partsMap.size} parts, ${locationsSet.size} locations, ${inventoryData.length} inventory records`);
}

/**
 * Setup header rows
 */
function setupHeaders(ss) {
  // Parts headers
  const partsSheet = ss.getSheetByName(SHEETS.PARTS);
  if (!partsSheet) {
    ss.insertSheet(SHEETS.PARTS);
  }
  partsSheet.getRange(1, 1, 1, 6).setValues([['part_id', 'part_number', 'name', 'category', 'unit_price', 'ranking']]);
  
  // Locations headers
  const locationsSheet = ss.getSheetByName(SHEETS.LOCATIONS);
  if (!locationsSheet) {
    ss.insertSheet(SHEETS.LOCATIONS);
  }
  locationsSheet.getRange(1, 1, 1, 4).setValues([['location_id', 'branch_code', 'name', 'profit_center']]);
  
  // Inventory headers
  const inventorySheet = ss.getSheetByName(SHEETS.INVENTORY);
  if (!inventorySheet) {
    ss.insertSheet(SHEETS.INVENTORY);
  }
  inventorySheet.getRange(1, 1, 1, 5).setValues([['id', 'location_id', 'part_id', 'qty_available', 'last_updated']]);
  
  // Transactions headers
  const transSheet = ss.getSheetByName(SHEETS.TRANSACTIONS);
  if (!transSheet) {
    ss.insertSheet(SHEETS.TRANSACTIONS);
  }
  transSheet.getRange(1, 1, 1, 8).setValues([['id', 'date', 'location_id', 'part_id', 'type', 'qty', 'user', 'notes']]);
}

/**
 * Deteksi lokasi dari path
 */
function detectLocation(locationPath) {
  if (!locationPath) return null;
  
  if (locationPath.includes('POSSV02') || locationPath.includes('Service Sandai')) {
    return 'DXK-SANDAI';
  }
  
  // Extract branch code dari path
  const match = locationPath.match(/Physical Locations \/ ([A-Z]+) \/ Stock/);
  if (match) {
    return match[1] + '-UTAMA';
  }
  
  return null;
}

/**
 * Dapatkan konten CSV dari file yang diupload
 */
function getCSVContent() {
  // Cek folder yang ditentukan untuk file CSV
  const folder = DriveApp.getFoldersByName('BengkelImport').next();
  const files = folder.getFilesByType(MimeType.CSV);
  
  if (!files.hasNext()) {
    return null;
  }
  
  const file = files.next();
  return file.getBlob().getDataAsString();
}

/**
 * Parse CSV content ke array of objects
 */
function parseCSVRows(csvContent) {
  const lines = csvContent.split(/\r?\n/);
  const headers = parseCSVLine(lines[0]);
  const rows = [];
  
  for (let i = 1; i < lines.length; i++) {
    if (!lines[i].trim()) continue;
    
    const values = parseCSVLine(lines[i]);
    const row = {};
    
    headers.forEach((header, index) => {
      row[header.trim()] = values[index] || '';
    });
    
    rows.push(row);
  }
  
  return rows;
}

/**
 * Parse satu baris CSV (handle quoted values)
 */
function parseCSVLine(line) {
  const result = [];
  let current = '';
  let inQuotes = false;
  
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ';' && !inQuotes) {
      result.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  
  result.push(current.trim());
  return result;
}

/**
 * Write parts data to sheet
 */
function writeParts(ss, parts) {
  const sheet = ss.getSheetByName(SHEETS.PARTS);
  const values = parts.map(p => [p.part_id, p.part_number, p.name, p.category, p.unit_price, p.ranking]);
  
  if (values.length > 0) {
    sheet.getRange(2, 1, values.length, 6).setValues(values);
  }
}

/**
 * Write locations data to sheet
 */
function writeLocations(ss, locationIds) {
  const sheet = ss.getSheetByName(SHEETS.LOCATIONS);
  const locationData = getLocationDetails();
  
  const values = locationIds.map(id => {
    const detail = locationData[id] || {};
    return [id, id.split('-')[0], detail.name || id, detail.profit_center || ''];
  });
  
  if (values.length > 0) {
    sheet.getRange(2, 1, values.length, 4).setValues(values);
  }
}

/**
 * Location details
 */
function getLocationDetails() {
  return {
    'DXK-UTAMA': {
      name: 'Gudang Utama',
      profit_center: '583'
    },
    'DXK-SANDAI': {
      name: 'Gudang Part Sandai',
      profit_center: '583'
    }
  };
}

/**
 * Write inventory data to sheet
 */
function writeInventory(ss, inventory) {
  const sheet = ss.getSheetByName(SHEETS.INVENTORY);
  const values = inventory.map((inv, idx) => [
    `inv-${Date.now()}-${idx}`,
    inv.location_id,
    inv.part_id,
    inv.qty_available,
    inv.last_updated
  ]);
  
  if (values.length > 0) {
    sheet.getRange(2, 1, values.length, 5).setValues(values);
  }
}

/**
 * Buat folder untuk import
 * Jalankan sekali untuk setup
 */
function setupImportFolder() {
  const folder = DriveApp.createFolder('BengkelImport');
  Logger.log(`Created folder: ${folder.getId()}`);
}
