import json
import stat
import os
import re
import shutil
from urllib.parse import quote

from bs4 import BeautifulSoup
import web_parser
from parser_datatypes import *

book_data_path: Literal['./api/book_data/'] = './api/book_data/'


def get_book_data_dir() -> dict:
  to_ret: dict
  with open(f'{book_data_path}directory.json', 'r') as f:
    to_ret = json.load(f)
  return to_ret

def set_book_data_dir(to_set: dict) -> None:
  with open(f'{book_data_path}directory.json', 'w') as of:
    json.dump(to_set, of, indent=2)

def add_book_data(
  new_book_data_dirpath: str,
  page_title: str,
  author: str,
  publish_date: str,
  thumbnail_alt: Optional[str],
  banner_alt: Optional[str],
) -> None:
  direct = get_book_data_dir()
  if quote(page_title) in direct:
    raise ValueError("Document Already Stored!")
  html_path, image_path, thumbnail_filepath, banner_filepath = web_parser.getPaths(new_book_data_dirpath)
  
  if thumbnail_filepath != None:
    if thumbnail_alt == None:
      thumbnail_alt_inp = input('Enter Alt Text for Thumbnail Image (Or leave blank for page title): ').strip()
      if len(thumbnail_alt_inp) != 0:
        thumbnail_alt = thumbnail_alt_inp
      else:
        thumbnail_alt = f'{page_title} thumbnail image.'
  
  if banner_filepath != None:
    if banner_alt == None:
      banner_alt_inp = input('Enter Alt Text for Banner Image (Or leave blank for page title): ').strip()
      if len(banner_alt_inp) != 0:
        banner_alt = banner_alt_inp
      else:
        banner_alt = f'{page_title} banner image.'
  
  native: List[Section | Paragraph] = web_parser.parse(html_path)
  
  doc_id: str = web_parser.get_doc_id(page_title)
  
  banner: Optional[Image] = None
  if (banner_filepath!=None):
    banner = Image(f'{doc_id}/images/{os.path.basename(banner_filepath)}', banner_alt)
  
  final = Document(doc_id, page_title, native, banner=banner)
  
  try:
    os.mkdir(f'{book_data_path}{doc_id}')
  except FileExistsError as e:
    print("Document already exists!")
    raise e
  except FileNotFoundError as e:
    print("Directory does not exist!")
    raise e
  
  if thumbnail_filepath!=None:
    os.makedirs(f"{book_data_path}{doc_id}/images/", exist_ok=True)
    if (os.path.isfile(thumbnail_filepath)):
      shutil.copy2(thumbnail_filepath, f"{book_data_path}{doc_id}/images/")
  
  if banner_filepath!=None:
    os.makedirs(f"{book_data_path}{doc_id}/images/", exist_ok=True)
    if (os.path.isfile(banner_filepath)):
      shutil.copy2(banner_filepath, f"{book_data_path}{doc_id}/images/")
  
  if image_path!=None:
    os.makedirs(f"{book_data_path}{doc_id}/images/", exist_ok=True)
    for i in os.listdir(image_path):
      if (os.path.isfile(image_path+"/"+i)):
        shutil.copy2(image_path+"/"+i, f"{book_data_path}{doc_id}/images")
  
  doc_json = {}
  doc_json["$schema"] = web_parser.API_ROOT_URL.removesuffix("api/")+"parser/document_content_schema.json"
  doc_json.update(asdict(final))
  
  web_parser.updateSrc(f'{book_data_path}{doc_id}/', doc_json)
  with open(f'{book_data_path}{doc_id}/content.json', "x") as of:
    json.dump(doc_json, of, indent=2)
  
  direct[doc_id] = {
    'title': page_title,
    'author': author,
    'publishDate': publish_date,
    'img': {
      'src': 'assets/images/books.avif' if thumbnail_filepath==None else f'{doc_id}/images/{os.path.basename(thumbnail_filepath)}',
      'alt': thumbnail_alt
    },
    'showTitleOverlay': False,
  }
  
  set_book_data_dir(direct)

def remove_book_data(book_data_id: str) -> None:
  direct = get_book_data_dir()
  
  if book_data_id not in direct:
    raise KeyError("Given book_data not found in directory!")
  
  if not os.path.exists(f'{book_data_path}{book_data_id}'):
    raise FileNotFoundError("Given book_data data couldn't be found in system!")
    
  def onerror(func, path, exc_info):
    exc_class, _, _ = exc_info
    if exc_class == PermissionError:
      os.chmod(path, stat.S_IWUSR)
      func(path)
    else:
      raise
  
  shutil.rmtree(f'{book_data_path}{book_data_id}', False, onerror)
  del direct[book_data_id]
  
  set_book_data_dir(direct)

def list_book_data() -> list[str]:
  direct = get_book_data_dir()
  return list(direct.keys())

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

    is_ok: bool = input("Is the above information correct (Enter 'Y' for yes) [Y/N]:") == "Y"
    if is_ok:
      break
  return {
    'folder_path': folder_path,
    'page_title': page_title,
    'author': author,
    'publish_date': publish_date,
  }

def book_data_cli(*args, **kwargs):
  
  while True:
    print("What doin?")
    print("1. Add Analysis")
    print("2. Remove Analysis")
    print("3. List Book Data")
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
            conf_fp = './parser/configs/book_data_config.yaml'
          user_in = load_config(conf_fp)
        else:
          user_in = read_cli_config()
        add_book_data(
          user_in['folder_path'],
          user_in['page_title'],
          user_in['author'],
          user_in['publish_date'],
          user_in.get('thumbnail_alt', None),
          user_in.get('banner_alt', None),
        )
        print("Successfully Added!")
        continue
      case '2':
        keys: list[str] = list_book_data()
        print("Available Book Data")
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
        remove_book_data(keys[remIndx])
        print("Successfully Removed!")
        continue
      case '3':
        print("Available Book Data:")
        for i, k in enumerate(list_book_data(), 1): print(f'{i}. \"{k}\"')
        continue
      case '4':
        print("Exiting!")
        break
      case _:
        print("INVALID CHOICE")
        print()
        continue

if __name__ == '__main__':
  book_data_cli()
  
  # book_data