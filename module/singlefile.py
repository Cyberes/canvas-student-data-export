from subprocess import run

SINGLEFILE_BINARY_PATH = "./node_modules/single-file/cli/single-file"
CHROME_PATH = "/usr/bin/chromium-browser"


def add_quotes(s):
    return "\"" + str(s).strip("\"") + "\""


def download_page(url, cookies_path, output_path, output_name_template=""):
    # TODO: we can probably safely exclude pages that match the regex r'/external_tools/retrieve\?'

    args = [
        add_quotes(SINGLEFILE_BINARY_PATH),
        "--browser-executable-path=" + add_quotes(CHROME_PATH.strip("\"")),
        "--browser-cookies-file=" + add_quotes(cookies_path),
        "--output-directory=" + add_quotes(output_path),
        add_quotes(url)
    ]

    if output_name_template != "":
        args.append("--filename-template=" + add_quotes(output_name_template))

    try:
        run("node " + " ".join(args), shell=True)
    except Exception as e:
        print("Was not able to save the URL " + url + " using singlefile. The reported error was " + e.strerror)
