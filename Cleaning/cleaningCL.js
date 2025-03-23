const fs = require("fs");

//renaming fields in the lecturer_details JSON file
function renameFields(data) {
  return data.map((item) => {
    const newItem = { ...item };

    // Rename fields
    if ("Course code" in newItem) {
      newItem["Course Code"] = newItem["Course code"];
      delete newItem["Course code"];
    }

    if ("Title" in newItem) {
      newItem["Course Title"] = newItem["Title"];
      delete newItem["Title"];
    }

    return newItem;
  });
}

// Read the existing JSON file
const filePath = "../jsonfiles/course_list.json";
const jsonData = JSON.parse(fs.readFileSync(filePath, "utf8"));

// Transform the data
const transformedData = renameFields(jsonData);

// Write back to file
fs.writeFileSync(filePath, JSON.stringify(transformedData, null, 2), "utf8");
console.log("Fields renamed successfully");
