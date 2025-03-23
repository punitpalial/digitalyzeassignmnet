import pandas as pd
import json
import numpy as np


def convert(obj):
    if isinstance(obj, (np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, list):
        return [convert(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert(value) for key, value in obj.items()}
    else:
        return obj
    
excel_file = "dataset.xlsx"

lecturer_df = pd.read_excel(excel_file, sheet_name="Lecturer Details")
rooms_df = pd.read_excel(excel_file, sheet_name="Rooms data")
course_list_df = pd.read_excel(excel_file, sheet_name="Course list")

merged_df = pd.merge(
    lecturer_df,
    rooms_df,
    how="left",
    left_on=["lecture Code", "Section number"],
    right_on=["Course Code", "Section number"]
)

final_df = pd.merge(
    merged_df,
    course_list_df,
    how="left",
    left_on="Course Code",
    right_on="Course code"
)

courses_json = {"courses": []}

for course_code, group in final_df.groupby("Course code"):
    course_entry = {
        "course_code": course_code,
        "title": group["Title"].iloc[0],
        "length": group["Length_x"].iloc[0],
        "priority": group["Priority"].iloc[0],
        "available_blocks": group["Available blocks"].iloc[0].split(", ") if pd.notna(group["Available blocks"].iloc[0]) else [],
        "unavailable_blocks": group["Unavailable blocks"].iloc[0].split(", ") if pd.notna(group["Unavailable blocks"].iloc[0]) else [],
        "minimum_section_size": group["Minimum section size"].iloc[0],
        "target_section_size": group["Target section size"].iloc[0],
        "maximum_section_size": group["Maximum section size"].iloc[0],
        "number_of_sections": group["Number of sections"].iloc[0],
        "total_credits": group["Total credits"].iloc[0],
        "sections": []
    }

    for _, row in group.iterrows():
        section_entry = {
            "section_number": row["Section number"],
            "lecturer_id": row["Lecturer ID"],
            "start_term": row["Start Term"],
            "room_number": row["Room Number"],
            "year": row[" Year"],
            "term_description": row["Term Description"],
            "term_name": row["Term name"]
        }
        course_entry["sections"].append(section_entry)

    courses_json["courses"].append(convert(course_entry))


json_output = json.dumps(courses_json, indent=2)
print(json_output)


with open("merged_course_schedule.json", "w") as f:
    f.write(json_output)