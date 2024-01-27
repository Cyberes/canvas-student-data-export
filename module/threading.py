import traceback
from pathlib import Path

from canvasapi.assignment import Assignment
from canvasapi.course import Course
from canvasapi.submission import Submission

from module.api.file import get_embedded_files
from module.const import global_consts
from module.helpers import make_valid_filename, shorten_file_name
from module.items import CanvasModuleItem, jsonify_anything, CanvasModule
from module.singlefile import download_page


def download_module_item(course: Course, module: CanvasModule, item: CanvasModuleItem, modules_dir: Path):
    try:
        module_name = make_valid_filename(str(module.module.name))
        module_name = shorten_file_name(module_name, len(module_name) - global_consts.MAX_FOLDER_NAME_SIZE)
        module_dir = modules_dir / module_name

        if not hasattr(item.item, 'url') or not item.item.url:
            return

        module_dir.mkdir(parents=True, exist_ok=True)

        if item.item.type == "File":
            file = course.get_file(item.item.content_id)
            module_file_path = module_dir / make_valid_filename(str(file.display_name))
            file.download(module_file_path)
        else:
            # It's a page, so download the attached files.
            for file in item.attached_files:
                file.download(module_dir / file.filename)

        # Download the module page.
        html_filename = make_valid_filename(str(item.item.title)) + ".html"
        download_page(item.item.html_url, module_dir, html_filename)
    except:
        # TODO: wrap all threaded funcs in this try/catch
        traceback.print_exc()


def download_assignment(base_assign_dir: Path, course: Course, assignment: Assignment):
    try:
        assignment_title = make_valid_filename(str(assignment.name))
        assignment_title = shorten_file_name(assignment_title, len(assignment_title) - global_consts.MAX_FOLDER_NAME_SIZE)
        assign_dir = Path(base_assign_dir, assignment_title)
        assign_dir.mkdir(parents=True, exist_ok=True)

        if assignment.html_url:
            download_page(assignment.html_url, assign_dir, "assignment.html")

            # Download attached files.
            if assignment.description:
                for file in get_embedded_files(course, assignment.description):
                    file.download(assign_dir / file.display_name)

        # Students cannot view their past attempts, but this logic is left if that's ever implemented in Canvas.
        submissions = [assignment.get_submission(global_consts.USER_ID)]
        for submission in submissions:
            download_attempt(submission, assign_dir)
            submission_dir = assign_dir / 'submission' / str(submission.id)
            for attachment in submission.attachments:
                filepath = submission_dir / attachment.display_name
                if not filepath.exists():
                    attachment.download(filepath)
    except:
        traceback.print_exc()


def download_attempt(submission: Submission, assign_dir: Path):
    try:
        submission_dir = assign_dir / 'submission' / str(submission.id)
        submission_dir.mkdir(parents=True, exist_ok=True)
        for file in submission.attachments:
            file.download(submission_dir / file.display_name)
        if submission.preview_url:
            download_page(submission.preview_url, submission_dir, f'{submission.id}.html')
    except:
        traceback.print_exc()
