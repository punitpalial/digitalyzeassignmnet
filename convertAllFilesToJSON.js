const XLSX = require("xlsx");
const fs = require("fs");

function replaceSpacesInValue(value) {
  if (typeof value === "string") {
    // Check if the string contains commas
    if (value.includes(",")) {
      // Split by comma and process each value
      return value.split(",").map((item) => item.trim().replace(/\s+/g, "_"));
    }
    return value.replace(/\s+/g, "_");
  }
  return value;
}

function processData(data) {
  if (Array.isArray(data)) {
    return data.map((item) => {
      if (typeof item === "object" && item !== null) {
        return processData(item);
      }
      return replaceSpacesInValue(item);
    });
  }

  if (typeof data === "object" && data !== null) {
    const processedData = {};
    for (const [key, value] of Object.entries(data)) {
      if (typeof value === "object" && value !== null) {
        processedData[key] = processData(value);
      } else {
        processedData[key] = replaceSpacesInValue(value);
      }
    }
    return processedData;
  }

  return replaceSpacesInValue(data);
}

function readExcelFile(filePath) {
  const workbook = XLSX.readFile(filePath);
  const result = {};

  // Process each sheet
  workbook.SheetNames.forEach((sheetName) => {
    const worksheet = workbook.Sheets[sheetName];
    const sheetData = XLSX.utils.sheet_to_json(worksheet, {
      raw: true,
      defval: null,
      blankrows: false,
    });
    result[sheetName] = processData(sheetData);
  });

  return result;
}

function saveToJsonFile(data, outputPath) {
  try {
    const jsonString = JSON.stringify(data, null, 2);
    fs.writeFileSync(outputPath, jsonString, "utf8");
    console.log(`Data successfully saved to ${outputPath}`);
  } catch (error) {
    console.error("Error saving JSON file:", error);
  }
}

// Read all sheets
const allSheetsData = readExcelFile("dataset.xlsx");

// Save each sheet to a separate JSON file
Object.entries(allSheetsData).forEach(([sheetName, sheetData]) => {
  const fileName = `${sheetName.toLowerCase().replace(/\s+/g, "_")}.json`;
  saveToJsonFile(sheetData, `jsonfiles/${fileName}`);
});
