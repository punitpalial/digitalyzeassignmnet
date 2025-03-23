const fs = require("fs");

//renaming fields in the lecturer_details JSON file
function renameFields(data) {
  return data.map((item) => {
    const newItem = { ...item };

    // Convert Start Term from string to integer
    if ("Start Term" in newItem) {
      if (newItem["Start Term"] === "1st_Term") {
        newItem["Start Term"] = 1;
      } else if (newItem["Start Term"] === "2nd_Term") {
        newItem["Start Term"] = 2;
      }
    }

    // Rename fields
    if ("Section number" in newItem) {
      newItem["Section Number"] = newItem["Section number"];
      delete newItem["Section number"];
    }

    if ("Start" in newItem) {
      newItem["Start Term"] = newItem["Start"];
      delete newItem["Start"];
    }

    if ("lecture ID" in newItem) {
      newItem["Course ID"] = newItem["lecture ID"];
      delete newItem["lecture ID"];
    }

    if (" Year" in newItem) {
      newItem["Year"] = newItem[" Year"];
      delete newItem[" Year"];
    }

    if ("prof ID" in newItem) {
      newItem["Prof ID"] = newItem["prof ID"];
      delete newItem["prof ID"];
    }

    return newItem;
  });
}

function removeTermName(data) {
  return data.map((item) => {
    const newItem = { ...item };
    delete newItem["Term name"];
    delete newItem["Year"];
    return newItem;
  });
}

// Read the existing JSON file
const filePath = "../jsonfiles/rooms_data.json";
const jsonData = JSON.parse(fs.readFileSync(filePath, "utf8"));

// Transform the data
let transformedData = renameFields(jsonData);
transformedData = removeTermName(transformedData);

// Write back to file
fs.writeFileSync(filePath, JSON.stringify(transformedData, null, 2), "utf8");
console.log("Fields cleaned successfully");
