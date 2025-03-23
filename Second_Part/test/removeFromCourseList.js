const fs = require("fs");
const path = require("path");

// Paths to JSON files
const courseListPath = path.join(
  __dirname,
  "..",
  "jsonfiles",
  "course_list.json"
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
  "unmatched_courses_not_found_in_ld_when_compared_to_cl.json"
);

// Read JSON files
const courseList = JSON.parse(fs.readFileSync(courseListPath, "utf8"));
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

// Filter course_list.json
const matchedCourses = [];
const unmatchedCourses = [];

courseList.forEach((course) => {
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

// Write results to files
fs.writeFileSync(
  courseListPath,
  JSON.stringify(matchedCourses, null, 2),
  "utf8"
);
fs.writeFileSync(
  unmatchedCoursesPath,
  JSON.stringify(unmatchedCourses, null, 2),
  "utf8"
);

console.log(`Processed ${courseList.length} courses in course_list.json:`);
console.log(
  `- ${matchedCourses.length} courses have matching lecturer details`
);
console.log(
  `- ${
    unmatchedCourses.length
  } courses don't have matching lecturer details (saved to ${path.basename(
    unmatchedCoursesPath
  )})`
);
