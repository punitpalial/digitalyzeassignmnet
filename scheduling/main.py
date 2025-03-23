import pandas as pd
import numpy as np
import pulp as pl
import json
from pathlib import Path

# Load all required data
def load_data():
    data_dir = Path("Second_Part/jsonfiles")
    
    with open(data_dir / "course_list.json", "r") as f:
        course_list = json.load(f)
    
    with open(data_dir / "lecturer_details.json", "r") as f:
        lecturer_details = json.load(f)
    
    with open(data_dir / "student_requests.json", "r") as f:
        student_requests = json.load(f)
    
    return course_list, lecturer_details, student_requests

# Clean and standardize data
def preprocess_data(course_list, lecturer_details, student_requests):
    # Convert to DataFrames for easier manipulation
    courses_df = pd.DataFrame(course_list)
    lecturers_df = pd.DataFrame(lecturer_details)
    requests_df = pd.DataFrame(student_requests)
    
    # Standardize course codes (lowercase)
    courses_df["Course Code"] = courses_df["Course Code"].str.lower()
    lecturers_df["Course Code"] = lecturers_df["Course Code"].str.lower()
    requests_df["Course Code"] = requests_df["Course Code"].str.lower()
    
    # Create unique section identifiers
    lecturers_df['Section_ID'] = lecturers_df['Course Code'] + '_' + lecturers_df['Section Number'].astype(str)
    
    # Extract all available blocks
    all_blocks = set()
    for blocks in courses_df["Available blocks"]:
        if isinstance(blocks, list):
            all_blocks.update(blocks)
        else:
            all_blocks.add(blocks)
    
    # Map priority to numeric values
    priority_map = {"Required": 3, "Requested": 2, "Recommended": 1}
    requests_df["Priority_Value"] = requests_df["Type"].map(priority_map)
    
    return courses_df, lecturers_df, requests_df, list(all_blocks)

def build_optimization_model(courses_df, lecturers_df, requests_df, all_blocks):
    # Create the model
    model = pl.LpProblem("Course_Scheduling", pl.LpMaximize)
    
    # Get unique students, courses, and sections
    students = requests_df["Student ID"].unique()
    course_sections = lecturers_df["Section_ID"].unique()
    professors = lecturers_df["Prof ID"].unique()
    
    # Create mapping from course codes to available blocks
    course_to_blocks = {}
    for _, course in courses_df.iterrows():
        code = course["Course Code"]
        if isinstance(course["Available blocks"], list):
            course_to_blocks[code] = course["Available blocks"]
        else:
            course_to_blocks[code] = [course["Available blocks"]]
    
    # Decision variables: x[student, section, block] = 1 if student is assigned to section in block
    x = {}
    for student in students:
        for section in course_sections:
            course_code = section.split('_')[0]
            if course_code in course_to_blocks:
                for block in course_to_blocks[course_code]:
                    x[(student, section, block)] = pl.LpVariable(
                        f"x_{student}_{section}_{block}", 
                        cat=pl.LpBinary
                    )
    
    # Professor assignment variables: y[professor, section, block] = 1 if professor teaches section in block
    y = {}
    for prof in professors:
        for section in course_sections:
            course_code = section.split('_')[0]
            if course_code in course_to_blocks:
                for block in course_to_blocks[course_code]:
                    y[(prof, section, block)] = pl.LpVariable(
                        f"y_{prof}_{section}_{block}", 
                        cat=pl.LpBinary
                    )
    
    # Objective function: Maximize priority-weighted student assignments
    objective = pl.lpSum(
        x[(student, section, block)] * 
        requests_df.loc[
            (requests_df["Student ID"] == student) & 
            (requests_df["Course Code"] == section.split('_')[0]), 
            "Priority_Value"
        ].values[0] 
        for student in students 
        for section in course_sections 
        for block in all_blocks 
        if (student, section, block) in x
    )
    
    model += objective
    
    # Constraints
    
    # 1. A student can only be in one course per block
    for student in students:
        for block in all_blocks:
            model += pl.lpSum(
                x[(student, section, block)] 
                for section in course_sections 
                if (student, section, block) in x
            ) <= 1
    
    # 2. A professor can only teach one section per block
    for prof in professors:
        for block in all_blocks:
            model += pl.lpSum(
                y[(prof, section, block)] 
                for section in course_sections 
                if (prof, section, block) in y
            ) <= 1
    
    # 3. Section size limits
    for section in course_sections:
        course_code = section.split('_')[0]
        if course_code in course_to_blocks:
            for block in course_to_blocks[course_code]:
                # Get min, target, max section sizes
                min_size = courses_df.loc[courses_df["Course Code"] == course_code, "Minimum section size"].values[0]
                max_size = courses_df.loc[courses_df["Course Code"] == course_code, "Maximum section size"].values[0]
                
                # Section must have at least min_size students and at most max_size
                section_size = pl.lpSum(
                    x[(student, section, block)] 
                    for student in students 
                    if (student, section, block) in x
                )
                
                # If section is used (at least one student), enforce minimum size
                section_used = pl.LpVariable(f"used_{section}_{block}", cat=pl.LpBinary)
                
                # If section_used is 1, then section_size >= min_size
                model += section_size >= min_size * section_used
                
                # If section_size > 0, then section_used must be 1
                model += section_size <= max_size * section_used
                
                # Ensure a section has exactly one professor if it's used
                model += pl.lpSum(
                    y[(prof, section, block)] 
                    for prof in professors 
                    if (prof, section, block) in y
                ) == section_used
    
    # 4. Each student should get their required courses
    for _, request in requests_df.iterrows():
        if request["Type"] == "Required":
            student = request["Student ID"]
            course_code = request["Course Code"]
            
            # Student must be assigned to at least one section of a required course
            model += pl.lpSum(
                x[(student, section, block)] 
                for section in course_sections 
                if section.split('_')[0] == course_code
                for block in all_blocks 
                if (student, section, block) in x
            ) >= 1
    
    return model

def solve_and_generate_schedules(model, courses_df, lecturers_df, requests_df, all_blocks):
    # Solve the model
    model.solve(pl.PULP_CBC_CMD(msg=False))
    
    print(f"Status: {pl.LpStatus[model.status]}")
    print(f"Objective value: {pl.value(model.objective)}")
    
    # Extract results
    student_schedules = {}
    professor_schedules = {}
    
    # Extract student schedules
    for var in model.variables():
        if var.name.startswith('x_') and var.value() == 1:
            _, student, section, block = var.name.split('_')
            course_code = section.split('_')[0]
            section_num = section.split('_')[1]
            
            if student not in student_schedules:
                student_schedules[student] = []
            
            course_title = courses_df.loc[courses_df["Course Code"] == course_code, "Course Title"].values[0]
            professor_id = lecturers_df.loc[
                (lecturers_df["Course Code"] == course_code) & 
                (lecturers_df["Section Number"] == int(section_num)), 
                "Prof ID"
            ].values[0]
            
            student_schedules[student].append({
                "Student ID": student,
                "Course Code": course_code,
                "Course Title": course_title,
                "Section": section_num,
                "Block": block,
                "Professor ID": professor_id
            })
    
    # Extract professor schedules
    for var in model.variables():
        if var.name.startswith('y_') and var.value() == 1:
            _, prof, section, block = var.name.split('_')
            course_code = section.split('_')[0]
            section_num = section.split('_')[1]
            
            if prof not in professor_schedules:
                professor_schedules[prof] = []
            
            course_title = courses_df.loc[courses_df["Course Code"] == course_code, "Course Title"].values[0]
            
            professor_schedules[prof].append({
                "Professor ID": prof,
                "Course Code": course_code,
                "Course Title": course_title,
                "Section": section_num,
                "Block": block
            })
    
    # Generate statistics
    total_requests = len(requests_df)
    fulfilled_required = 0
    fulfilled_requested = 0
    fulfilled_recommended = 0
    
    for student in student_schedules:
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
    
    total_required = len(requests_df[requests_df["Type"] == "Required"])
    total_requested = len(requests_df[requests_df["Type"] == "Requested"])
    total_recommended = len(requests_df[requests_df["Type"] == "Recommended"])
    
    # Save results to JSON files
    with open("student_schedules.json", "w") as f:
        json.dump(student_schedules, f, indent=2)
    
    with open("professor_schedules.json", "w") as f:
        json.dump(professor_schedules, f, indent=2)
    
    # Print statistics
    print("\nScheduling Statistics:")
    print(f"Total student requests: {total_requests}")
    print(f"Required courses fulfilled: {fulfilled_required}/{total_required} ({fulfilled_required/total_required*100:.2f}%)")
    print(f"Requested courses fulfilled: {fulfilled_requested}/{total_requested} ({fulfilled_requested/total_requested*100:.2f}%)")
    print(f"Recommended courses fulfilled: {fulfilled_recommended}/{total_recommended} ({fulfilled_recommended/total_recommended*100:.2f}%)")
    
    return student_schedules, professor_schedules


def main():
    print("Loading data...")
    course_list, lecturer_details, student_requests = load_data()
    
    print("Preprocessing data...")
    courses_df, lecturers_df, requests_df, all_blocks = preprocess_data(course_list, lecturer_details, student_requests)
    
    print("Building optimization model...")
    model = build_optimization_model(courses_df, lecturers_df, requests_df, all_blocks)
    
    print("Solving model and generating schedules...")
    student_schedules, professor_schedules = solve_and_generate_schedules(model, courses_df, lecturers_df, requests_df, all_blocks)
    
    print("Done! Results saved to student_schedules.json and professor_schedules.json")

if __name__ == "__main__":
    main()
