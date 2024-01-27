import re

import canvasapi
from canvasapi.course import Course

HTML_ITEM_ATTACHED_FILE_RE = re.compile(r'<a .*? data-api-endpoint=\"(.*?)\" .*?>')
CANVAS_API_FILE_ID_RE = re.compile(r'.*?/api/v1/courses/.*?/files/(.*?)$')


def get_embedded_files(course: Course, html: str):
    attached_files = set()
    file_matches = re.findall(HTML_ITEM_ATTACHED_FILE_RE, html)
    for match in file_matches:
        file_id = re.match(CANVAS_API_FILE_ID_RE, match)
        if file_id:
            try:
                canvas_file = course.get_file(file_id.group(1))
                attached_files.add(canvas_file)
            except canvasapi.exceptions.ResourceDoesNotExist:
                continue
    return attached_files
