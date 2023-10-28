from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import canvasapi
from tqdm import tqdm

from module.helpers import make_valid_folder_path


def do_download(task):
    task[1].parent.mkdir(parents=True, exist_ok=True)
    task[0].download(task[1])


def download_user_files(canvas: canvasapi.Canvas, base_path: str):
    base_path = Path(base_path)
    user = canvas.get_current_user()
    folders = []
    for folder in user.get_folders():
        n = folder.full_name.lstrip('my files/')
        if n:
            c_n = make_valid_folder_path(n)
            folders.append((folder, c_n))

    files = []
    for folder, folder_name in tqdm(folders, desc='Fetching User Files'):
        for file in folder.get_files():
            out_path = base_path / folder_name / file.display_name
            files.append((file, out_path))

    with ThreadPoolExecutor(max_workers=10) as executor:
        bar = tqdm(files, desc='Downloading User Files')
        futures = [executor.submit(do_download, task) for task in files]
        for _ in as_completed(futures):
            bar.update()
