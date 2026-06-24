import os
import re
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for

from db import get_db_connection

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

STATUS_OPTIONS = ["Active", "Graduated", "Suspended"]
GENDER_OPTIONS = ["Male", "Female", "Other"]
SEMESTER_OPTIONS = ["Fall", "Spring", "Summer"]
LETTER_OPTIONS = ["A", "B", "C", "D", "F", "Incomplete"]


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _validate_student(data):
    errors = []
    if not data.get("first_name"):
        errors.append("First name is required.")
    if not data.get("last_name"):
        errors.append("Last name is required.")
    if not data.get("national_id"):
        errors.append("National ID is required.")
    if not data.get("email") or not EMAIL_RE.match(data["email"]):
        errors.append("A valid email address is required.")
    if not data.get("date_of_birth"):
        errors.append("Date of birth is required.")
    if data.get("gender") not in GENDER_OPTIONS:
        errors.append("Gender selection is invalid.")
    if not data.get("department"):
        errors.append("Department is required.")
    if data.get("status") not in STATUS_OPTIONS:
        errors.append("Status selection is invalid.")
    try:
        gpa = float(data.get("gpa", "0"))
        if gpa < 0 or gpa > 4:
            errors.append("GPA must be between 0.00 and 4.00.")
    except ValueError:
        errors.append("GPA must be a decimal number.")
    return errors


def _validate_course(data):
    errors = []
    if not data.get("course_code"):
        errors.append("Course code is required.")
    if not data.get("course_name"):
        errors.append("Course name is required.")
    try:
        credit = int(data.get("credit_hours", 0))
        if credit < 1 or credit > 6:
            errors.append("Credit hours must be between 1 and 6.")
    except ValueError:
        errors.append("Credit hours must be a number.")
    if not data.get("instructor_name"):
        errors.append("Instructor name is required.")
    if not data.get("department"):
        errors.append("Department is required.")
    if data.get("semester") not in SEMESTER_OPTIONS:
        errors.append("Semester selection is invalid.")
    if not data.get("academic_year"):
        errors.append("Academic year is required.")
    return errors


def _validate_enrollment(data):
    errors = []
    if not data.get("student_id"):
        errors.append("Student selection is required.")
    if not data.get("course_id"):
        errors.append("Course selection is required.")
    if data.get("grade"):
        try:
            grade = float(data.get("grade"))
            if grade < 0 or grade > 100:
                errors.append("Grade must be between 0 and 100.")
        except ValueError:
            errors.append("Grade must be a number.")
    if data.get("letter_grade") and data.get("letter_grade") not in LETTER_OPTIONS:
        errors.append("Letter grade selection is invalid.")
    return errors


def _get_counts():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS count FROM students")
            students_count = cursor.fetchone()["count"]
            cursor.execute("SELECT COUNT(*) AS count FROM courses")
            courses_count = cursor.fetchone()["count"]
            cursor.execute("SELECT COUNT(*) AS count FROM enrollments")
            enrollments_count = cursor.fetchone()["count"]
    return students_count, courses_count, enrollments_count


def _get_students(search=None):
    query = "SELECT * FROM students"
    params = []
    if search:
        query += " WHERE first_name LIKE %s OR last_name LIKE %s OR national_id LIKE %s OR department LIKE %s"
        term = f"%{search}%"
        params = [term, term, term, term]
    query += " ORDER BY student_id DESC"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()


def _get_courses():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM courses ORDER BY course_id DESC")
            return cursor.fetchall()


def _get_enrollments():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT e.*, s.first_name, s.last_name, c.course_code, c.course_name "
                "FROM enrollments e "
                "JOIN students s ON s.student_id = e.student_id "
                "JOIN courses c ON c.course_id = e.course_id "
                "ORDER BY e.enrollment_id DESC"
            )
            return cursor.fetchall()


def _get_student(student_id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
            return cursor.fetchone()


def _get_course(course_id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM courses WHERE course_id = %s", (course_id,))
            return cursor.fetchone()


def _get_student_enrollments(student_id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT e.*, c.course_code, c.course_name, c.credit_hours "
                "FROM enrollments e "
                "JOIN courses c ON c.course_id = e.course_id "
                "WHERE e.student_id = %s "
                "ORDER BY e.enrolled_at DESC",
                (student_id,),
            )
            return cursor.fetchall()


@app.route("/")
def index():
    counts = _get_counts()
    students = _get_students()
    courses = _get_courses()
    enrollments = _get_enrollments()
    return render_template(
        "index.html",
        students_count=counts[0],
        courses_count=counts[1],
        enrollments_count=counts[2],
        recent_students=students[:5],
        recent_courses=courses[:5],
        recent_enrollments=enrollments[:5],
    )


@app.route("/students")
def students():
    search = request.args.get("search", "")
    students_list = _get_students(search)
    return render_template(
        "students.html",
        students=students_list,
        search=search,
    )


@app.route("/students/add", methods=["GET", "POST"])
def student_add():
    if request.method == "POST":
        data = request.form.to_dict()
        errors = _validate_student(data)
        if errors:
            for err in errors:
                flash(err, "error")
        else:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    try:
                        cursor.execute(
                            "INSERT INTO students (first_name, last_name, national_id, email, date_of_birth, gender, department, enrollment_date, gpa, status) "
                            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                            (
                                data["first_name"],
                                data["last_name"],
                                data["national_id"],
                                data["email"],
                                data["date_of_birth"],
                                data["gender"],
                                data["department"],
                                data.get("enrollment_date") or datetime.now().date(),
                                _to_float(data.get("gpa", "0.00")),
                                data["status"],
                            ),
                        )
                        flash("Student added successfully.", "success")
                        return redirect(url_for("students"))
                    except Exception as exc:
                        flash(str(exc), "error")
    return render_template(
        "student_form.html",
        student={},
        genders=GENDER_OPTIONS,
        statuses=STATUS_OPTIONS,
        action_url=url_for("student_add"),
        form_title="Add Student",
    )


@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
def student_edit(student_id):
    student = _get_student(student_id)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("students"))
    if request.method == "POST":
        data = request.form.to_dict()
        errors = _validate_student(data)
        if errors:
            for err in errors:
                flash(err, "error")
        else:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    try:
                        cursor.execute(
                            "UPDATE students SET first_name=%s, last_name=%s, national_id=%s, email=%s, date_of_birth=%s, gender=%s, department=%s, enrollment_date=%s, gpa=%s, status=%s WHERE student_id=%s",
                            (
                                data["first_name"],
                                data["last_name"],
                                data["national_id"],
                                data["email"],
                                data["date_of_birth"],
                                data["gender"],
                                data["department"],
                                data["enrollment_date"],
                                _to_float(data.get("gpa", "0.00")),
                                data["status"],
                                student_id,
                            ),
                        )
                        flash("Student updated successfully.", "success")
                        return redirect(url_for("students"))
                    except Exception as exc:
                        flash(str(exc), "error")
    student_enrollments = _get_student_enrollments(student_id)
    return render_template(
        "student_form.html",
        student=student,
        genders=GENDER_OPTIONS,
        statuses=STATUS_OPTIONS,
        action_url=url_for("student_edit", student_id=student_id),
        form_title="Edit Student",
        student_enrollments=student_enrollments,
    )


@app.route("/students/<int:student_id>/delete", methods=["POST"])
def student_delete(student_id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM students WHERE student_id=%s", (student_id,))
    flash("Student removed successfully.", "success")
    return redirect(url_for("students"))


@app.route("/courses")
def courses():
    courses_list = _get_courses()
    return render_template("courses.html", courses=courses_list)


@app.route("/courses/add", methods=["GET", "POST"])
def course_add():
    if request.method == "POST":
        data = request.form.to_dict()
        errors = _validate_course(data)
        if errors:
            for err in errors:
                flash(err, "error")
        else:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    try:
                        cursor.execute(
                            "INSERT INTO courses (course_code, course_name, credit_hours, instructor_name, department, semester, academic_year) "
                            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                            (
                                data["course_code"],
                                data["course_name"],
                                int(data["credit_hours"]),
                                data["instructor_name"],
                                data["department"],
                                data["semester"],
                                int(data["academic_year"]),
                            ),
                        )
                        flash("Course added successfully.", "success")
                        return redirect(url_for("courses"))
                    except Exception as exc:
                        flash(str(exc), "error")
    return render_template(
        "course_form.html",
        course={},
        semesters=SEMESTER_OPTIONS,
        action_url=url_for("course_add"),
        form_title="Add Course",
    )


@app.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
def course_edit(course_id):
    course = _get_course(course_id)
    if not course:
        flash("Course not found.", "error")
        return redirect(url_for("courses"))
    if request.method == "POST":
        data = request.form.to_dict()
        errors = _validate_course(data)
        if errors:
            for err in errors:
                flash(err, "error")
        else:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    try:
                        cursor.execute(
                            "UPDATE courses SET course_code=%s, course_name=%s, credit_hours=%s, instructor_name=%s, department=%s, semester=%s, academic_year=%s WHERE course_id=%s",
                            (
                                data["course_code"],
                                data["course_name"],
                                int(data["credit_hours"]),
                                data["instructor_name"],
                                data["department"],
                                data["semester"],
                                int(data["academic_year"]),
                                course_id,
                            ),
                        )
                        flash("Course updated successfully.", "success")
                        return redirect(url_for("courses"))
                    except Exception as exc:
                        flash(str(exc), "error")
    return render_template(
        "course_form.html",
        course=course,
        semesters=SEMESTER_OPTIONS,
        action_url=url_for("course_edit", course_id=course_id),
        form_title="Edit Course",
    )


@app.route("/courses/<int:course_id>/delete", methods=["POST"])
def course_delete(course_id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM courses WHERE course_id=%s", (course_id,))
    flash("Course removed successfully.", "success")
    return redirect(url_for("courses"))


@app.route("/enrollments")
def enrollments():
    enrollments_list = _get_enrollments()
    return render_template(
        "enrollments.html",
        enrollments=enrollments_list,
    )


@app.route("/enrollments/add", methods=["GET", "POST"])
def enrollment_add():
    students = _get_students()
    courses = _get_courses()
    if request.method == "POST":
        data = request.form.to_dict()
        errors = _validate_enrollment(data)
        if errors:
            for err in errors:
                flash(err, "error")
        else:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    try:
                        cursor.execute(
                            "INSERT INTO enrollments (student_id, course_id, grade, letter_grade) VALUES (%s,%s,%s,%s)",
                            (
                                int(data["student_id"]),
                                int(data["course_id"]),
                                data["grade"] or None,
                                data["letter_grade"] or None,
                            ),
                        )
                        flash("Student enrolled successfully.", "success")
                        return redirect(url_for("enrollments"))
                    except Exception as exc:
                        flash(str(exc), "error")
    return render_template(
        "enrollment_form.html",
        students=students,
        courses=courses,
        enrollment={},
        letter_options=LETTER_OPTIONS,
        action_url=url_for("enrollment_add"),
        form_title="Enroll Student",
    )


@app.route("/enrollments/<int:enrollment_id>/edit", methods=["GET", "POST"])
def enrollment_edit(enrollment_id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM enrollments WHERE enrollment_id=%s", (enrollment_id,))
            enrollment = cursor.fetchone()
    if not enrollment:
        flash("Enrollment not found.", "error")
        return redirect(url_for("enrollments"))
    if request.method == "POST":
        data = request.form.to_dict()
        errors = _validate_enrollment(data)
        if errors:
            for err in errors:
                flash(err, "error")
        else:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    try:
                        cursor.execute(
                            "UPDATE enrollments SET grade=%s, letter_grade=%s WHERE enrollment_id=%s",
                            (
                                data["grade"] or None,
                                data["letter_grade"] or None,
                                enrollment_id,
                            ),
                        )
                        flash("Enrollment updated successfully.", "success")
                        return redirect(url_for("enrollments"))
                    except Exception as exc:
                        flash(str(exc), "error")
    students = _get_students()
    courses = _get_courses()
    return render_template(
        "enrollment_form.html",
        students=students,
        courses=courses,
        enrollment=enrollment,
        letter_options=LETTER_OPTIONS,
        action_url=url_for("enrollment_edit", enrollment_id=enrollment_id),
        form_title="Edit Enrollment",
    )


@app.route("/enrollments/<int:enrollment_id>/delete", methods=["POST"])
def enrollment_delete(enrollment_id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM enrollments WHERE enrollment_id=%s", (enrollment_id,))
    flash("Enrollment removed successfully.", "success")
    return redirect(url_for("enrollments"))


@app.route("/students/<int:student_id>")
def student_detail(student_id):
    student = _get_student(student_id)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("students"))
    student_enrollments = _get_student_enrollments(student_id)
    return render_template("student_detail.html", student=student, student_enrollments=student_enrollments)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
