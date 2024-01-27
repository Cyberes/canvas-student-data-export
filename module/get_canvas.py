import re
from typing import List

import canvasapi
import dateutil.parser
from canvasapi.discussion_topic import DiscussionTopic
from tqdm import tqdm

from module.const import global_consts
from module.items import CanvasDiscussion, CanvasPage, CanvasTopicEntry, CanvasTopicReply, CanvasModule

HTML_ITEM_ATTACHED_FILE_RE = re.compile(r'<a .*? data-api-endpoint=\"(.*?)\" .*?>')
CANVAS_API_FILE_ID_RE = re.compile(r'.*?/api/v1/courses/.*?/files/(.*?)$')


def find_course_modules(course) -> List[CanvasModule]:
    # modules_dir = os.path.join(global_consts.OUTPUT_LOCATION, course_view.term, course_view.name, "modules")

    results = []

    try:
        modules = list(course.get_modules())
        for module in tqdm(modules, desc='Fetching Modules'):
            try:
                resolved_module = CanvasModule(module)
                for item in resolved_module.items:
                    if item.item.type == 'Page':
                        page = course.get_page(item.item.page_url)
                        item.page = page
                        if hasattr(page, 'body'):
                            # Extract the attached files from the item's HTML.
                            file_matches = re.findall(HTML_ITEM_ATTACHED_FILE_RE, page.body)
                            for match in file_matches:
                                file_id = re.match(CANVAS_API_FILE_ID_RE, match)
                                if file_id:
                                    try:
                                        # Grab the metadata from the API.
                                        canvas_file = course.get_file(file_id.group(1))
                                        item.attached_files.add(canvas_file)
                                    except canvasapi.exceptions.ResourceDoesNotExist:
                                        continue
                results.append(resolved_module)
            except Exception as e:
                tqdm.write(f"Skipping module file download that gave the following error: {e}")
    except Exception as e:
        tqdm.write(f"Skipping module file download that gave the following error: {e}")

    return results


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
            page_view = CanvasPage()
            page_view.id = page.id if hasattr(page, "id") else 0
            page_view.title = str(page.title).replace('  ', ' ') if hasattr(page, "title") else ""
            page_view.body = str(page.body) if hasattr(page, "body") else ""

            if hasattr(page, "created_at"):
                page_view.created_date = dateutil.parser.parse(page.created_at).strftime(global_consts.DATE_TEMPLATE)
            else:
                page_view.created_date = ''

            if hasattr(page, "updated_at"):
                page_view.last_updated_date = dateutil.parser.parse(page.updated_at).strftime(global_consts.DATE_TEMPLATE)
            else:
                page_view.last_updated_date = ''

            page_views.append(page_view)
    except Exception as e:
        print("Skipping page download that gave the following error:")
        print(e)
    return page_views


def find_course_assignments(course):
    results = []
    assignments = list(course.get_assignments())
    for assignment in tqdm(assignments, desc='Fetching Assignments'):
        # Have to re-define the object because the `/api/v1/courses/:course_id/assignments` endpoint is sometimes outdated.
        # The endpoint `/api/v1/courses/:course_id/assignments/:id` has the most up to date data.
        assignment = course.get_assignment(assignment.id)
        results.append(assignment)
    return results


def find_course_announcements(course):
    announcement_views = []
    announcements: List[DiscussionTopic] = list(course.get_discussion_topics(only_announcements=True))

    for announcement in tqdm(announcements, desc='Fetching Announcements'):
        discussion_view = get_discussion_view(announcement)
        announcement_views.append(discussion_view)

    return announcement_views


def get_discussion_view(discussion_topic):
    # Create discussion view
    discussion_view = CanvasDiscussion(discussion_topic)
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
                topic_entry_view = CanvasTopicEntry()
                topic_entry_view.id = topic_entry.id if hasattr(topic_entry, "id") else 0
                topic_entry_view.author = str(topic_entry.user_name) if hasattr(topic_entry, "user_name") else ""
                topic_entry_view.posted_date = topic_entry.created_at_date.strftime("%B %d, %Y %I:%M %p") if hasattr(topic_entry, "created_at_date") else ""
                topic_entry_view.body = str(topic_entry.message) if hasattr(topic_entry, "message") else ""

                # Get this topic's replies
                topic_entry_replies = topic_entry.get_replies()

                try:
                    for topic_reply in topic_entry_replies:
                        # Create new topic reply view
                        topic_reply_view = CanvasTopicReply()
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
    discussion_topics = list(course.get_discussion_topics())
    for discussion_topic in tqdm(discussion_topics, desc='Fetching Discussions'):
        discussion_view = get_discussion_view(discussion_topic)
        discussion_views.append(discussion_view)
    return discussion_views
