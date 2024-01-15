import json
import os
from http.cookiejar import MozillaCookieJar
from pathlib import Path

import canvasapi
import jsonpickle
import requests
import yaml
from canvasapi import Canvas

from module.const import COURSES_TO_SKIP, DL_LOCATION
from module.download_canvas import download_assignment_pages, download_course_announcement_pages, download_course_discussion_pages, download_course_files, download_course_html, download_course_module_pages, download_submission_attachments, download_course_grades_page, download_course_home_page_html
from module.get_canvas import find_course_announcements, find_course_assignments, find_course_discussions, find_course_modules, find_course_pages
from module.items import CourseView
from module.user_files import download_user_files

SCRIPT_PATH = os.path.abspath(os.path.dirname(__file__))


def export_all_course_data(c):
    json_data = json.dumps(json.loads(jsonpickle.encode(c, unpicklable=False)), indent=4)
    course_output_dir = os.path.join(DL_LOCATION, c.term, c.name)
    if not os.path.exists(course_output_dir):
        os.makedirs(course_output_dir)
    course_output_path = os.path.join(course_output_dir, c.name + ".json")
    with open(course_output_path, "w") as file:
        file.write(json_data)


if __name__ == "__main__":
    # Startup checks.
    creds_file = Path(SCRIPT_PATH, 'credentials.yaml')
    if not creds_file.is_file():
        print('The credentials.yaml file does not exist:', creds_file)
        quit(1)

    with open("credentials.yaml", 'r') as f:
        credentials = yaml.full_load(f)

    API_URL = credentials["API_URL"]
    API_KEY = credentials["API_KEY"]
    USER_ID = credentials["USER_ID"]
    COOKIES_PATH = str(Path(credentials["COOKIES_PATH"]).resolve().expanduser().absolute())

    if not Path(COOKIES_PATH).is_file():
        print('The cookies file does not exist:', COOKIES_PATH)
        quit(1)

    COOKIE_JAR = MozillaCookieJar(COOKIES_PATH)
    COOKIE_JAR.load(ignore_discard=True, ignore_expires=True)

    # ==================================================================================================================
    # Initialization

    print("Welcome to the Canvas Student Data Export Tool")
    if not os.path.exists(DL_LOCATION):
        print("Creating output directory:", DL_LOCATION)
        os.makedirs(DL_LOCATION)

    if COOKIES_PATH:
        # Test the cookies.
        print("Authenticating with Canvas frontend...")

        # Requests takes a dict, not the MozillaCookieJar object.
        request_cookies = {c.name: c.value for c in COOKIE_JAR}

        r = requests.get(f'{API_URL}/profile', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}, cookies=request_cookies)
        if r.status_code != 200:
            print('Failed to fetch Canvas profile: got status code', r.status_code)
            quit(1)
        if not r.url.startswith(API_URL):
            print('Failed to fetch Canvas profile: client was redirected away from Canvas:')
            print(r.url)
            quit(1)
        if 'profileContent__Block' not in r.text:
            # TODO: add an arg to skip this check.
            print('Failed to test Canvas profile: could not find an element with the class "profileContent__Block". This could mean that your authentication is incorrect.')
            quit(1)

        # TODO: log debug status success here
    else:
        print('No cookies file specified! No HTML pages will be saved.')

    print("Authenticating with Canvas API...")
    canvas = Canvas(API_URL, API_KEY)
    courses = canvas.get_courses(include="term")
    try:
        course_count = len(list(courses))
    except canvasapi.exceptions.InvalidAccessToken as e:
        try:
            msg = e.message[0]['message']
        except:
            # Something went very wrong.
            msg = ''
        print('Failed to fetch courses from the Canvas API:', msg)
        quit(1)

    print('')

    skip = set(COURSES_TO_SKIP)

    # ==================================================================================================================
    # Exporting

    print("Downloading courses page...")
    download_course_html(API_URL, COOKIES_PATH)

    print('Downloading user files...')
    download_user_files(canvas, DL_LOCATION / 'User Files')
    print('')

    all_courses_views = []

    for course in courses:
        if course.id in skip or not hasattr(course, "name") or not hasattr(course, "term"):
            continue

        course_view = CourseView(course)
        print(f"=== {course_view.term}: {course_view.name} ===")

        valid, r = course_view.test_course(API_URL, COOKIE_JAR)
        if not valid:
            print(f'Invalid course: {course_view.course_id} - {r} - {r.text}')
            if r.status_code == 401:
                # We can't recover from this error.
                quit(1)
            continue

        course_view.assignments = find_course_assignments(course, USER_ID)
        course_view.announcements = find_course_announcements(course)
        course_view.discussions = find_course_discussions(course)
        course_view.pages = find_course_pages(course)
        course_view.modules = find_course_modules(course, course_view)
        all_courses_views.append(course_view)

        print('Downloading course home page...')
        download_course_home_page_html(API_URL, course_view, COOKIES_PATH)

        print('Downloading grades...')
        download_course_grades_page(API_URL, course_view, COOKIES_PATH)

        download_assignment_pages(API_URL, course_view, COOKIES_PATH, COOKIE_JAR)

        download_course_module_pages(API_URL, course_view, COOKIES_PATH)

        download_course_announcement_pages(API_URL, course_view, COOKIES_PATH)

        download_course_discussion_pages(API_URL, course_view, COOKIES_PATH)

        download_course_files(course, course_view)

        download_submission_attachments(course, course_view)

        print("Exporting course metadata...")
        export_all_course_data(course_view)

        if course_count > 1:
            print('')

    # Remove elements from the course objects that can't be JSON serialized, then format it.
    json_str = json.dumps(json.loads(jsonpickle.encode(all_courses_views, unpicklable=False)), indent=4)

    all_output_path = os.path.join(DL_LOCATION, "all_output.json")
    with open(all_output_path, "w") as out_file:
        out_file.write(json_str)

    print("\nProcess complete. All canvas data exported!")
