from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial

import canvasapi
from tqdm import tqdm

from module.api.file import get_embedded_files
from module.const import global_consts
from module.helpers import make_valid_filename, make_valid_folder_path, shorten_file_name
from module.items import CanvasCourse, jsonify_anything
from module.singlefile import download_page
from module.threading import download_assignment, download_module_item


def download_course_files(course, course_view):
    dl_dir = global_consts.OUTPUT_LOCATION / course_view.term / course_view.name
    dl_dir.mkdir(parents=True, exist_ok=True)

    try:
        files = list(course.get_files())
    except canvasapi.exceptions.Forbidden:
        print('Files view is disabled for this course.')
        return

    for file in tqdm(files, desc='Downloading Files'):
        try:
            file_folder = course.get_folder(file.folder_id)
            folder_dl_dir = dl_dir / make_valid_folder_path(file_folder.full_name)
            folder_dl_dir.mkdir(parents=True, exist_ok=True)
            dl_path = folder_dl_dir / make_valid_filename(str(file.display_name))
            file.download(dl_path)
        except Exception as e:
            tqdm.write(f"Skipping {file.display_name} - {e}")


def download_course_discussion_pages(resolved_course: CanvasCourse):
    if not len(resolved_course.discussions):
        return

    base_discussion_dir = global_consts.OUTPUT_LOCATION / resolved_course.term / resolved_course.name / 'discussions'
    base_discussion_dir.mkdir(parents=True, exist_ok=True)

    # (base_discussion_dir / 'discussions.json').write_text(jsonify_anything(resolved_course.discussions))
    download_page(global_consts.API_URL + "/courses/" + str(resolved_course.course_id) + "/discussion_topics/", base_discussion_dir, "discussions.html")

    for discussion in tqdm(list(resolved_course.discussions), desc='Downloading Discussions'):
        discussion_title = make_valid_filename(str(discussion.title))
        discussion_title = shorten_file_name(discussion_title, len(discussion_title) - global_consts.MAX_FOLDER_NAME_SIZE)
        discussion_dir = base_discussion_dir / discussion_title

        if not discussion.url:
            continue

        discussion_dir.mkdir(parents=True, exist_ok=True)

        for file in get_embedded_files(resolved_course.course, discussion.body):
            file.download(discussion_dir / file.display_name)

        for i in range(discussion.amount_pages):
            filename = "discussion_" + str(i + 1) + ".html"
            download_page(discussion.url + "/page-" + str(i + 1), discussion_dir, filename)


def download_assignments(course_view: CanvasCourse):
    if not len(course_view.assignments):
        return

    base_assign_dir = global_consts.OUTPUT_LOCATION / course_view.term / course_view.name / 'assignments'
    base_assign_dir.mkdir(parents=True, exist_ok=True)

    # (base_assign_dir / 'assignments.json').write_text(jsonify_anything(course_view.assignments))
    download_page(global_consts.API_URL + "/courses/" + str(course_view.course_id) + "/assignments/", base_assign_dir, "assignments.html")

    with ThreadPoolExecutor(max_workers=3) as executor:
        download_func = partial(download_assignment, base_assign_dir, course_view.course)
        list(tqdm(executor.map(download_func, course_view.assignments), total=len(course_view.assignments), desc='Downloading Assignments'))


def download_course_announcement_pages(resolved_course: CanvasCourse):
    if not len(resolved_course.announcements):
        return

    base_announce_dir = global_consts.OUTPUT_LOCATION / resolved_course.term / resolved_course.name / 'announcements'
    base_announce_dir.mkdir(parents=True, exist_ok=True)

    # (base_announce_dir / 'announcements.json').write_text(jsonify_anything(resolved_course.announcements))
    download_page(global_consts.API_URL + "/courses/" + str(resolved_course.course_id) + "/announcements/", base_announce_dir, "announcements.html")

    for announcement in tqdm(list(resolved_course.announcements), desc='Downloading Announcements'):
        announcements_title = make_valid_filename(str(announcement.title))
        announcements_title = shorten_file_name(announcements_title, len(announcements_title) - global_consts.MAX_FOLDER_NAME_SIZE)
        announce_dir = base_announce_dir / announcements_title

        if not announcement.url:
            continue

        announce_dir.mkdir(parents=True, exist_ok=True)

        for file in get_embedded_files(resolved_course.course, announcement.body):
            file.download(announce_dir / file.display_name)

        for i in range(announcement.amount_pages):
            filename = "announcement_" + str(i + 1) + ".html"
            download_page(announcement.url + "/page-" + str(i + 1), announce_dir, filename)


def download_course_home_page_html(course_view):
    dl_dir = global_consts.OUTPUT_LOCATION / course_view.term / course_view.name
    dl_dir.mkdir(parents=True, exist_ok=True)
    download_page(global_consts.API_URL + "/courses/" + str(course_view.course_id), dl_dir, "homepage.html")


def download_course_modules(course_view: CanvasCourse):
    modules_dir = global_consts.OUTPUT_LOCATION / course_view.term / course_view.name / 'modules'
    modules_dir.mkdir(parents=True, exist_ok=True)

    # (modules_dir / 'modules.json').write_text(jsonify_anything(course_view.modules))
    download_page(global_consts.API_URL + "/courses/" + str(course_view.course_id) + "/modules/", modules_dir, "modules.html")

    with ThreadPoolExecutor(max_workers=3) as executor:
        for module in tqdm(list(course_view.modules), desc='Downloading Modules'):
            bar = tqdm(list(module.items), leave=False, desc=module.module.name)
            futures = [executor.submit(download_module_item, course_view.course, module, item, modules_dir) for item in module.items]
            for _ in as_completed(futures):
                bar.update()
            bar.close()


def download_course_grades_page(course_view: CanvasCourse):
    dl_dir = global_consts.OUTPUT_LOCATION / course_view.term / course_view.name
    dl_dir.mkdir(parents=True, exist_ok=True)
    api_target = f'{global_consts.API_URL}/courses/{course_view.course_id}/grades'
    download_page(api_target, dl_dir, "grades.html")
