import json
import stat
import pyuac
import os
import re
import shutil
from urllib.parse import quote

from bs4 import BeautifulSoup
import web_parser
from parser_datatypes import *

analyses_path: Literal['./api/analyses/'] = './api/analyses/'

def get_analysis_dir() -> dict:
  to_ret: dict
  with open(f'{analyses_path}directory.json', 'r') as f:
    to_ret = json.load(f)
  return to_ret

def set_analysis_dir(to_set: dict) -> None:
  with open(f'{analyses_path}directory.json', 'w') as of:
    json.dump(to_set, of, indent=2)

def add_analysis(
  new_analysis_dirpath: str,
  page_title: str,
  author: str,
  publish_date: str,
  thumbnail_alt: Optional[str],
  banner_alt: Optional[str],
) -> None:
  direct = get_analysis_dir()
  if quote(page_title) in direct:
    raise ValueError("Document Already Stored!")
  html_path, image_path, thumbnail_filepath, banner_filepath = web_parser.getPaths(new_analysis_dirpath)
  
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
  
  soup: BeautifulSoup = web_parser.getSoup(html_path)
  de_spanned = web_parser.resolveSpans(web_parser.nest(soup))
  m_text = web_parser.mergeText(de_spanned)
  rem_empty = list(filter(web_parser.isNonEmpty, m_text))
  
  sectioned = web_parser.sectionate(rem_empty, 1)
  native: List[Section | Paragraph] = web_parser.natify(sectioned)
  
  page_title: str
  doc_id: str = page_title.replace(" ", "_")
  doc_id = re.sub(r'[\\/*?:"<>|#%]', "", doc_id)
  doc_id = doc_id.strip(' .')
  
  banner: Optional[Image] = None
  if (banner_filepath!=None):
    banner = Image(f'{doc_id}/images/{os.path.basename(banner_filepath)}', banner_alt)
  
  final = Document(doc_id, page_title, native, banner=banner)
  
  try:
    os.mkdir(f'{analyses_path}{doc_id}')
  except FileExistsError as e:
    print("Document already exists!")
    raise e
  except FileNotFoundError as e:
    print("Directory does not exist!")
    raise e
  
  if thumbnail_filepath!=None:
    os.makedirs(f"{analyses_path}{doc_id}/images/", exist_ok=True)
    if (os.path.isfile(thumbnail_filepath)):
      shutil.copy2(thumbnail_filepath, f"{analyses_path}{doc_id}/images/")
  
  if banner_filepath!=None:
    os.makedirs(f"{analyses_path}{doc_id}/images/", exist_ok=True)
    if (os.path.isfile(banner_filepath)):
      shutil.copy2(banner_filepath, f"{analyses_path}{doc_id}/images/")
  
  if image_path!=None:
    os.makedirs(f"{analyses_path}{doc_id}/images/", exist_ok=True)
    for i in os.listdir(image_path):
      if (os.path.isfile(image_path+"/"+i)):
        shutil.copy2(image_path+"/"+i, f"{analyses_path}{doc_id}/images")
  
  doc_json = {}
  doc_json["$schema"] = web_parser.API_ROOT_URL.removesuffix("api/")+"parser/document_content_schema.json"
  doc_json.update(asdict(final))
  
  web_parser.updateSrc(f'{analyses_path}{doc_id}/', doc_json)
  with open(f'{analyses_path}{doc_id}/content.json', "x") as of:
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
  
  set_analysis_dir(direct)

def remove_analysis(analysis_id: str) -> None:
  direct = get_analysis_dir()
  
  if analysis_id not in direct:
    raise KeyError("Given analysis not found in directory!")
  
  if not os.path.exists(f'{analyses_path}{analysis_id}'):
    raise FileNotFoundError("Given analysis data couldn't be found in system!")
  print(analysis_id)
  
  def onerror(func, path, exc_info):
    exc_class, _, _ = exc_info
    if exc_class == PermissionError:
      os.chmod(path, stat.S_IWUSR)
      func(path)
    else:
      raise
  
  shutil.rmtree(f'{analyses_path}{analysis_id}', False, onerror)
  del direct[analysis_id]
  
  set_analysis_dir(direct)

def list_analysis() -> list[str]:
  direct = get_analysis_dir()
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

def analysis_cli(*args, **kwargs):
  
  while True:
    print("What doin?")
    print("1. Add Analysis")
    print("2. Remove Analysis")
    print("3. List Analyses")
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
            conf_fp = './parser/parse_config.yaml'
          user_in = load_config(conf_fp)
        else:
          user_in = read_cli_config()
        add_analysis(
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
        keys: list[str] = list_analysis()
        print("Available Analyses")
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
        remove_analysis(keys[remIndx])
        print("Successfully Removed!")
        continue
      case '3':
        print("Available Analyses:")
        for i, k in enumerate(list_analysis(), 1): print(f'{i}. \"{k}\"')
        continue
      case '4':
        print("Exiting!")
        break
      case _:
        print("INVALID CHOICE")
        print()
        continue

if __name__ == '__main__':
  analysis_cli()