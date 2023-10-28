import os
from http.cookiejar import MozillaCookieJar

import dateutil.parser
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from module.const import DATE_TEMPLATE, DL_LOCATION, MAX_FOLDER_NAME_SIZE
from module.helpers import make_valid_filename, shorten_file_name
from module.items import AssignmentView, AttachmentView, DiscussionView, ModuleItemView, ModuleView, PageView, SubmissionView, TopicEntryView, TopicReplyView


def find_course_modules(course, course_view):
    modules_dir = os.path.join(DL_LOCATION, course_view.term, course_view.name, "modules")

    # Create modules directory if not present
    if not os.path.exists(modules_dir):
        os.makedirs(modules_dir)

    module_views = []

    try:
        modules = list(course.get_modules())

        for module in tqdm(modules, desc='Downloading Module Files'):
            module_view = ModuleView()
            module_view.id = module.id if hasattr(module, "id") else ""
            module_view.name = str(module.name) if hasattr(module, "name") else ""

            try:
                # Get module items
                module_items = module.get_module_items()

                for module_item in module_items:
                    module_item_view = ModuleItemView()
                    module_item_view.id = module_item.id if hasattr(module_item, "id") else 0
                    module_item_view.title = str(module_item.title).replace('  ', ' ') if hasattr(module_item, "title") else ""
                    module_item_view.content_type = str(module_item.type) if hasattr(module_item, "type") else ""
                    module_item_view.url = str(module_item.html_url) if hasattr(module_item, "html_url") else ""
                    module_item_view.external_url = str(module_item.external_url) if hasattr(module_item, "external_url") else ""

                    if module_item_view.content_type == "File":
                        # If problems arise due to long pathnames, changing module.name to module.id might help
                        # A change would also have to be made in downloadCourseModulePages(api_url, course_view, cookies_path)
                        module_name = make_valid_filename(str(module.name))
                        module_name = shorten_file_name(module_name, len(module_name) - MAX_FOLDER_NAME_SIZE)
                        module_dir = os.path.join(modules_dir, module_name, "files")

                        try:
                            # Create directory for current module if not present
                            if not os.path.exists(module_dir):
                                os.makedirs(module_dir)

                            # Get the file object
                            module_file = course.get_file(str(module_item.content_id))

                            # Create path for module file download
                            module_file_path = os.path.join(module_dir, make_valid_filename(str(module_file.display_name)))

                            # Download file if it doesn't already exist
                            if not os.path.exists(module_file_path):
                                module_file.download(module_file_path)
                        except Exception as e:
                            tqdm.write(f"Skipping module file download that gave the following error: {e} - {module_item}")

                    module_view.items.append(module_item_view)
            except Exception as e:
                tqdm.write(f"Skipping module file download that gave the following error: {e}")

            module_views.append(module_view)

    except Exception as e:
        print("Skipping entire module that gave the following error:")
        print(e)

    return module_views


def get_extra_assignment_files(html, cookie_jar: MozillaCookieJar):
    soup = BeautifulSoup(html, 'html.parser')
    urls = [a['data-api-endpoint'] for a in soup.find_all('a', {'data-api-returntype': 'File'})]

    s = requests.Session()
    for cookie in cookie_jar:
        s.cookies.set(cookie.name, cookie.value)

    extra_files = []
    for item in urls:
        r = s.get(item)
        if r.status_code != 200:
            continue
        j = r.json()
        extra_files.append((j['display_name'], j['url']))

    return extra_files


def get_course_page_urls(course):
    page_urls = []
    try:
        pages = list(course.get_pages())
        for page in pages:
            if hasattr(page, "url"):
                page_urls.append(str(page.url))
    except Exception as e:
        if e.message != "Not Found":
            print(f"Skipping page: {e}")
    return page_urls


def find_course_pages(course):
    page_views = []
    try:
        page_urls = get_course_page_urls(course)
        if not len(page_urls):
            return

        for url in tqdm(page_urls, desc='Fetching Pages'):
            page = course.get_page(url)
            page_view = PageView()
            page_view.id = page.id if hasattr(page, "id") else 0
            page_view.title = str(page.title).replace('  ', ' ') if hasattr(page, "title") else ""
            page_view.body = str(page.body) if hasattr(page, "body") else ""

            if hasattr(page, "created_at"):
                page_view.created_date = dateutil.parser.parse(page.created_at).strftime(DATE_TEMPLATE)
            else:
                page_view.created_date = ''

            if hasattr(page, "updated_at"):
                page_view.last_updated_date = dateutil.parser.parse(page.updated_at).strftime(DATE_TEMPLATE)
            else:
                page_view.last_updated_date = ''

            page_views.append(page_view)
    except Exception as e:
        print("Skipping page download that gave the following error:")
        print(e)
    return page_views


def find_course_assignments(course, user_id):
    assignment_views = []

    # Get all assignments
    assignments = list(course.get_assignments())

    for assignment in tqdm(assignments, desc='Fetching Assignments'):
        assignment_view = AssignmentView()
        assignment_view.id = assignment.id if hasattr(assignment, "id") else ""
        assignment_view.title = make_valid_filename(str(assignment.name).replace('  ', ' ')) if hasattr(assignment, "name") else ""
        assignment_view.description = str(assignment.description) if hasattr(assignment, "description") else ""
        assignment_view.assigned_date = assignment.created_at_date.strftime(DATE_TEMPLATE) if hasattr(assignment, "created_at_date") else ""
        assignment_view.due_date = assignment.due_at_date.strftime(DATE_TEMPLATE) if hasattr(assignment, "due_at_date") else ""
        assignment_view.html_url = assignment.html_url if hasattr(assignment, "html_url") else ""
        assignment_view.ext_url = str(assignment.url) if hasattr(assignment, "url") else ""
        assignment_view.updated_url = str(assignment.submissions_download_url).split("submissions?")[0] if hasattr(assignment, "submissions_download_url") else ""

        # Download submission for this user only
        submissions = [assignment.get_submission(user_id)]
        if not len(submissions):
            raise IndexError(f'No submissions found for assignment: {vars(assignment)}')

        try:
            for submission in submissions:
                sub_view = SubmissionView()
                sub_view.id = submission.id if hasattr(submission, "id") else 0
                sub_view.grade = str(submission.grade) if hasattr(submission, "grade") else ""
                sub_view.raw_score = str(submission.score) if hasattr(submission, "score") else ""
                sub_view.total_possible_points = str(assignment.points_possible) if hasattr(assignment, "points_possible") else ""
                sub_view.submission_comments = str(submission.submission_comments) if hasattr(submission, "submission_comments") else ""
                sub_view.attempt = submission.attempt if hasattr(submission, "attempt") and submission.attempt is not None else 0
                sub_view.user_id = str(submission.user_id) if hasattr(submission, "user_id") else ""
                sub_view.preview_url = str(submission.preview_url) if hasattr(submission, "preview_url") else ""
                sub_view.ext_url = str(submission.url) if hasattr(submission, "url") else ""

                try:
                    submission.attachments
                except AttributeError:
                    print('No attachments')
                else:
                    for attachment in submission.attachments:
                        attach_view = AttachmentView()
                        attach_view.url = attachment.url
                        attach_view.id = attachment.id
                        attach_view.filename = attachment.filename
                        sub_view.attachments.append(attach_view)
                assignment_view.submissions.append(sub_view)
        except Exception as e:
            raise
            # print("Skipping submission that gave the following error:")
            # print(e)

        assignment_views.append(assignment_view)

    return assignment_views


def find_course_announcements(course):
    announcement_views = []

    # try:
    announcements = list(course.get_discussion_topics(only_announcements=True))

    for announcement in tqdm(announcements, desc='Fetching Announcements'):
        discussion_view = get_discussion_view(announcement)

        announcement_views.append(discussion_view)
    # except Exception as e:
    #     print("Skipping announcement that gave the following error:")
    #     print(e)

    return announcement_views


def get_discussion_view(discussion_topic):
    # Create discussion view
    discussion_view = DiscussionView()
    discussion_view.id = discussion_topic.id if hasattr(discussion_topic, "id") else 0
    discussion_view.title = str(discussion_topic.title).replace('  ', ' ') if hasattr(discussion_topic, "title") else ""
    discussion_view.author = str(discussion_topic.user_name) if hasattr(discussion_topic, "user_name") else ""
    discussion_view.posted_date = discussion_topic.created_at_date.strftime("%B %d, %Y %I:%M %p") if hasattr(discussion_topic, "created_at_date") else ""
    discussion_view.body = str(discussion_topic.message) if hasattr(discussion_topic, "message") else ""
    discussion_view.url = str(discussion_topic.html_url) if hasattr(discussion_topic, "html_url") else ""

    # Keeps track of how many topic_entries there are.
    topic_entries_counter = 0

    # Topic entries
    if hasattr(discussion_topic, "discussion_subentry_count") and discussion_topic.discussion_subentry_count > 0:
        # Need to get replies to entries recursively?
        discussion_topic_entries = discussion_topic.get_topic_entries()
        try:
            for topic_entry in discussion_topic_entries:
                topic_entries_counter += 1

                # Create new discussion view for the topic_entry
                topic_entry_view = TopicEntryView()
                topic_entry_view.id = topic_entry.id if hasattr(topic_entry, "id") else 0
                topic_entry_view.author = str(topic_entry.user_name) if hasattr(topic_entry, "user_name") else ""
                topic_entry_view.posted_date = topic_entry.created_at_date.strftime("%B %d, %Y %I:%M %p") if hasattr(topic_entry, "created_at_date") else ""
                topic_entry_view.body = str(topic_entry.message) if hasattr(topic_entry, "message") else ""

                # Get this topic's replies
                topic_entry_replies = topic_entry.get_replies()

                try:
                    for topic_reply in topic_entry_replies:
                        # Create new topic reply view
                        topic_reply_view = TopicReplyView()
                        topic_reply_view.id = topic_reply.id if hasattr(topic_reply, "id") else 0
                        topic_reply_view.author = str(topic_reply.user_name) if hasattr(topic_reply, "user_name") else ""
                        topic_reply_view.posted_date = topic_reply.created_at_date.strftime("%B %d, %Y %I:%M %p") if hasattr(topic_reply, "created_at_date") else ""
                        topic_reply_view.message = str(topic_reply.message) if hasattr(topic_reply, "message") else ""
                        topic_entry_view.topic_replies.append(topic_reply_view)
                except Exception as e:
                    print("Tried to enumerate discussion topic entry replies but received the following error:")
                    print(e)

                discussion_view.topic_entries.append(topic_entry_view)
        except Exception as e:
            print("Tried to enumerate discussion topic entries but received the following error:")
            print(e)

    # Amount of pages.
    # Typically 50 topic entries are stored on a page before it creates another page.
    discussion_view.amount_pages = int(topic_entries_counter / 50) + 1

    return discussion_view


def find_course_discussions(course):
    discussion_views = []

    # try:
    discussion_topics = list(course.get_discussion_topics())

    for discussion_topic in tqdm(discussion_topics, desc='Fetching Discussions'):
        discussion_view = get_discussion_view(discussion_topic)
        discussion_views.append(discussion_view)
    # except Exception as e:
    #     print("Skipping discussion that gave the following error:")
    #     print(e)

    return discussion_views
