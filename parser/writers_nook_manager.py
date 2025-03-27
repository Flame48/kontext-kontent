import json
import stat
import os
import re
import shutil
from urllib.parse import quote

from bs4 import BeautifulSoup
import web_parser
from parser_datatypes import *

writers_nook_path: Literal['./api/writers_nook/'] = './api/writers_nook/'
def get_writers_nook_dir() -> dict:
  to_ret: dict
  with open(f'{writers_nook_path}directory.json', 'r') as f:
    to_ret = json.load(f)
  return to_ret

def set_writers_nook_dir(to_set) -> None:
  with open(f'{writers_nook_path}directory.json', 'w') as of:
    json.dump(to_set, of, indent=2)

def get_tag_list(memo_entries: dict) -> list[str]:
  tags: set = set()
  for v in memo_entries.values(): tags |= set(v['tags'])
  return list(tags)

def add_memo(
  new_memo_dirpath: str,
  page_title: str,
  author: str,
  publish_date: str,
  tags: list[str],
) -> None:
  direct = get_writers_nook_dir()
  if quote(page_title) in direct["items"]:
    raise ValueError("Document Already Stored!")
  
  html_path, image_path, _, _ = web_parser.getPaths(new_memo_dirpath)
  
  native: List[Section | Paragraph] = web_parser.parse(html_path)
  
  doc_id: str = web_parser.get_doc_id(page_title)
  
  final = Document(doc_id, page_title, native)
  
  try:
    os.mkdir(f'{writers_nook_path}{doc_id}')
  except FileExistsError as e:
    print("Document already exists!")
    raise e
  except FileNotFoundError as e:
    print("Directory does not exist!")
    raise e
  
  if image_path!=None:
    os.makedirs(f"{writers_nook_path}{doc_id}/images/", exist_ok=True)
    for i in os.listdir(image_path):
      if (os.path.isfile(image_path+"/"+i)):
        shutil.copy2(image_path+"/"+i, f"{writers_nook_path}{doc_id}/images")
  
  doc_json = {}
  doc_json["$schema"] = web_parser.API_ROOT_URL.removesuffix("api/")+"parser/document_content_schema.json"
  doc_json.update(asdict(final))
  
  web_parser.updateSrc(f'{writers_nook_path}{doc_id}/', doc_json)
  with open(f'{writers_nook_path}{doc_id}/content.json', "x") as of:
    json.dump(doc_json, of, indent=2)
  
  direct["items"][doc_id] = {
    'title': page_title,
    'author': author,
    'publishDate': publish_date,
    'tags': tags
  }
  
  direct["tags"] = get_tag_list(direct["items"])
  set_writers_nook_dir(direct)

def remove_memo(memo_id: str) -> None:
  direct = get_writers_nook_dir()
  
  if memo_id not in direct["items"]:
    raise KeyError("Given memo not found in directory!")
  
  if not os.path.exists(f'{writers_nook_path}{memo_id}'):
    raise FileNotFoundError("Given memo data couldn't be found in system!")
  
  def onerror(func, path, exc_info):
    exc_class, _, _ = exc_info
    if exc_class == PermissionError:
      os.chmod(path, stat.S_IWUSR)
      func(path)
    else:
      raise
  shutil.rmtree(f'{writers_nook_path}{memo_id}', False, onerror)
  del direct["items"][memo_id]
  
  direct["tags"] = get_tag_list(direct["items"])
  set_writers_nook_dir(direct)

def list_memo() -> list[str]:
  direct = get_writers_nook_dir()
  return list(direct["items"].keys())

def load_config(fp: str):
  if (fp!=None) and os.path.exists(fp) and os.path.isfile(fp):
    import yaml
    with open(fp, "r") as cf:
      config = yaml.load(cf, Loader=yaml.SafeLoader)
    return config
  else:
    raise FileNotFoundError("Config file not found!")

def read_cli_config() -> dict:
  while True:
    folder_path: str = os.path.abspath(input("> Path to Exported Directory: "))
    page_title: str = input("> Page Title: ")
    author: str = input("> Author: ")
    publish_date: str = input("> Publish Date: ")
    tags: list[str] = []
    print("Inputting tags: [Enter empty to stop]")
    while (inp:=input("> ").strip()) != '': tags.append(inp.lower())

    is_ok: bool = input("Is the above information correct (Enter 'Y' for yes) [Y/N]:") == "Y"
    if is_ok:
      break
  return {
    'folder_path': folder_path,
    'page_title': page_title,
    'author': author,
    'publish_date': publish_date,
    'tags': tags
  }

def writers_nook_cli(*args, **kwargs):
  while True:
    print("What doin?")
    print("1. Add Memo")
    print("2. Remove Memo")
    print("3. List Memos")
    print("4. Exit")
    ch = input("> ").strip()
    match(ch):
      case '1':
        print("Read Config? [Y/N]:")
        read_conf: str = input("> ").strip().lower()
        user_in: dict
        if read_conf == 'y':
          print("Enter config path [Enter nothing for default fp]:")
          conf_fp: str = input("> ").strip()
          if conf_fp=='':
            conf_fp = './parser/configs/nook_config.yaml'
          user_in = load_config(conf_fp)
        else:
          user_in = read_cli_config()
        add_memo(
          user_in['folder_path'],
          user_in['page_title'],
          user_in['author'],
          user_in['publish_date'],
          user_in['tags'],
        )
        print("Successfully Added!")
        continue
      case '2':
        keys: list[str] = list_memo()
        print("Available Memos")
        for i, k in enumerate(keys, 1): print(f'{i}. \"{k}\"')
        to_rem_indx = input('Enter number to remove [N/n to go back]:\n> ').strip()
        if to_rem_indx.lower() == 'n': continue
        if not to_rem_indx.isnumeric():
          print("INVALID INPUT")
          print()
          continue
        remIndx = int(to_rem_indx)-1
        if (remIndx<0) or (remIndx>=len(keys)):
          print("INVALID INPUT")
          print()
          continue
        remove_memo(keys[remIndx])
        print("Successfully Removed!")
        continue
      case '3':
        print("Available Memos:")
        for i, k in enumerate(list_memo(), 1): print(f'{i}. \"{k}\"')
        continue
      case '4':
        print("Exiting!")
        break
      case _:
        print("INVALID CHOICE")
        print()
        continue

if __name__ == '__main__':
  writers_nook_cli()