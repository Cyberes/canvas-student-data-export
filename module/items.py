from http.cookiejar import MozillaCookieJar

import requests

from module.helpers import make_valid_filename


class ModuleItemView:
    def __init__(self):
        self.id = 0
        self.title = ""
        self.content_type = ""
        self.url = ""
        self.external_url = ""


class ModuleView:
    def __init__(self):
        self.id = 0
        self.name = ""
        self.items = []


class PageView:
    def __init__(self):
        self.id = 0
        self.title = ""
        self.body = ""
        self.created_date = ""
        self.last_updated_date = ""


class TopicReplyView:
    def __init__(self):
        self.id = 0
        self.author = ""
        self.posted_date = ""
        self.body = ""


class TopicEntryView:
    def __init__(self):
        self.id = 0
        self.author = ""
        self.posted_date = ""
        self.body = ""
        self.topic_replies = []


class DiscussionView:
    def __init__(self):
        self.id = 0
        self.title = ""
        self.author = ""
        self.posted_date = ""
        self.body = ""
        self.topic_entries = []
        self.url = ""
        self.amount_pages = 0


class SubmissionView:
    def __init__(self):
        self.id = 0
        self.attachments = []
        self.grade = ""
        self.raw_score = ""
        self.submission_comments = ""
        self.total_possible_points = ""
        self.attempt = 0
        self.user_id = "no-id"
        self.preview_url = ""
        self.ext_url = ""


class AttachmentView:
    def __init__(self):
        self.id = 0
        self.filename = ""
        self.url = ""


class AssignmentView:

    def __init__(self):
        self.id = 0
        self.title = ""
        self.description = ""
        self.assigned_date = ""
        self.due_date = ""
        self.submissions = []
        self.html_url = ""
        self.ext_url = ""
        self.updated_url = ""


class CourseView:
    def __init__(self, course):
        self.course_id = course.id if hasattr(course, "id") else 0
        self.term = make_valid_filename(course.term["name"] if hasattr(course, "term") and "name" in course.term.keys() else "")
        self.course_code = make_valid_filename(course.course_code if hasattr(course, "course_code") else "")
        self.name = course.name if hasattr(course, "name") else ""

        self.course_code = self.course_code.replace('  ', ' ')
        self.name = self.name.replace('  ', ' ')

        self.assignments = []
        self.announcements = []
        self.discussions = []
        self.modules = []

    def test_course(self, base_url: str, cookie_jar: MozillaCookieJar):
        s = requests.Session()
        for cookie in cookie_jar:
            s.cookies.set(cookie.name, cookie.value)
        try:
            r = s.get(f'{base_url}/api/v1/courses/{self.course_id}')
            if not r.status_code == 200:
                return False, r
            return True, r
        except Exception as e:
            return False, e
