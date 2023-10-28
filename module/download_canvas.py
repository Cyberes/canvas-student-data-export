import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from http.cookiejar import MozillaCookieJar

import canvasapi
import requests
from tqdm import tqdm

from module.const import DL_LOCATION, MAX_FOLDER_NAME_SIZE
from module.helpers import make_valid_filename, make_valid_folder_path, shorten_file_name
from module.singlefile import download_page
from module.threading import download_assignment, download_module_item


def download_course_files(course, course_view):
    # file full_name starts with "course files"
    dl_dir = os.path.join(DL_LOCATION, course_view.term, course_view.name)

    # Create directory if not present
    if not os.path.exists(dl_dir):
        os.makedirs(dl_dir)

    try:
        files = list(course.get_files())
    except canvasapi.exceptions.Forbidden:
        print('Files view is disabled for this course.')
        return

    for file in tqdm(files, desc='Downloading Files'):
        try:
            file_folder = course.get_folder(file.folder_id)

            folder_dl_dir = os.path.join(dl_dir, make_valid_folder_path(file_folder.full_name))

            if not os.path.exists(folder_dl_dir):
                os.makedirs(folder_dl_dir)

            dl_path = os.path.join(folder_dl_dir, make_valid_filename(str(file.display_name)))

            # Download file if it doesn't already exist
            if not os.path.exists(dl_path):
                # print('Downloading: {}'.format(dl_path))
                file.download(dl_path)
        except Exception as e:
            tqdm.write(f"Skipping {file.display_name} - {e}")


def download_course_discussion_pages(api_url, course_view, cookies_path):
    if cookies_path == "" or len(course_view.discussions) == 0:
        return

    base_discussion_dir = os.path.join(DL_LOCATION, course_view.term, course_view.name, "discussions")
    if not os.path.exists(base_discussion_dir):
        os.makedirs(base_discussion_dir)

    discussion_list_dir = os.path.join(base_discussion_dir, "discussion_list.html")

    # Download assignment list (theres a chance this might be the course homepage if the course has the assignments page disabled)
    if not os.path.exists(discussion_list_dir):
        download_page(api_url + "/courses/" + str(course_view.course_id) + "/discussion_topics/", cookies_path, base_discussion_dir, "discussion_list.html")

    for discussion in tqdm(list(course_view.discussions), desc='Downloading Discussions'):
        discussion_title = make_valid_filename(str(discussion.title))
        discussion_title = shorten_file_name(discussion_title, len(discussion_title) - MAX_FOLDER_NAME_SIZE)
        discussion_dir = os.path.join(base_discussion_dir, discussion_title)

        if discussion.url == "":
            continue

        if not os.path.exists(discussion_dir):
            os.makedirs(discussion_dir)

        # Downloads each page that a discussion takes.
        for i in range(discussion.amount_pages):
            filename = "discussion_" + str(i + 1) + ".html"
            discussion_page_dir = os.path.join(discussion_dir, filename)

            # Download assignment page, this usually has instructions and etc.
            if not os.path.exists(discussion_page_dir):
                download_page(discussion.url + "/page-" + str(i + 1), cookies_path, discussion_dir, filename)


def download_assignment_pages(api_url, course_view, cookies_path, cookie_jar: MozillaCookieJar):
    if cookies_path == "" or len(course_view.assignments) == 0:
        return

    base_assign_dir = os.path.join(DL_LOCATION, course_view.term, course_view.name, "assignments")
    if not os.path.exists(base_assign_dir):
        os.makedirs(base_assign_dir)

    assignment_list_path = os.path.join(base_assign_dir, "assignment_list.html")

    # Download assignment list (theres a chance this might be the course homepage if the course has the assignments page disabled)
    if not os.path.exists(assignment_list_path):
        download_page(api_url + "/courses/" + str(course_view.course_id) + "/assignments/", cookies_path, base_assign_dir, "assignment_list.html")

    with ThreadPoolExecutor(max_workers=3) as executor:
        download_func = partial(download_assignment, cookies_path, cookie_jar, base_assign_dir)
        list(tqdm(executor.map(download_func, course_view.assignments), total=len(course_view.assignments), desc='Downloading Assignments'))


def download_course_announcement_pages(api_url, course_view, cookies_path):
    """
    Download assignment list.
    There's a chance this might be the course homepage if the course has the assignments page disabled.
    :param api_url:
    :param course_view:
    :param cookies_path:
    :return:
    """

    if cookies_path == "" or len(course_view.announcements) == 0:
        return

    base_announce_dir = os.path.join(DL_LOCATION, course_view.term, course_view.name, "announcements")
    if not os.path.exists(base_announce_dir):
        os.makedirs(base_announce_dir)
    announcement_list_dir = os.path.join(base_announce_dir, "announcement_list.html")
    if not os.path.exists(announcement_list_dir):
        download_page(api_url + "/courses/" + str(course_view.course_id) + "/announcements/", cookies_path, base_announce_dir, "announcement_list.html")

    for announcements in tqdm(list(course_view.announcements), desc='Downloading Announcements'):
        announcements_title = make_valid_filename(str(announcements.title))
        announcements_title = shorten_file_name(announcements_title, len(announcements_title) - MAX_FOLDER_NAME_SIZE)
        announce_dir = os.path.join(base_announce_dir, announcements_title)

        if announcements.url == "":
            continue

        if not os.path.exists(announce_dir):
            os.makedirs(announce_dir)

        # Downloads each page that a discussion takes.
        for i in range(announcements.amount_pages):
            filename = "announcement_" + str(i + 1) + ".html"
            announcement_page_dir = os.path.join(announce_dir, filename)

            # Download assignment page, this usually has instructions and etc.
            if not os.path.exists(announcement_page_dir):
                download_page(announcements.url + "/page-" + str(i + 1), cookies_path, announce_dir, filename)


def download_submission_attachments(course, course_view):
    course_dir = os.path.join(DL_LOCATION, course_view.term, course_view.name)

    # Create directory if not present
    if not os.path.exists(course_dir):
        os.makedirs(course_dir)

    for assignment in tqdm(list(course_view.assignments), desc='Downloading Submissions'):
        for submission in assignment.submissions:
            assignment_title = make_valid_filename(str(assignment.title))
            assignment_title = shorten_file_name(assignment_title, len(assignment_title) - MAX_FOLDER_NAME_SIZE)
            attachment_dir = os.path.join(course_dir, "assignments", assignment_title)
            if len(assignment.submissions) != 1:
                attachment_dir = os.path.join(attachment_dir, str(submission.user_id))
            if not os.path.exists(attachment_dir) and submission.attachments:
                os.makedirs(attachment_dir)
            for attachment in submission.attachments:
                filepath = os.path.join(attachment_dir, make_valid_filename(str(attachment.id) + "_" + attachment.filename))
                if not os.path.exists(filepath):
                    # print('Downloading attachment: {}'.format(filepath))
                    r = requests.get(attachment.url, allow_redirects=True)
                    with open(filepath, 'wb') as f:
                        f.write(r.content)
                # else:
                #     print('File already exists: {}'.format(filepath))


def download_course_html(api_url, cookies_path):
    if cookies_path == "":
        return

    course_dir = DL_LOCATION

    if not os.path.exists(course_dir):
        os.makedirs(course_dir)

    course_list_path = os.path.join(course_dir, "course_list.html")

    # Downloads the course list.
    if not os.path.exists(course_list_path):
        download_page(api_url + "/courses/", cookies_path, course_dir, "course_list.html")


def download_course_home_page_html(api_url, course_view, cookies_path):
    if cookies_path == "":
        return

    dl_dir = os.path.join(DL_LOCATION, course_view.term, course_view.name)
    if not os.path.exists(dl_dir):
        os.makedirs(dl_dir)

    homepage_path = os.path.join(dl_dir, "homepage.html")

    # Downloads the course home page.
    if not os.path.exists(homepage_path):
        download_page(api_url + "/courses/" + str(course_view.course_id), cookies_path, dl_dir, "homepage.html")


def download_course_module_pages(api_url, course_view, cookies_path):
    if cookies_path == "" or len(course_view.modules) == 0:
        return

    modules_dir = os.path.join(DL_LOCATION, course_view.term, course_view.name, "modules")
    if not os.path.exists(modules_dir):
        os.makedirs(modules_dir)

    module_list_dir = os.path.join(modules_dir, "modules_list.html")

    # Downloads the modules page (possible this is disabled by the teacher)
    if not os.path.exists(module_list_dir):
        download_page(api_url + "/courses/" + str(course_view.course_id) + "/modules/", cookies_path, modules_dir, "modules_list.html")

    with ThreadPoolExecutor(max_workers=3) as executor:
        for module in tqdm(list(course_view.modules), desc='Downloading Module Pages'):
            bar = tqdm(list(module.items), leave=False, desc=module.name)
            futures = [executor.submit(download_module_item, module, item, modules_dir, cookies_path) for item in module.items]
            for _ in as_completed(futures):
                bar.update()
            bar.close()
