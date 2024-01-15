# Introduction

Forked from https://github.com/davekats/canvas-student-data-export

Major changes:

- Reorganized the project structure.
- Refactored the code to make it more Pythonic.
- Added progress bars.
- Use threading where possible.
- Save assignment attachements.
- Save all user files.

---

The Canvas Student Data Export Tool can export nearly all of a student's data from Instructure Canvas Learning Management System (Canvas LMS).
This is useful when you are graduating or leaving your college or university, and would like to have a backup of all the data you had in canvas. Also, some instructors disable the built-in export tool.

The tool exports all of the following data for each course:

- Assignments
- Announcements
- Discussions
- Pages
- Files
- Modules
- Single file webpage of the Canvas page for grades, assignments, announcements, discussions, and modules

Additionally, all your files stored on Canvas (such as historic submissions and attachments) will be downloaded.

**TO DO LIST**
- [x] Export grades.
- [x] Detect when the cookies and API token are not valid.
- [ ] Use argparse.
- [ ] Add an argument to prohibit overwriting existing files.
- [ ] Have the path to the Chrome binary be specified by a required argument.
- [ ] Use logging.
- [ ] Refactor `download_canvas.py`.
- [ ] Refactor `export.py`.

## Install

```shell
pip install -r requirements.txt
npm install
```

Make sure you have Chomium or Chrome installed. Currently, the executable path is hardcoded to `/usr/bin/chromium-browser` in `module/singlefile.py`. If you are not on Linux or do not use Chromium, you will need to change the path.

## Run

1. Get your Canvas API key by going to Canvas and navigating to `Account` > `Settings` > `Approved Integrations` > `New Access Token`
2. Get your Canvas User ID at `https://example.instructure.com/api/v1/users/self` in the `id` field
3. Save your cookies for your Canvas domain

Then, create the file `credentials.yaml` with the following content:

```yaml
API_URL: [ base Canvas URL of your institution ]
API_KEY: [ API Key from Canvas ]
USER_ID: [ user ID from Canvas ]
COOKIES_PATH: [ path to cookies file ]
```

Make `credentials.yaml` is in the same directory as `export.py`.

<br>

Now, run the program:

```shell
python export.py
```

The folder `./output` will be created and your data downloaded to this path.
