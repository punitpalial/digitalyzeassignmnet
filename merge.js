const fs = require("fs");

function mergeJSONFiles() {
  try {
    // Read all JSON files
    const lecturerDetails = JSON.parse(
      fs.readFileSync("./jsonfiles/lecturer_details.json", "utf8")
    );
    const roomsData = JSON.parse(
      fs.readFileSync("./jsonfiles/rooms_data.json", "utf8")
    );
    const courseList = JSON.parse(
      fs.readFileSync("./jsonfiles/course_list.json", "utf8")
    );
    const studentRequests = JSON.parse(
      fs.readFileSync("./jsonfiles/student_requests.json", "utf8")
    );

    // Create merged data structure
    const mergedData = {
      courses: courseList.map((course) => {
        // Find all room assignments for this course
        const roomAssignments = roomsData.filter(
          (room) => room.Course_Code === course.Course_Code
        );

        // Find all lecturer assignments for this course
        const lecturerAssignments = lecturerDetails.filter(
          (lecturer) => lecturer.Course_Code === course.Course_Code
        );

        // Find all student requests for this course
        const requests = studentRequests.filter(
          (request) => request.Course_Code === course.Course_Code
        );

        return {
          ...course,
          room_assignments: roomAssignments,
          lecturer_assignments: lecturerAssignments,
          student_requests: requests.length, // Count of requests for this course
        };
      }),
    };

    // Write merged data to new file
    fs.writeFileSync(
      "./jsonfiles/merged_data.json",
      JSON.stringify(mergedData, null, 2),
      "utf8"
    );

    console.log("JSON files merged successfully!");
  } catch (error) {
    console.error("Error merging JSON files:", error);
  }
}

mergeJSONFiles();
