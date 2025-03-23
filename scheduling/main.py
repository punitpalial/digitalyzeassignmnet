import pandas as pd
import numpy as np
import pulp as pl
import json
from pathlib import Path

# Load all required data from JSON files
def load_data():
    """
    Load course data, lecturer details, and student requests from JSON files.
    Returns the raw data for further processing.
    """
    data_dir = Path("Second_Part/jsonfiles")
    
    with open(data_dir / "course_list.json", "r") as f:
        course_list = json.load(f)
    
    with open(data_dir / "lecturer_details.json", "r") as f:
        lecturer_details = json.load(f)
    
    with open(data_dir / "student_requests.json", "r") as f:
        student_requests = json.load(f)
    
    return course_list, lecturer_details, student_requests

# Clean and standardize data for optimization
def preprocess_data(course_list, lecturer_details, student_requests):
    """
    Preprocess the raw data:
    - Convert to DataFrames for easier manipulation
    - Standardize course codes
    - Create unique section identifiers
    - Extract all available blocks
    - Map priority types to numeric values
    """
    # Convert to DataFrames for easier manipulation
    courses_df = pd.DataFrame(course_list)
    lecturers_df = pd.DataFrame(lecturer_details)
    requests_df = pd.DataFrame(student_requests)
    
    # Standardize course codes (lowercase) for consistent comparison
    courses_df["Course Code"] = courses_df["Course Code"].str.lower()
    lecturers_df["Course Code"] = lecturers_df["Course Code"].str.lower()
    requests_df["Course Code"] = requests_df["Course Code"].str.lower()
    
    # Create unique section identifiers (course_code_section_number)
    lecturers_df['Section_ID'] = lecturers_df['Course Code'] + '_' + lecturers_df['Section Number'].astype(str)
    
    # Extract all available blocks across all courses
    all_blocks = set()
    for blocks in courses_df["Available blocks"]:
        if isinstance(blocks, list):
            all_blocks.update(blocks)
        else:
            all_blocks.add(blocks)
    
    # Map priority types to numeric values for optimization
    # Rule 8: "Required" > "Requested" > "Recommended"
    priority_map = {"Required": 3, "Requested": 2, "Recommended": 1}
    requests_df["Priority_Value"] = requests_df["Type"].map(priority_map)
    
    # Create a lookup table for request priorities - will be used in optimization
    request_priorities = {}
    for _, row in requests_df.iterrows():
        student_id = row["Student ID"]
        course_code = row["Course Code"]
        priority = row["Priority_Value"]
        request_priorities[(student_id, course_code)] = priority
    
    return courses_df, lecturers_df, requests_df, list(all_blocks), request_priorities

def build_optimization_model(courses_df, lecturers_df, requests_df, all_blocks, request_priorities):
    """
    Build the PuLP optimization model with:
    - Decision variables for student-section-block assignments
    - Decision variables for professor-section-block assignments
    - Objective function to maximize satisfied requests by priority
    - Constraints based on scheduling rules
    """
    # Create the optimization model (maximization problem)
    model = pl.LpProblem("Course_Scheduling", pl.LpMaximize)
    
    # Get unique students, courses, and sections for variable creation
    students = requests_df["Student ID"].unique()
    course_sections = lecturers_df["Section_ID"].unique()
    professors = lecturers_df["Prof ID"].unique()
    
    # Map courses to their available blocks
    # Rule 9: Schedule sections only in available blocks
    course_to_blocks = {}
    for _, course in courses_df.iterrows():
        code = course["Course Code"]
        if isinstance(course["Available blocks"], list):
            course_to_blocks[code] = course["Available blocks"]
        else:
            course_to_blocks[code] = [course["Available blocks"]]
    
    # Map student IDs to the courses they've requested (for efficient variable creation)
    student_course_requests = {}
    for _, request in requests_df.iterrows():
        student_id = request["Student ID"]
        course_code = request["Course Code"]
        
        if student_id not in student_course_requests:
            student_course_requests[student_id] = set()
        
        student_course_requests[student_id].add(course_code)
    
    # Map courses to lecturer assignments
    course_to_lecturers = {}
    for _, lecturer in lecturers_df.iterrows():
        course_code = lecturer["Course Code"]
        section_id = lecturer["Section_ID"]
        prof_id = lecturer["Prof ID"]
        
        if section_id not in course_to_lecturers:
            course_to_lecturers[section_id] = []
        
        course_to_lecturers[section_id].append(prof_id)
    
    print("Creating decision variables...")
    
    # DECISION VARIABLES
    
    # 1. Student assignment variables: x[student, section, block] = 1 if student is assigned to section in block
    x = {}
    # Only create variables for courses that students have actually requested
    for student in students:
        if student in student_course_requests:
            for section in course_sections:
                course_code = section.split('_')[0]
                # Only create variables if student requested this course
                if course_code in student_course_requests[student] and course_code in course_to_blocks:
                    for block in course_to_blocks[course_code]:
                        x[(student, section, block)] = pl.LpVariable(
                            f"x_{student}_{section}_{block}", 
                            cat=pl.LpBinary
                        )
    
    # 2. Professor assignment variables: y[professor, section, block] = 1 if professor teaches section in block
    y = {}
    for section in course_sections:
        course_code = section.split('_')[0]
        if course_code in course_to_blocks:
            for block in course_to_blocks[course_code]:
                for prof in professors:
                    # Only create variables for professors who can teach this section
                    if section in course_to_lecturers and prof in course_to_lecturers[section]:
                        y[(prof, section, block)] = pl.LpVariable(
                            f"y_{prof}_{section}_{block}", 
                            cat=pl.LpBinary
                        )
    
    # 3. Section usage variables: section_used[section, block] = 1 if section is scheduled in block
    section_used = {}
    for section in course_sections:
        course_code = section.split('_')[0]
        if course_code in course_to_blocks:
            for block in course_to_blocks[course_code]:
                section_used[(section, block)] = pl.LpVariable(
                    f"used_{section}_{block}", 
                    cat=pl.LpBinary
                )
    
    print("Setting up objective function...")
    
    # OBJECTIVE FUNCTION
    # Maximize the sum of fulfilled student requests, weighted by priority
    # Rule 8: "Required" > "Requested" > "Recommended"
    objective_terms = []
    
    for (student, section, block) in x:
        course_code = section.split('_')[0]
        # Look up the priority value for this student-course combination
        priority_key = (student, course_code)
        
        if priority_key in request_priorities:
            priority = request_priorities[priority_key]
            objective_terms.append(x[(student, section, block)] * priority)
    
    model += pl.lpSum(objective_terms)
    
    print("Adding constraints...")
    
    # CONSTRAINTS
    
    # 1. Rule 4: A student can only be in one course per block
    for student in students:
        for block in all_blocks:
            model += pl.lpSum(
                x[(student, section, block)] 
                for section in course_sections 
                if (student, section, block) in x
            ) <= 1, f"student_{student}_one_course_block_{block}"
    
    # 2. Rule 3: A professor can only teach one section per block
    for prof in professors:
        for block in all_blocks:
            model += pl.lpSum(
                y[(prof, section, block)] 
                for section in course_sections 
                if (prof, section, block) in y
            ) <= 1, f"prof_{prof}_one_section_block_{block}"
    
    # 3. Rule 7: Section size limits - prevent overcrowding
    for section in course_sections:
        course_code = section.split('_')[0]
        if course_code in course_to_blocks:
            for block in course_to_blocks[course_code]:
                # Only if this section-block combination can be used
                if (section, block) in section_used:
                    # Get min, target, max section sizes
                    section_course_rows = courses_df[courses_df["Course Code"] == course_code]
                    
                    if not section_course_rows.empty:
                        min_size = section_course_rows["Minimum section size"].values[0]
                        max_size = section_course_rows["Maximum section size"].values[0]
                        
                        # Calculate section size (number of students assigned)
                        section_size = pl.lpSum(
                            x[(student, section, block)] 
                            for student in students 
                            if (student, section, block) in x
                        )
                        
                        # If section is used, enforce minimum size
                        model += section_size >= min_size * section_used[(section, block)], f"min_size_{section}_{block}"
                        
                        # Section cannot exceed maximum size
                        model += section_size <= max_size * section_used[(section, block)], f"max_size_{section}_{block}"
                        
                        # Ensure a section has exactly one professor if it's used
                        model += pl.lpSum(
                            y[(prof, section, block)] 
                            for prof in professors 
                            if (prof, section, block) in y
                        ) == section_used[(section, block)], f"one_prof_{section}_{block}"
    
    # 4. Required courses must be fulfilled for all students
    for _, request in requests_df[requests_df["Type"] == "Required"].iterrows():
        student = request["Student ID"]
        course_code = request["Course Code"]
        
        # Find all sections for this course
        relevant_sections = [s for s in course_sections if s.split('_')[0] == course_code]
        
        # Student must be assigned to at least one section of a required course
        if relevant_sections:
            model += pl.lpSum(
                x[(student, section, block)] 
                for section in relevant_sections
                for block in course_to_blocks.get(course_code, [])
                if (student, section, block) in x
            ) >= 1, f"required_{student}_{course_code}"
    
    # 5. Balance distribution across sections (Rule 7)
    for course_code in set(section.split('_')[0] for section in course_sections):
        # Find all sections for this course
        course_sections_list = [s for s in course_sections if s.split('_')[0] == course_code]
        
        if len(course_sections_list) > 1 and course_code in course_to_blocks:
            for block in course_to_blocks[course_code]:
                # For each pair of sections, try to balance enrollment
                for i, section1 in enumerate(course_sections_list):
                    for section2 in course_sections_list[i+1:]:
                        # Only if both sections could be scheduled in this block
                        if (section1, block) in section_used and (section2, block) in section_used:
                            # Calculate section sizes
                            size1 = pl.lpSum(
                                x[(student, section1, block)] 
                                for student in students 
                                if (student, section1, block) in x
                            )
                            
                            size2 = pl.lpSum(
                                x[(student, section2, block)] 
                                for student in students 
                                if (student, section2, block) in x
                            )
                            
                            # Limit the difference in section sizes
                            # This is a soft constraint using a dummy variable
                            diff = pl.LpVariable(f"diff_{section1}_{section2}_{block}", lowBound=0)
                            model += diff >= size1 - size2, f"diff1_{section1}_{section2}_{block}"
                            model += diff >= size2 - size1, f"diff2_{section1}_{section2}_{block}"
                            
                            # Add a small penalty to the objective function for imbalanced sections
                            model += -0.01 * diff  # Small weight to avoid compromising main objective
    
    return model

def solve_and_generate_schedules(model, courses_df, lecturers_df, requests_df, all_blocks):
    """
    Solve the optimization model and extract the results:
    - Student schedules
    - Professor schedules
    - Statistics on fulfilled vs. unfulfilled requests
    """
    print("Solving optimization model...")
    # Use CBC solver with time limit to ensure termination
    solver = pl.PULP_CBC_CMD(msg=True, timeLimit=300)
    model.solve(solver)
    
    print(f"Status: {pl.LpStatus[model.status]}")
    
    if model.status != pl.LpStatusOptimal:
        print("Warning: Optimal solution not found. Using best solution found so far.")
    
    print(f"Objective value: {pl.value(model.objective)}")
    
    # Extract results
    student_schedules = {}
    professor_schedules = {}
    
    print("Extracting student schedules...")
    # Extract student schedules
    # Extracting student schedules
    print("Extracting student schedules...")
    student_schedules = {}
    for var in model.variables():
        # Only consider x variables (student assignments) with value 1
        if var.name.startswith('x_') and var.value() == 1:
            # Parse variable name to extract components
            # Format: x_student_course-code_section-number_block
            parts = var.name.split('_')
            if len(parts) >= 4:  # Ensure we have enough parts
                student = parts[1]
                section = '_'.join(parts[2:-1])  # Handle course codes that might contain underscores
                block = parts[-1]
                
                # Extract course code and section number
                section_parts = section.split('_')
                if len(section_parts) >= 2:
                    course_code = '_'.join(section_parts[:-1])  # Handle course codes with underscores
                    section_num = section_parts[-1]
                    
                    # Initialize student entry if not exists
                    if student not in student_schedules:
                        student_schedules[student] = []
                    
                    # Get course title from courses dataframe
                    course_title = courses_df.loc[
                        courses_df["Course Code"] == course_code, 
                        "Course Title"
                    ].values[0] if len(courses_df.loc[courses_df["Course Code"] == course_code]) > 0 else "Unknown Course"
                    
                    # Find the professor for this section with error handling
                    try:
                        # Convert section_num to int only if it's not empty
                        if section_num:
                            section_num_int = int(section_num)
                            professor_query = lecturers_df[
                                (lecturers_df["Course Code"] == course_code) & 
                                (lecturers_df["Section Number"] == section_num_int)
                            ]
                        else:
                            # Handle case where section_num is empty
                            professor_query = lecturers_df[
                                (lecturers_df["Course Code"] == course_code)
                            ]
                        
                        if len(professor_query) > 0:
                            professor_id = professor_query["Prof ID"].values[0]
                        else:
                            professor_id = "Unknown"
                    except (ValueError, IndexError):
                        # Handle conversion errors or empty results
                        professor_id = "Unknown"
                    
                    # Add course to student schedule
                    student_schedules[student].append({
                        "Student ID": student,
                        "Course Code": course_code,
                        "Course Title": course_title,
                        "Section": section_num,
                        "Block": block,
                        "Professor ID": professor_id
                    })
    
    print("Extracting professor schedules...")
    # Extract professor schedules
    for var in model.variables():
        if var.name.startswith('y_') and var.value() > 0.9:
            parts = var.name.split('_')
            if len(parts) >= 4:
                prof = parts[1]
                # Handle section names that might contain underscores
                section = '_'.join(parts[2:-1])
                block = parts[-1]
                
                course_code = section.split('_')[0]
                section_num = section.split('_')[1]
                
                if prof not in professor_schedules:
                    professor_schedules[prof] = []
                
                # Get course information
                course_title = "Unknown"
                course_row = courses_df[courses_df["Course Code"] == course_code]
                if not course_row.empty:
                    course_title = course_row["Course Title"].values[0]
                
                professor_schedules[prof].append({
                    "Professor ID": prof,
                    "Course Code": course_code,
                    "Course Title": course_title,
                    "Section": section_num,
                    "Block": block
                })
    
    print("Calculating statistics...")
    # Generate statistics on request fulfillment
    total_requests = len(requests_df)
    fulfilled_required = 0
    fulfilled_requested = 0
    fulfilled_recommended = 0
    total_required = len(requests_df[requests_df["Type"] == "Required"])
    total_requested = len(requests_df[requests_df["Type"] == "Requested"])
    total_recommended = len(requests_df[requests_df["Type"] == "Recommended"])
    
    # For each student, check which of their requests were fulfilled
    for student in student_schedules:
        # Get all courses assigned to this student
        scheduled_courses = {schedule["Course Code"] for schedule in student_schedules[student]}
        
        # Count fulfilled requests by type
        student_requests = requests_df[requests_df["Student ID"] == int(student)]
        for _, request in student_requests.iterrows():
            if request["Course Code"] in scheduled_courses:
                if request["Type"] == "Required":
                    fulfilled_required += 1
                elif request["Type"] == "Requested":
                    fulfilled_requested += 1
                elif request["Type"] == "Recommended":
                    fulfilled_recommended += 1

    # Convert NumPy types to native Python types for JSON serialization
    def convert_numpy_types(obj):
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
             return [convert_numpy_types(i) for i in obj]
        elif isinstance(obj, np.integer):
             return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        else:
            return obj
    
    # Apply conversion before saving
    student_schedules_converted = convert_numpy_types(student_schedules)
    professor_schedules_converted = convert_numpy_types(professor_schedules)

    # Save the converted data
    with open("student_schedules.json", "w") as f:
        json.dump(student_schedules_converted, f, indent=2)

    with open("professor_schedules.json", "w") as f:
        json.dump(professor_schedules_converted, f, indent=2)
            
    # # Save results to JSON files
    # print("Saving schedules to JSON files...")
    # with open("student_schedules.json", "w") as f:
    #     json.dump(student_schedules, f, indent=2)
    
    # with open("professor_schedules.json", "w") as f:
    #     json.dump(professor_schedules, f, indent=2)

    # Create a table for resolved & unresolved requests
    stats_data = {
        "Priority": ["Required", "Requested", "Recommended", "Total"],
        "Total Requests": [total_required, total_requested, total_recommended, total_requests],
        "Fulfilled": [fulfilled_required, fulfilled_requested, fulfilled_recommended, 
                    fulfilled_required + fulfilled_requested + fulfilled_recommended],
        "Unfulfilled": [total_required - fulfilled_required, 
                    total_requested - fulfilled_requested,
                    total_recommended - fulfilled_recommended,
                    total_requests - (fulfilled_required + fulfilled_requested + fulfilled_recommended)],
        "Fulfillment Rate (%)": [fulfilled_required/max(1,total_required)*100,
                                fulfilled_requested/max(1,total_requested)*100,
                                fulfilled_recommended/max(1,total_recommended)*100,
                                (fulfilled_required + fulfilled_requested + fulfilled_recommended)/total_requests*100]
    }

    # Save as CSV
    stats_df = pd.DataFrame(stats_data)
    stats_df.to_csv("request_fulfillment_statistics.csv", index=False)
    print("Request fulfillment statistics saved to request_fulfillment_statistics.csv")

    # Identify students with unfulfilled required requests
    unfulfilled_required_requests = []
    for _, request in requests_df[requests_df["Type"] == "Required"].iterrows():
        student_id = request["Student ID"]
        course_code = request["Course Code"]
        
        # Check if this student has this course in their schedule
        if str(student_id) in student_schedules:
            student_courses = {schedule["Course Code"] for schedule in student_schedules[str(student_id)]}
            if course_code not in student_courses:
                unfulfilled_required_requests.append({
                    "Student ID": student_id,
                    "Course Code": course_code,
                    "Course Title": request["Course Title"]
                })
        else:
            # Student not scheduled at all
            unfulfilled_required_requests.append({
                "Student ID": student_id,
                "Course Code": course_code,
                "Course Title": request["Course Title"]
            })

    # Save as CSV
    if unfulfilled_required_requests:
        pd.DataFrame(unfulfilled_required_requests).to_csv("unfulfilled_required_requests.csv", index=False)
        print(f"WARNING: {len(unfulfilled_required_requests)} required requests could not be fulfilled.")
        
    # Print detailed statistics
    print("\n===== SCHEDULING STATISTICS =====")
    print(f"Total student requests: {total_requests}")
    print(f"Total students scheduled: {len(student_schedules)}")
    print(f"Total professors scheduled: {len(professor_schedules)}")
    print("\nRequest Fulfillment by Priority:")
    print(f"Required courses fulfilled: {fulfilled_required}/{total_required} ({fulfilled_required/max(1,total_required)*100:.2f}%)")
    print(f"Requested courses fulfilled: {fulfilled_requested}/{total_requested} ({fulfilled_requested/max(1,total_requested)*100:.2f}%)")
    print(f"Recommended courses fulfilled: {fulfilled_recommended}/{total_recommended} ({fulfilled_recommended/max(1,total_recommended)*100:.2f}%)")
    print(f"Overall fulfillment rate: {(fulfilled_required + fulfilled_requested + fulfilled_recommended)/total_requests*100:.2f}%")
    
    return student_schedules, professor_schedules



def main():
    """
    Main function to execute the entire scheduling process:
    1. Load data from JSON files
    2. Preprocess the data
    3. Build the optimization model
    4. Solve the model and generate schedules
    5. Save the results
    """
    print("Loading data...")
    course_list, lecturer_details, student_requests = load_data()
    
    print("Preprocessing data...")
    courses_df, lecturers_df, requests_df, all_blocks, request_priorities = preprocess_data(
        course_list, lecturer_details, student_requests
    )
    
    print("Building optimization model...")
    model = build_optimization_model(
        courses_df, lecturers_df, requests_df, all_blocks, request_priorities
    )
    
    print("Solving model and generating schedules...")
    student_schedules, professor_schedules = solve_and_generate_schedules(
        model, courses_df, lecturers_df, requests_df, all_blocks
    )
    
    print("\nDone! Results saved to student_schedules.json and professor_schedules.json")
    
    # Generate block schedules for visualization
    print("Generating block schedules for visualization...")
    generate_block_schedules(student_schedules, professor_schedules, all_blocks)

def generate_block_schedules(student_schedules, professor_schedules, all_blocks):
    """
    Generate visual block schedules for all students and professors.
    Creates CSV files showing which courses are scheduled in each block.
    """
    # Generate student block schedules
    student_block_schedules = {}
    for student_id, courses in student_schedules.items():
        student_block_schedules[student_id] = {block: "---" for block in all_blocks}
        for course in courses:
            block = course["Block"]
            course_info = f"{course['Course Code']} (Sec {course['Section']})"
            student_block_schedules[student_id][block] = course_info
    
    # Generate professor block schedules
    professor_block_schedules = {}
    for prof_id, courses in professor_schedules.items():
        professor_block_schedules[prof_id] = {block: "---" for block in all_blocks}
        for course in courses:
            block = course["Block"]
            course_info = f"{course['Course Code']} (Sec {course['Section']})"
            professor_block_schedules[prof_id][block] = course_info
    
    # Save as CSV files
    student_schedule_df = pd.DataFrame.from_dict(student_block_schedules, orient='index')
    student_schedule_df.index.name = "Student ID"
    student_schedule_df = student_schedule_df.reindex(columns=sorted(all_blocks))
    student_schedule_df.to_csv("student_block_schedules.csv")
    
    professor_schedule_df = pd.DataFrame.from_dict(professor_block_schedules, orient='index')
    professor_schedule_df.index.name = "Professor ID"
    professor_schedule_df = professor_schedule_df.reindex(columns=sorted(all_blocks))
    professor_schedule_df.to_csv("professor_block_schedules.csv")
    
    print("Block schedules generated and saved to CSV files.")

if __name__ == "__main__":
    main()