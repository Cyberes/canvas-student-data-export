import argparse
import json
import os
from http.cookiejar import MozillaCookieJar
from pathlib import Path

import canvasapi
import requests
import yaml
from canvasapi import Canvas

from module.const import global_consts
from module.download_canvas import download_assignments, download_course_modules, download_course_grades_page, download_course_announcement_pages, download_course_home_page_html, download_course_discussion_pages
from module.get_canvas import find_course_pages, find_course_modules, find_course_assignments, find_course_announcements, find_course_discussions
from module.items import CanvasCourse, jsonify_anything
from module.singlefile import download_page
from module.user_files import download_user_files

SCRIPT_PATH = os.path.abspath(os.path.dirname(__file__))


def export_all_course_data(c):
    json_data = jsonify_anything(c)
    course_output_dir = os.path.join(OUTPUT_LOCATION, c.term, c.name)
    if not os.path.exists(course_output_dir):
        os.makedirs(course_output_dir)
    course_output_path = os.path.join(course_output_dir, c.name + ".json")
    with open(course_output_path, "w") as file:
        file.write(json_data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--output', default='./output', help='Output location. If it does not exist, it will be created.')
    parser.add_argument('--term', default=None, help='Only download this term.')
    parser.add_argument('--user-files', action='store_true', help="Download the user files.")
    args = parser.parse_args()

    OUTPUT_LOCATION = Path(args.output).resolve().expanduser().absolute()
    OUTPUT_LOCATION.mkdir(parents=True, exist_ok=True)

    # Startup checks.
    creds_file = Path(SCRIPT_PATH, 'credentials.yaml')
    if not creds_file.is_file():
        print('The credentials.yaml file does not exist:', creds_file)
        quit(1)

    with open("credentials.yaml", 'r') as f:
        credentials = yaml.full_load(f)

    global_consts.API_URL = credentials["API_URL"]
    global_consts.API_KEY = credentials["API_KEY"]
    global_consts.USER_ID = credentials["USER_ID"]
    global_consts.COOKIES_PATH = str(Path(credentials["COOKIES_PATH"]).resolve().expanduser().absolute())

    if not Path(global_consts.COOKIES_PATH).is_file():
        print('The cookies file does not exist:', global_consts.COOKIES_PATH)
        quit(1)

    global_consts.COOKIE_JAR = MozillaCookieJar(global_consts.COOKIES_PATH)
    global_consts.COOKIE_JAR.load(ignore_discard=True, ignore_expires=True)

    # ==================================================================================================================
    # Initialization

    print("Welcome to the Canvas Student Data Export Tool")
    if not os.path.exists(OUTPUT_LOCATION):
        print("Creating output directory:", OUTPUT_LOCATION)
        os.makedirs(OUTPUT_LOCATION)

    if global_consts.COOKIES_PATH:
        # Test the cookies.
        print("Authenticating with Canvas frontend...")

        # Requests takes a dict, not the MozillaCookieJar object.
        request_cookies = {c.name: c.value for c in global_consts.COOKIE_JAR}

        r = requests.get(f'{global_consts.API_URL}/profile', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}, cookies=request_cookies)
        if r.status_code != 200:
            print('Failed to fetch Canvas profile: got status code', r.status_code)
            quit(1)
        if not r.url.startswith(global_consts.API_URL):
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
    canvas = Canvas(global_consts.API_URL, global_consts.API_KEY)
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

    skip = set(global_consts.COURSES_TO_SKIP)

    # ==================================================================================================================
    # Exporting

    print("Downloading courses page...")
    courses_dict = {v['id']: v for v in json.loads(jsonify_anything(courses))['_elements']}
    (global_consts.OUTPUT_LOCATION / 'courses.json').write_text(json.dumps(courses_dict))
    download_page(global_consts.API_URL + "/courses/", global_consts.OUTPUT_LOCATION, "courses.html")

    if args.user_files:
        print('Downloading user files...')
        download_user_files(canvas, OUTPUT_LOCATION / 'User Files')

    print('')

    all_courses_views = []

    for course in courses:
        if course.id in skip or not hasattr(course, "name") or not hasattr(course, "term"):
            continue

        resolved_canvas_course = CanvasCourse(course)

        if args.term and args.term != resolved_canvas_course.term:
            print('Skipping term:', resolved_canvas_course.term, '\n')
            continue

        print(f"=== {resolved_canvas_course.term}: {resolved_canvas_course.name} ===")

        valid, r = resolved_canvas_course.test_course(global_consts.API_URL, global_consts.COOKIE_JAR)
        if not valid:
            print(f'Invalid course: {resolved_canvas_course.course_id} - {r} - {r.text}')
            if r.status_code == 401:
                # We can't recover from this error.
                quit(1)
            continue

        resolved_canvas_course.modules = find_course_modules(course)
        resolved_canvas_course.assignments = find_course_assignments(course)
        resolved_canvas_course.announcements = find_course_announcements(course)
        resolved_canvas_course.discussions = find_course_discussions(course)
        resolved_canvas_course.pages = find_course_pages(course)

        all_courses_views.append(resolved_canvas_course)

        print('Downloading course home page...')
        download_course_home_page_html(resolved_canvas_course)

        print('Downloading grades...')
        download_course_grades_page(resolved_canvas_course)

        download_assignments(resolved_canvas_course)

        download_course_modules(resolved_canvas_course)

        download_course_announcement_pages(resolved_canvas_course)

        download_course_discussion_pages(resolved_canvas_course)

        download_course_files(course, resolved_canvas_course)

        print("Exporting course metadata...")
        export_all_course_data(resolved_canvas_course)

        if course_count > 1:
            print('')

    # Remove elements from the course objects that can't be JSON serialized, then format it.
    json_str = jsonify_anything(all_courses_views)

    all_output_path = os.path.join(OUTPUT_LOCATION, "all_output.json")
    with open(all_output_path, "w") as out_file:
        out_file.write(json_str)

    print("\nProcess complete. All canvas data exported!")
