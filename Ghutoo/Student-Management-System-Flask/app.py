"""Student Management System web application."""

import csv
import re
import io
import math
import sqlite3
from pathlib import Path

from flask import Flask, abort, make_response, redirect, render_template, request, url_for
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "students.db"
app = Flask(__name__, template_folder=".", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

STUDENT_FIELDS = (
    "name", "usn", "gender", "dob", "blood_group", "email", "phone",
    "address", "city", "state", "pincode", "department", "semester",
    "section", "batch", "father_name", "mother_name", "parent_phone",
    "github", "linkedin",
)
REQUIRED_IMPORT_FIELDS = set(STUDENT_FIELDS) - {"github", "linkedin"}
CSV_HEADER_ALIASES = {
    "date of birth": "dob", "dateofbirth": "dob", "blood group": "blood_group",
    "pin code": "pincode", "pin": "pincode", "father name": "father_name",
    "mother name": "mother_name", "parent phone": "parent_phone",
}


def connect_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def student_values(form):
    fields = (
        "name", "usn", "gender", "dob", "blood_group", "email", "phone",
        "address", "city", "state", "pincode", "department", "semester",
        "section", "batch", "father_name", "mother_name", "parent_phone",
        "github", "linkedin",
    )
    values = [form.get(field, "").strip() for field in fields]
    values[12] = int(values[12])
    return values


def normalize_csv_header(header):
    normalized = re.sub(r"[_\s]+", " ", (header or "").strip().lstrip("\ufeff").lower())
    return CSV_HEADER_ALIASES.get(normalized, normalized.replace(" ", "_"))


def validate_import_row(row, line_number):
    values = {field: (row.get(field) or "").strip() for field in STUDENT_FIELDS}
    errors = []
    for field in REQUIRED_IMPORT_FIELDS:
        if not values[field]:
            errors.append(f"{field.replace('_', ' ').title()} is required")
    if values["gender"] and values["gender"].casefold() not in {"male", "female", "other"}:
        errors.append("Gender must be Male, Female, or Other")
    if values["semester"]:
        try:
            semester = int(values["semester"])
            if not 1 <= semester <= 8:
                errors.append("Semester must be between 1 and 8")
            values["semester"] = semester
        except ValueError:
            errors.append("Semester must be a number from 1 to 8")
    if errors:
        return None, f"Row {line_number}: " + "; ".join(errors)
    values["gender"] = values["gender"].title()
    values["github"] = values["github"] or None
    values["linkedin"] = values["linkedin"] or None
    return values, None


@app.route("/")
def home():
    with connect_db() as db:
        total_students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        departments = db.execute("SELECT COUNT(DISTINCT department) FROM students").fetchone()[0]
    return render_template("index.html", total_students=total_students, total_departments=departments)


@app.route("/dashboard")
def dashboard():
    with connect_db() as db:
        stats = db.execute("""SELECT COUNT(*) AS total,
            COUNT(DISTINCT department) AS departments,
            SUM(gender = 'Male') AS male, SUM(gender = 'Female') AS female,
            SUM(gender = 'Other') AS other,
            SUM(semester IN (7, 8)) AS final_year FROM students""").fetchone()
        department_stats = db.execute("SELECT department, COUNT(*) AS count FROM students GROUP BY department ORDER BY count DESC").fetchall()
    return render_template("dashboard.html", stats=stats, department_stats=department_stats)


@app.route("/students")
def students():
    search = request.args.get("search", "").strip()
    department = request.args.get("department", "").strip()
    sort = request.args.get("sort", "name")
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 30
    order_by = {"name": "name COLLATE NOCASE", "semester": "semester", "department": "department"}.get(sort, "name COLLATE NOCASE")
    where = "WHERE 1=1"
    params = []
    if search:
        where += " AND (name LIKE ? OR usn LIKE ? OR department LIKE ? OR CAST(semester AS TEXT) LIKE ? OR city LIKE ? OR state LIKE ? OR section LIKE ?)"
        params.extend([f"%{search}%"] * 7)
    if department:
        where += " AND department = ?"
        params.append(department)
    with connect_db() as db:
        total = db.execute(f"SELECT COUNT(*) FROM students {where}", params).fetchone()[0]
        rows = db.execute(f"SELECT * FROM students {where} ORDER BY {order_by} LIMIT ? OFFSET ?", [*params, per_page, (page - 1) * per_page]).fetchall()
        departments = [row[0] for row in db.execute("SELECT DISTINCT department FROM students ORDER BY department")]
    return render_template("students.html", students=rows, search=search, department=department, sort=sort,
                           page=page, total_pages=max(1, math.ceil(total / per_page)), total=total, departments=departments)


@app.route("/export-csv")
def export_csv():
    with connect_db() as db:
        rows = db.execute("SELECT * FROM students ORDER BY name COLLATE NOCASE").fetchall()
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "USN", "Gender", "DOB", "Blood Group", "Email", "Phone", "Address", "City", "State", "Pincode", "Department", "Semester", "Section", "Batch", "Father Name", "Mother Name", "Parent Phone", "GitHub", "LinkedIn"])
    writer.writerows([tuple(row) for row in rows])
    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=students.csv"
    return response


@app.route("/import-template")
def import_template():
    headers = [
        "Name", "USN", "Gender", "DOB", "Blood Group", "Email", "Phone",
        "Address", "City", "State", "Pincode", "Department", "Semester",
        "Section", "Batch", "Father Name", "Mother Name", "Parent Phone",
        "GitHub", "LinkedIn",
    ]
    output = io.StringIO(newline="")
    csv.writer(output).writerow(headers)
    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=student_import_template.csv"
    return response


@app.route("/import-students", methods=["GET", "POST"])
def import_students():
    if request.method == "GET":
        return render_template("import_students.html")

    upload = request.files.get("csv_file")
    if upload is None or not upload.filename:
        return render_template("import_students.html", error="Choose a CSV file to upload.")
    if not upload.filename.lower().endswith(".csv"):
        return render_template("import_students.html", error="Please upload a .csv file.")

    try:
        text = upload.stream.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        if not reader.fieldnames:
            raise ValueError("The CSV file is empty or has no header row.")
        field_map = {header: normalize_csv_header(header) for header in reader.fieldnames}
        missing = sorted(REQUIRED_IMPORT_FIELDS - set(field_map.values()))
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(field.replace("_", " ") for field in missing))
        rows = []
        for raw_row in reader:
            if not raw_row or all(not (value or "").strip() for value in raw_row.values()):
                continue
            normalized_row = {field_map[key]: value for key, value in raw_row.items() if key in field_map}
            rows.append((reader.line_num, normalized_row))
    except (UnicodeDecodeError, csv.Error, ValueError) as error:
        return render_template("import_students.html", error=f"Could not read this CSV: {error}")

    added = 0
    updated = 0
    errors = []
    columns = ", ".join(STUDENT_FIELDS)
    placeholders = ", ".join("?" for _ in STUDENT_FIELDS)
    updates = ", ".join(f"{field}=excluded.{field}" for field in STUDENT_FIELDS if field != "usn")
    statement = f"INSERT INTO students ({columns}) VALUES ({placeholders}) ON CONFLICT(usn) DO UPDATE SET {updates}"

    with connect_db() as db:
        for line_number, row in rows:
            values, error = validate_import_row(row, line_number)
            if error:
                errors.append(error)
                continue
            try:
                existing = db.execute("SELECT 1 FROM students WHERE usn = ?", (values["usn"],)).fetchone()
                db.execute(statement, [values[field] for field in STUDENT_FIELDS])
                if existing:
                    updated += 1
                else:
                    added += 1
            except sqlite3.IntegrityError as error:
                errors.append(f"Row {line_number}: {error}")

    return render_template("import_students.html", added=added, updated=updated,
                           skipped=len(errors), errors=errors, processed=True)


@app.route("/export-pdf")
def export_pdf():
    with connect_db() as db:
        rows = db.execute("SELECT name, usn, department, semester, section, city, phone FROM students ORDER BY name COLLATE NOCASE").fetchall()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="Student directory")
    data = [["Name", "USN", "Department", "Semester", "Section", "City", "Phone"], *[list(row) for row in rows]]
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#142d4e")),
                               ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#d7e0ea")),
                               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6fa")]),
                               ("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")] ))
    doc.build([table])
    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=students.pdf"
    return response


@app.route("/add-student", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        values = student_values(request.form)
        with connect_db() as db:
            db.execute("""INSERT INTO students (name, usn, gender, dob, blood_group, email, phone, address, city, state,
                pincode, department, semester, section, batch, father_name, mother_name, parent_phone, github, linkedin)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", values)
        return redirect(url_for("students"))
    return render_template("add_students.html", student=None)


@app.route("/edit-student/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    with connect_db() as db:
        student = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if student is None:
            abort(404)
        if request.method == "POST":
            values = student_values(request.form)
            db.execute("""UPDATE students SET name=?, usn=?, gender=?, dob=?, blood_group=?, email=?, phone=?, address=?,
                city=?, state=?, pincode=?, department=?, semester=?, section=?, batch=?, father_name=?, mother_name=?,
                parent_phone=?, github=?, linkedin=? WHERE id=?""", [*values, student_id])
            return redirect(url_for("student_profile", student_id=student_id))
    return render_template("edit_student.html", student=student)


@app.route("/student-profile/<int:student_id>")
def student_profile(student_id):
    with connect_db() as db:
        student = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if student is None:
        abort(404)
    return render_template("student_profile.html", student=student)


@app.route("/download-pdf/<int:student_id>")
def download_pdf(student_id):
    with connect_db() as db:
        student = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if student is None:
        abort(404)
    labels = ["Name", "USN", "Gender", "Date of birth", "Blood group", "Email", "Phone", "Address", "City", "State", "PIN code", "Department", "Semester", "Section", "Batch", "Father", "Mother", "Parent phone", "GitHub", "LinkedIn"]
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    title = styles["Heading1"]
    title.alignment = TA_CENTER
    data = [[Paragraph(f"<b>{label}</b>", styles["BodyText"]), Paragraph(str(student[index + 1] or "—"), styles["BodyText"])] for index, label in enumerate(labels)]
    table = Table(data, colWidths=[130, 370])
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#d7e0ea")), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef3f8")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 8)]))
    SimpleDocTemplate(buffer, pagesize=A4, title=f"{student['name']} profile").build([Paragraph("Student profile", title), Spacer(1, 18), table])
    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={student['usn']}_profile.pdf"
    return response


@app.route("/delete-student/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    with connect_db() as db:
        db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    return redirect(url_for("students"))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=False)
