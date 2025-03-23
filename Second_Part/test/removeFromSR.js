const fs = require("fs");
const path = require("path");

// Paths to JSON files
const studentRequestsPath = path.join(
  __dirname,
  "..",
  "jsonfiles",
  "student_requests.json"
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
  "unmatched_courses_from_student_requests.json"
);

// Read JSON files
const studentRequests = JSON.parse(
  fs.readFileSync(studentRequestsPath, "utf8")
);
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

// Filter student_requests.json
const matchedRequests = [];
const unmatchedRequests = [];

studentRequests.forEach((request) => {
  const courseCode = request["Course Code"];
  // If courseCode is null or not found in lecturer course codes
  if (
    courseCode === null ||
    !lecturerCourseCodes.has(courseCode.toLowerCase())
  ) {
    unmatchedRequests.push(request);
  } else {
    matchedRequests.push(request);
  }
});

// Write results to files
fs.writeFileSync(
  studentRequestsPath,
  JSON.stringify(matchedRequests, null, 2),
  "utf8"
);
fs.writeFileSync(
  unmatchedCoursesPath,
  JSON.stringify(unmatchedRequests, null, 2),
  "utf8"
);

console.log(`Processed ${studentRequests.length} student requests:`);
console.log(
  `- ${matchedRequests.length} requests have matching lecturer details`
);
console.log(
  `- ${
    unmatchedRequests.length
  } requests don't have matching lecturer details (saved to ${path.basename(
    unmatchedCoursesPath
  )})`
);
