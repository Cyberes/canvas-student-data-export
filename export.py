import json
import os
from http.cookiejar import MozillaCookieJar
from pathlib import Path

import jsonpickle
import yaml
from canvasapi import Canvas

from module.const import COURSES_TO_SKIP, DL_LOCATION
from module.download_canvas import download_assignment_pages, download_course_announcement_pages, download_course_discussion_pages, download_course_files, download_course_home_page_html, download_course_html, download_course_module_pages, download_submission_attachments
from module.get_canvas import find_course_announcements, find_course_assignments, find_course_discussions, find_course_modules, find_course_pages
from module.items import CourseView
from module.user_files import download_user_files

with open("credentials.yaml", 'r') as f:
    credentials = yaml.full_load(f)
API_URL = credentials["API_URL"]
API_KEY = credentials["API_KEY"]
USER_ID = credentials["USER_ID"]
COOKIES_PATH = str(Path(credentials["COOKIES_PATH"]).resolve().expanduser().absolute())
COOKIE_JAR = MozillaCookieJar(COOKIES_PATH)
COOKIE_JAR.load(ignore_discard=True, ignore_expires=True)


def export_all_course_data(c):
    json_data = json.dumps(json.loads(jsonpickle.encode(c, unpicklable=False)), indent=4)
    course_output_dir = os.path.join(DL_LOCATION, c.term, c.name)
    if not os.path.exists(course_output_dir):
        os.makedirs(course_output_dir)
    course_output_path = os.path.join(course_output_dir, c.name + ".json")
    with open(course_output_path, "w") as file:
        file.write(json_data)


if __name__ == "__main__":
    print("Welcome to the Canvas Student Data Export Tool")
    print("Creating output directory:", DL_LOCATION)
    if not os.path.exists(DL_LOCATION):
        os.makedirs(DL_LOCATION)

    print("Connecting to Canvas...")
    canvas = Canvas(API_URL, API_KEY)

    print('\nDownloading user files...')
    download_user_files(canvas, DL_LOCATION / 'User Files')
    print('')

    all_courses_views = []

    print("Getting list of all courses...")
    courses = canvas.get_courses(include="term")
    course_count = len(list(courses))

    skip = set(COURSES_TO_SKIP)

    if COOKIES_PATH:
        print("Fetching Courses...")
        download_course_html(API_URL, COOKIES_PATH)

    print('')

    for course in courses:
        if course.id in skip or not hasattr(course, "name") or not hasattr(course, "term"):
            continue

        course_view = CourseView(course)
        print(f"=== {course_view.term}: {course_view.name} ===")

        valid, r = course_view.test_course(API_URL, COOKIE_JAR)
        if not valid:
            print(f'Invalid course: {course_view.course_id} - {r}')
            continue

        course_view.assignments = find_course_assignments(course, USER_ID)
        course_view.announcements = find_course_announcements(course)
        course_view.discussions = find_course_discussions(course)
        course_view.pages = find_course_pages(course)
        course_view.modules = find_course_modules(course, course_view)
        all_courses_views.append(course_view)

        download_course_files(course, course_view)

        download_submission_attachments(course, course_view)

        print('Downloading course home page...')
        download_course_home_page_html(API_URL, course_view, COOKIES_PATH)

        download_assignment_pages(API_URL, course_view, COOKIES_PATH, COOKIE_JAR)

        download_course_module_pages(API_URL, course_view, COOKIES_PATH)

        download_course_announcement_pages(API_URL, course_view, COOKIES_PATH)

        download_course_discussion_pages(API_URL, course_view, COOKIES_PATH)

        print("Exporting all course data...")
        export_all_course_data(course_view)

        if course_count > 1:
            print('')

    # Remove elemnts from the course objects that can't be JSON serialized, then format it.
    json_str = json.dumps(json.loads(jsonpickle.encode(all_courses_views, unpicklable=False)), indent=4)

    all_output_path = os.path.join(DL_LOCATION, "all_output.json")
    with open(all_output_path, "w") as out_file:
        out_file.write(json_str)

    print("\nProcess complete. All canvas data exported!")
