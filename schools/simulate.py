# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import sys
import frappe
import random
import string
from frappe.utils import cstr
from frappe.utils.make_random import get_random
from schools.api import enroll_student, get_student_group_students, make_attendance_records, get_fee_structure, get_fee_amount
import datetime
from datetime import timedelta

def simulate():
	start_date = frappe.utils.add_days(frappe.utils.nowdate(), -30)
	current_date = frappe.utils.getdate(start_date)
	runs_for = frappe.utils.date_diff(frappe.utils.nowdate(), current_date)

	print ("Approving Students...")
	for d in xrange(200):
		approve_random_student_applicant()
		enroll_random_student(current_date)

	print ("Making Course Schedules...")

	cd = current_date
	for i in xrange(1,4):
		make_course_schedule(cd, frappe.utils.add_days(cd, 39))
		cd = frappe.utils.add_days(cd, 40)
		make_examinations(cd.year,cd.month,cd.day)
		cd = frappe.utils.add_days(cd, 1)

	for i in xrange(runs_for):
		sys.stdout.write("\rSimulating {0}".format(current_date.strftime("%Y-%m-%d")))
		sys.stdout.flush()
		frappe.local.current_date = current_date

		mark_student_attendance(current_date)

		current_date = frappe.utils.add_days(current_date, 1)
	submit_fees()

def approve_random_student_applicant():
	random_student = get_random("Student Applicant", {"application_status": "Applied"})
	if random_student:
		status = ["Approved", "Rejected"]
		frappe.db.set_value("Student Applicant", random_student, "application_status", status[weighted_choice([9,3])])

def enroll_random_student(current_date):
	random_student = get_random("Student Applicant", {"application_status": "Approved"})
	if random_student:
		enrollment = enroll_student(random_student)
		enrollment.academic_year = get_random("Academic Year")
		enrollment.enrollment_date = current_date
		enrollment.submit()
		frappe.db.commit()

		assign_student_group(enrollment.student, enrollment.program)

def submit_fees():
	for i in xrange(1,40):
		random_student = random.choice(frappe.get_list("Program Enrollment" , fields= ("student" , "student_name", "program")))
		fee = frappe.new_doc("Fees")
		fee.student = random_student.student
		fee.student_name = random_student.student_name
		fee.academic_term = get_random("Academic Term")
		fee.academic_year = get_random("Academic Year")
		fee.program = random_student.program
		fee.fee_structure = get_fee_structure(fee.program, fee.academic_term)
		temp = get_fee_amount(fee.fee_structure)
		if temp is None:
			continue
		for i in temp:
			fee.append("amount", i)
		fee.insert()
		if not weighted_choice([8,4]):
			fee.submit()

def assign_student_group(student, program):
	courses = []
	for d in frappe.get_list("Program Course", fields=("course"), filters={"parent": program }):
		courses.append(d.course)

	for d in xrange(3):
		course = random.choice(courses)
		random_sg = get_random("Student Group", {"course": course})
		if random_sg:
			student_group = frappe.get_doc("Student Group", random_sg)
			student_group.append("students", {"student": student})
			student_group.save()
		courses.remove(course)

def make_course_schedule(start_date, end_date):
	for d in frappe.db.get_list("Student Group"):
		cs = frappe.new_doc("Scheduling Tool")
		cs.student_group = d.name
		cs.room = get_random("Room")
		cs.instructor = get_random("Instructor")
		cs.course_start_date = cstr(start_date)
		cs.course_end_date = cstr(end_date)
		day = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
		for x in xrange(3):
			random_day = random.choice(day)
			cs.day = random_day
			cs.from_time = timedelta(hours=(random.randrange(7, 17,1)))
			cs.to_time = cs.from_time + timedelta(hours=1)
			cs.schedule_course()
			day.remove(random_day)


def mark_student_attendance(current_date):
	status = ["Present", "Absent"]
	for d in frappe.db.get_list("Course Schedule", filters={"schedule_date": current_date}, fields=("name", "student_group")):
		students = get_student_group_students(d.student_group)
		for stud in students:
			make_attendance_records(stud.student, stud.student_name, d.name, status[weighted_choice([9,4])])

def weighted_choice(weights):
	totals = []
	running_total = 0

	for w in weights:
		running_total += w
		totals.append(running_total)

	rnd = random.random() * running_total
	for i, total in enumerate(totals):
		if rnd < total:
			return i

def make_examinations(year,month,day):
	for i in xrange(1,9):
		exam = frappe.new_doc("Examination")
		temp_sg = frappe.db.get_list("Student Group" , fields=("course" , "name"))
		exam.course = temp_sg[i].course
		exam.student_group = temp_sg[i].name
		temp_inst = frappe.db.get_list("Instructor" , fields = ("instructor_name" , "name"))
		exam.exam_name = exam.student_group + "-" + str(month) + "/" + str(year)
		exam.exam_code = id_generator()
		t1 = temp_inst[i]
		t2 = temp_inst[-i]
		exam.supervisor = t1.name
		exam.supervisor_name = t1.instructor_name
		exam.examiner = t2.name
		exam.examiner_name = t2.instructor_name
		room = frappe.db.get_list("Room")
		exam.room = room[i].name
		exam.schedule_date = datetime.date(year,month,day)
		exam.from_time = datetime.datetime(year,month,day,random.randint(10,14),0,0)
		exam.to_time = exam.from_time + timedelta(hours = random.randint(1,3))
		exam.save()
		if i% 2 is 0:
			exam.submit()

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
	return ''.join(random.choice(chars) for _ in range(size))
