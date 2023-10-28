import os
from pathlib import Path

from module.singlefile import download_page
from module.const import MAX_FOLDER_NAME_SIZE
from module.download import download_file
from module.get_canvas import get_extra_assignment_files
from module.helpers import make_valid_filename, shorten_file_name


def download_module_item(module, item, modules_dir, cookies_path):
    # If problems arise due to long pathnames, changing module.name to module.id might help, this can also be done with item.title
    # A change would also have to be made in findCourseModules(course, course_view)
    module_name = make_valid_filename(str(module.name))
    module_name = shorten_file_name(module_name, len(module_name) - MAX_FOLDER_NAME_SIZE)
    items_dir = os.path.join(modules_dir, module_name)

    if item.url != "":
        if not os.path.exists(items_dir):
            os.makedirs(items_dir)

        filename = make_valid_filename(str(item.title)) + ".html"
        module_item_dir = os.path.join(items_dir, filename)

        # Download the module page.
        if not os.path.exists(module_item_dir):
            download_page(item.url, cookies_path, items_dir, filename)


def download_assignment(cookies_path, cookie_jar, base_assign_dir, assignment):
    assignment_title = make_valid_filename(str(assignment.title))
    assignment_title = shorten_file_name(assignment_title, len(assignment_title) - MAX_FOLDER_NAME_SIZE)
    assign_dir = os.path.join(base_assign_dir, assignment_title)

    if assignment.html_url != "":
        if not os.path.exists(assign_dir):
            os.makedirs(assign_dir)

        assignment_page_path = os.path.join(assign_dir, "assignment.html")

        if not os.path.exists(assignment_page_path):
            download_page(assignment.html_url, cookies_path, assign_dir, "assignment.html")

        extra_files = get_extra_assignment_files(assignment.description, cookie_jar)
        for name, url in extra_files:
            download_file(url, Path(assign_dir, name), cookie_jar)

    for submission in assignment.submissions:
        download_submission(assignment, submission, assign_dir, cookies_path)


def download_submission(assignment, submission, assign_dir, cookies_path):
    submission_dir = assign_dir

    if len(assignment.submissions) != 1:
        submission_dir = os.path.join(assign_dir, str(submission.user_id))

    if submission.preview_url != "":
        if not os.path.exists(submission_dir):
            os.makedirs(submission_dir)

        submission_page_dir = os.path.join(submission_dir, "submission.html")

        if not os.path.exists(submission_page_dir):
            download_page(submission.preview_url, cookies_path, submission_dir, "submission.html")

    if (submission.attempt != 1 and assignment.updated_url != "" and assignment.html_url != ""
            and assignment.html_url.rstrip("/") != assignment.updated_url.rstrip("/")):
        submission_dir = os.path.join(assign_dir, "attempts")

        if not os.path.exists(submission_dir):
            os.makedirs(submission_dir)

        for i in range(submission.attempt):
            filename = "attempt_" + str(i + 1) + ".html"
            submission_page_attempt_dir = os.path.join(submission_dir, filename)

            if not os.path.exists(submission_page_attempt_dir):
                download_page(assignment.updated_url + "/history?version=" + str(i + 1), cookies_path, submission_dir, filename)
