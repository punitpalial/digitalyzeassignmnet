const fs = require("fs");

//renaming fields in the lecturer_details JSON file
function renameFields(data) {
  return data.map((item) => {
    const newItem = { ...item };

    // Rename fields
    if ("Lecturer ID" in newItem) {
      newItem["Prof ID"] = newItem["Lecturer ID"];
      delete newItem["Lecturer ID"];
    }

    if ("Lecture Title" in newItem) {
      newItem["Course Title"] = newItem["Lecture Title"];
      delete newItem["Lecture Title"];
    }

    if ("lecture Code" in newItem) {
      newItem["Course Code"] = newItem["lecture Code"];
      delete newItem["lecture Code"];
    }

    if ("Section number" in newItem) {
      newItem["Section Number"] = newItem["Section number"];
      delete newItem["Section number"];
    }

    return newItem;
  });
}

// Read the existing JSON file
const filePath = "../jsonfiles/lecturer_details.json";
const jsonData = JSON.parse(fs.readFileSync(filePath, "utf8"));

// Transform the data
const transformedData = renameFields(jsonData);

// Write back to file
fs.writeFileSync(filePath, JSON.stringify(transformedData, null, 2), "utf8");
console.log("Fields renamed successfully");
