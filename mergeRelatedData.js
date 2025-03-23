const fs = require("fs");
const path = require("path");

// Directory containing the JSON files
const jsonDirectory = path.join(__dirname, "jsonfiles");

// Output file path
const outputFilePath = path.join(__dirname, "integrated_data.json");

// Function to read a JSON file
function readJsonFile(filePath) {
  try {
    const data = fs.readFileSync(filePath, "utf8");
    return JSON.parse(data);
  } catch (error) {
    console.error(`Error reading file ${filePath}:`, error);
    return null;
  }
}

// Read all necessary JSON files
const roomsData = readJsonFile(path.join(jsonDirectory, "rooms_data.json"));
const lecturerDetails = readJsonFile(
  path.join(jsonDirectory, "lecturer_details.json")
);
const studentRequests = readJsonFile(
  path.join(jsonDirectory, "student_requests.json")
);
const courseList =
  readJsonFile(path.join(jsonDirectory, "course_list.json")) || [];

// Normalize field names function
function normalizeKey(key) {
  return key.toLowerCase().replace(/[^a-z0-9]/g, "");
}

// Create a map for faster lookups
function createLookupMap(data, keyField) {
  const map = new Map();
  if (!data) return map;

  data.forEach((item) => {
    const key = item[keyField]?.toString();
    if (key) {
      if (!map.has(key)) {
        map.set(key, []);
      }
      map.get(key).push(item);
    }
  });
  return map;
}

// Create lookup maps
const coursesByID = createLookupMap(courseList, "Course ID");
const coursesByCode = createLookupMap(courseList, "Course Code");
const roomsByCourseID = createLookupMap(roomsData, "Course ID");
const lecturersByProfID = createLookupMap(lecturerDetails, "Prof ID");
const studentRequestsByCourseID = createLookupMap(studentRequests, "Course ID");
const studentsByID = new Map();

// Group student requests by student ID
if (studentRequests) {
  studentRequests.forEach((request) => {
    const studentID = request["Student ID"]?.toString();
    if (studentID) {
      if (!studentsByID.has(studentID)) {
        studentsByID.set(studentID, {
          id: request["Student ID"],
          collegeYear: request["College Year"],
          requests: [],
        });
      }

      studentsByID.get(studentID).requests.push({
        courseId: request["Course ID"],
        courseTitle: request["Course Title"],
        courseCode: request["Course Code"],
        type: request["Type"],
        priority: request["Priority"],
        requestStartTerm: request["Request start term"],
        length: request["Length"],
      });
    }
  });
}

// Create integrated course structure
const courses = [];
const addedCourseIDs = new Set();

// Add courses from course list
if (courseList) {
  courseList.forEach((course) => {
    const courseID = course["Course ID"]?.toString();
    if (courseID && !addedCourseIDs.has(courseID)) {
      addedCourseIDs.add(courseID);
      courses.push(createCourseObject(course));
    }
  });
}

// Add courses from rooms data if not already added
if (roomsData) {
  roomsData.forEach((room) => {
    const courseID = room["Course ID"]?.toString();
    if (courseID && !addedCourseIDs.has(courseID)) {
      addedCourseIDs.add(courseID);
      courses.push(createCourseObject(room));
    }
  });
}

// Add courses from lecturer details if not already added
if (lecturerDetails) {
  lecturerDetails.forEach((lecturer) => {
    const courseCode = lecturer["Course Code"];
    const sectionNumber = lecturer["Section Number"];

    if (courseCode && sectionNumber) {
      const matchingCourses = coursesByCode.get(courseCode) || [];
      const matchingCourse = matchingCourses.find(
        (c) => c["Section Number"] === sectionNumber
      );

      if (matchingCourse) {
        const courseID = matchingCourse["Course ID"]?.toString();
        if (courseID && !addedCourseIDs.has(courseID)) {
          addedCourseIDs.add(courseID);
          courses.push(createCourseObject(matchingCourse));
        }
      } else if (!matchingCourses.length) {
        // Create a new course if we don't have it yet
        const newCourse = {
          "Course Code": courseCode,
          "Course Title": lecturer["Course Title"],
          Length: lecturer["Length"],
          "Section Number": sectionNumber,
          "Prof ID": lecturer["Prof ID"],
          "Start Term": lecturer["Start Term"],
        };

        courses.push(createCourseObject(newCourse));
      }
    }
  });
}

// Helper function to create a standardized course object
function createCourseObject(data) {
  const courseID = data["Course ID"]?.toString();
  const courseCode = data["Course Code"];
  const sectionNumber = data["Section Number"];

  // Find related data
  const roomInfo = roomsData?.find(
    (r) =>
      r["Course ID"]?.toString() === courseID &&
      r["Section Number"] === sectionNumber
  );

  const lecturerInfo = lecturerDetails?.find(
    (l) =>
      l["Course Code"] === courseCode && l["Section Number"] === sectionNumber
  );

  const profID = data["Prof ID"] || lecturerInfo?.["Prof ID"];

  const studentRequests = studentRequestsByCourseID.get(courseID) || [];

  // Create the course object
  return {
    id: data["Course ID"],
    title: data["Course Title"]?.replace(/_/g, " "),
    code: courseCode,
    length: data["Length"],
    credits: data["Credits"],
    department: data["Department(s)"]?.replace(/_/g, " "),
    sections: [
      {
        number: sectionNumber,
        term: data["Start Term"],
        room: roomInfo
          ? {
              number: roomInfo["Room Number"],
            }
          : null,
        professor: profID
          ? {
              id: profID,
            }
          : null,
        students: studentRequests.map((req) => ({
          id: req["Student ID"],
          requestType: req["Type"],
          priority: req["Priority"],
        })),
      },
    ],
  };
}

// Create the final integrated structure
const integratedData = {
  courses: courses,
  professors: Array.from(lecturersByProfID.keys()).map((profID) => {
    const professorCourses = lecturersByProfID.get(profID);
    return {
      id: parseInt(profID),
      courses: professorCourses.map((course) => ({
        title: course["Course Title"]?.replace(/_/g, " "),
        code: course["Course Code"],
        sectionNumber: course["Section Number"],
      })),
    };
  }),
  students: Array.from(studentsByID.values()),
  rooms: roomsData
    ? Array.from(new Set(roomsData.map((r) => r["Room Number"]))).map(
        (roomNumber) => {
          const roomCourses = roomsData.filter(
            (r) => r["Room Number"] === roomNumber
          );
          return {
            number: roomNumber,
            courses: roomCourses.map((course) => ({
              id: course["Course ID"],
              title: course["Course Title"]?.replace(/_/g, " "),
              code: course["Course Code"],
              sectionNumber: course["Section Number"],
            })),
          };
        }
      )
    : [],
};

// Write the integrated data to a new JSON file
fs.writeFileSync(
  outputFilePath,
  JSON.stringify(integratedData, null, 2),
  "utf8"
);
console.log(`Integrated data saved to ${outputFilePath}`);
