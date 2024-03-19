import json
from http.cookiejar import MozillaCookieJar
from typing import List, Any

import requests
from canvasapi.assignment import Assignment
from canvasapi.course import Course
from canvasapi.file import File
from canvasapi.module import ModuleItem, Module
from canvasapi.page import Page

from module.helpers import make_valid_filename


def varsify(item) -> Any:
    result = {}
    try:
        if isinstance(item, (str, int, float, bool)):
            return item
        elif isinstance(item, (list, set)):
            l_result = []
            for i, x in enumerate(item):
                l_result.append(varsify(x))
            return l_result
        else:
            for k, v in vars(item).items():
                if isinstance(v, dict):
                    result[k] = varsify(v)
                elif isinstance(v, list):
                    result[k] = []
                    for i, x in enumerate(v):
                        result[k].insert(i, varsify(x))
                else:
                    if not k.startswith('_'):
                        result[k] = varsify(v)
            return result
    except:
        return item


def jsonify_anything(item):
    return json.dumps(varsify(item), indent=4, sort_keys=True, default=str)


class CanvasModuleItem:
    def __init__(self, module_item: ModuleItem):
        self.item = module_item
        self.attached_files: set[File] = set()
        self.page: Page


class CanvasModule:
    def __init__(self, module: Module):
        self.module = module
        self.items: List[CanvasModuleItem] = []
        for item in module.get_module_items():
            i = self.module.get_module_item(item.id)
            self.items.append(CanvasModuleItem(i))


class CanvasPage:
    def __init__(self):
        self.id = 0
        self.title = ""
        self.body = ""
        self.created_date = ""
        self.last_updated_date = ""


class CanvasTopicReply:
    def __init__(self):
        self.id = 0
        self.author = ""
        self.posted_date = ""
        self.body = ""


class CanvasTopicEntry:
    def __init__(self):
        self.id = 0
        self.author = ""
        self.posted_date = ""
        self.body = ""
        self.topic_replies = []


class CanvasDiscussion:
    def __init__(self, discussion):
        self.discussion = discussion
        self.id = 0
        self.title = ""
        self.author = ""
        self.posted_date = ""
        self.body = ""
        self.topic_entries = []
        self.url = ""
        self.amount_pages = 0


class CanvasSubmission:
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


class CanvasCourse:
    def __init__(self, course):
        self.course: Course = course
        self.course_id = course.id if hasattr(course, "id") else 0
        self.term = make_valid_filename(course.term["name"] if hasattr(course, "term") and "name" in course.term.keys() else "")
        self.course_code = make_valid_filename(course.course_code if hasattr(course, "course_code") else "")

        if hasattr(course, 'original_name'):
            self.name = make_valid_filename(course.original_name)
        else:
            self.name = make_valid_filename(course.name) if hasattr(course, "name") else ""

        self.course_code = self.course_code.replace('  ', ' ')
        self.name = self.name.replace('  ', ' ')

        self.assignments: List[Assignment] = []
        self.announcements: List[CanvasDiscussion] = []
        self.discussions: List[CanvasDiscussion] = []
        self.modules: List[CanvasModule] = []

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
