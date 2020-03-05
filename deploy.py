import os
from zipfile import ZipFile

from bs4 import BeautifulSoup
from requests.sessions import Session

from addon.constants import MODEL_NAME

username = os.environ.get('ANKI_USERNAME')
password = os.environ.get('ANKI_PASSWORD')
addon_id = os.environ.get('ANKI_ADDON_ID')

print(username)
print(password)
print(addon_id)


def create_zip():
    file_paths = []
    exclude_dirs = ['test', '__pycache__', '.git', '.idea', '.pytest_cache', 'screenshots']
    exclude_files = ['README.md', '.gitignore', '.travis.yml', 'deploy.py', 'requirements.txt', '.DS_Store', 'meta.json']
    exclude_ext = ['.png', '.ui', '.qrc', '.log', '.zip', '.tpl']
    for dirname, sub_dirs, files in os.walk("."):
        for d in exclude_dirs:
            if d in sub_dirs:
                sub_dirs.remove(d)
        for f in exclude_files:
            if f in files:
                files.remove(f)
        for ext in exclude_ext:
            for f in files[:]:
                if f.endswith(ext):
                    files.remove(f)
        for filename in files:
            file_paths.append(os.path.join(dirname, filename))

    with ZipFile(f'{MODEL_NAME}.zip', 'w') as zf:
        for file in file_paths:
            zf.write(file)


def update(title, tags, desc):
    s = Session()
    URL = 'https://ankiweb.net/account/login'
    rsp = s.get(URL)
    soup = BeautifulSoup(rsp.text, features="html.parser")
    csrf_token = soup.find('input', {'name': 'csrf_token'}).get('value')
    s.post(URL, data={'submit': 1, 'csrf_token': csrf_token, 'username': username, 'password': password})

    URL = 'https://ankiweb.net/shared/upload'
    file = {'v21file': open(f'{MODEL_NAME}.zip', 'rb')}
    rsp = s.post(URL, files=file, data={
        'title': title,
        'tags': tags,
        'desc': desc,
        'id': addon_id,
        'submit': 'Update',
        'v21file': file,
        'v20file': '',
    })
    if rsp.url == f'https://ankiweb.net/shared/info/{addon_id}':
        return True
    else:
        return False


def main():
    create_zip()
    # with open('anki_addon_page.tpl', encoding='utf-8') as tpl:
    #     return update('Dict2Anki（有道,欧陆词典单词本同步工具）', '有道 欧陆 导入 同步', tpl.read())


if __name__ == '__main__':
    if main():
        exit(0)
    else:
        exit(1)
