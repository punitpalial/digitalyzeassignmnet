const fs = require("fs");
const path = require("path");

// Paths to the JSON files using relative paths
const roomsDataPath = path.join(
  __dirname,
  "..",
  "jsonfiles",
  "rooms_data.json"
);
const lecturerDetailsPath = path.join(
  __dirname,
  "..",
  "jsonfiles",
  "lecturer_details.json"
);
const unmatchedCoursesPath = path.join(
  __dirname,
  "..",
  "jsonfiles",
  "unmatched_courses_not_found_in_ld_when_compared_to_rd.json"
);

// Read the JSON files
const roomsData = JSON.parse(fs.readFileSync(roomsDataPath, "utf8"));
const lecturerDetails = JSON.parse(
  fs.readFileSync(lecturerDetailsPath, "utf8")
);

// Extract all course codes from lecturer_details.json
const lecturerCourseCodes = new Set();
lecturerDetails.forEach((lecturer) => {
  if (lecturer["Course Code"]) {
    lecturerCourseCodes.add(lecturer["Course Code"].toLowerCase());
  }
});

console.log(
  `Found ${lecturerCourseCodes.size} unique course codes in lecturer_details.json`
);

// Filter rooms_data
const matchedCourses = [];
const unmatchedCourses = [];

roomsData.forEach((course) => {
  const courseCode = course["Course Code"];
  // If courseCode is null or not found in lecturer course codes
  if (
    courseCode === null ||
    !lecturerCourseCodes.has(courseCode.toLowerCase())
  ) {
    unmatchedCourses.push(course);
  } else {
    matchedCourses.push(course);
  }
});

// Write the results to files
fs.writeFileSync(
  roomsDataPath,
  JSON.stringify(matchedCourses, null, 2),
  "utf8"
);
fs.writeFileSync(
  unmatchedCoursesPath,
  JSON.stringify(unmatchedCourses, null, 2),
  "utf8"
);

console.log(`Processed ${roomsData.length} courses in rooms_data.json:`);
console.log(
  `- ${matchedCourses.length} courses have matching lecturer details`
);
console.log(
  `- ${unmatchedCourses.length} courses don't have matching lecturer details (saved to unmatched_courses_not_found_in_ld_when_compared_to_rd.json)`
);
