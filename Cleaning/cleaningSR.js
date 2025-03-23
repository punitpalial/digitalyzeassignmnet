const fs = require("fs");

//renaming fields in the lecturer_details JSON file
function renameFields(data) {
  return data.map((item) => {
    const newItem = { ...item };

    // Convert Start Term from string to integer
    if ("College Year" in newItem) {
      if (newItem["College Year"] === "1st_Year") {
        newItem["College Year"] = 1;
      } else if (newItem["College Year"] === "2nd_Year") {
        newItem["College Year"] = 2;
      } else if (newItem["College Year"] === "3rd_Year") {
        newItem["College Year"] = 3;
      } else if (newItem["College Year"] === "4th_Year") {
        newItem["College Year"] = 4;
      }
    }

    if ("Request start term" in newItem) {
      if (newItem["Request start term"] === "First_term") {
        newItem["Request start term"] = 1;
      } else if (newItem["Request start term"] === "Second_term") {
        newItem["Request start term"] = 2;
      } else if (newItem["Request start term"] === "Any_term") {
        newItem["Request start term"] = null;
      }
    }

    // Rename fields
    if ("Title" in newItem) {
      newItem["Course Title"] = newItem["Title"];
      delete newItem["Title"];
    }

    if ("student ID" in newItem) {
      newItem["Student ID"] = newItem["student ID"];
      delete newItem["student ID"];
    }

    if ("Course code" in newItem) {
      newItem["Course Code"] = newItem["Course code"];
      delete newItem["Course code"];
    }

    return newItem;
  });
}

// Read the existing JSON file
const filePath = "../jsonfiles/student_requests.json";
const jsonData = JSON.parse(fs.readFileSync(filePath, "utf8"));

// Transform the data
const transformedData = renameFields(jsonData);

// Write back to file
fs.writeFileSync(filePath, JSON.stringify(transformedData, null, 2), "utf8");
console.log("Fields renamed successfully");
