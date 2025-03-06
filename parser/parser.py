import os
from dataclasses import dataclass, asdict, field
import json
import shutil
from typing import Any, Dict, List, Optional, Literal, Tuple, Union
import uuid
from bs4 import BeautifulSoup, NavigableString, Tag

API_ROOT_URL = "https://raw.githubusercontent.com/Flame48/kontext-kontent/refs/heads/main"

@dataclass
class Br:
  type: str = "br"

@dataclass
class Text:
  content: str
  type: str = "text"
  format: Optional[List[Union[
    Literal["bold"],
    Literal["italic"],
    Literal["underline"]
  ]]] = field(default_factory=list)
  
@dataclass
class Link:
  href: str
  text: Text
  type: str = "link"

@dataclass
class Image:
  src: str
  alt: str
  type: str = "image"

@dataclass
class Paragraph:
  elements: List[Union[Text, Br, Link, Image]]
  type: str = "paragraph"
  
@dataclass
class Section:
  elements: List[Union["Section", Paragraph]]
  heading: str
  type: str = "section"

@dataclass
class Document:
  id: str
  title: str
  elements: List[Union["Section", Paragraph]]
  metadata: Dict = field(default_factory=dict)

def getPaths(dirPath: str) -> Tuple[str, str|None, str|None]:
  dirPath = os.path.abspath(dirPath)
  
  html_path = None
  image_path = None
  thumbnail_filepath = None
  
  for d in os.listdir(dirPath):
    if (html_path == None) and (os.path.isfile(dirPath+"/"+d)):
      _, fExt = os.path.splitext(d)
      if (fExt == '.html'):
        html_path = os.path.abspath(dirPath+"/"+d)
    
    if (thumbnail_filepath == None) and (os.path.isfile(dirPath+"/"+d)):
      fName, _ = os.path.splitext(d)
      if (fName == 'thumbnail'):
        thumbnail_filepath = os.path.abspath(dirPath+"/"+d)
    
    if (image_path == None) and (d == 'images'):
      image_path = os.path.abspath(dirPath+"/"+d)
  if (html_path==None):
    raise IOError("Html page not found in given directory.")
  
  return html_path, image_path, thumbnail_filepath

def getSoup(fp: str) -> BeautifulSoup:
  with open(fp, 'r', encoding='utf-8') as f:
    soup: BeautifulSoup =  BeautifulSoup(f.read(), 'html.parser')
    body = soup.find('body')
    return body

imgRootUrl = ''
def nest(soup: BeautifulSoup|Tag) -> List[Dict]:
  toRet = []
  for c in soup.children:
    if isinstance(c, NavigableString):
      toRet.append({
        'type': 'text',
        'content': c.strip(),
      })
    else:
      c: Tag
      if c.name in ['sup']:
        continue
      if c.name == 'img':
        toRet.append({
          'type': c.name,
          'src': (imgRootUrl+c['src']) if 'src' in c.attrs else '#',
          'alt': c['alt'] if 'alt' in c.attrs else ''
        })
        continue
      if c.name == 'a':
        toRet.append({
          'type': c.name,
          'href': c['href'] if 'href' in c.attrs else '#',
          'children': nest(c),
        })
        continue
      toRet.append({
        'type': c.name,
        'children': nest(c),
      })
  return toRet

def resolveSpans(nst: List[Dict]) -> List[Dict]:
  toRet: List[Dict] = []
  for tg in nst:
    if (tg['type'] == 'span'):
      toRet.extend(resolveSpans(tg['children']))
    else:
      if ('children' in tg):
        tg['children'] = resolveSpans(tg['children'])
      toRet.append(tg)
  return toRet

def mergeText(nst: List[Dict]) -> List[Dict]:
  toRet: List[Dict] = []
  txtToAdd: Dict = {
    'type': 'text',
    'content': '',
  }
  
  for tg in nst:
    if (tg['type'] == 'text'):
      txtToAdd['content'] = (txtToAdd['content']+' '+tg['content']).strip()
    else:
      if len(txtToAdd['content']) != 0:
        toRet.append(txtToAdd)
      if ('children' in tg):
        tg['children'] = mergeText(tg['children'])
      toRet.append(tg)
  
  if len(txtToAdd['content']) != 0:
    toRet.append(txtToAdd)
    
  return toRet

def isNonEmpty(tg: Dict) -> bool:
  if (tg['type'] == 'text'):
    return len(tg['content'].strip())!=0
  if (tg['type'] in ['br', 'img']):
    return True
  if not ('children' in tg):
    return True
  if (len(tg['children']) == 0):
    return False
  for c in tg['children']:
    if (isNonEmpty(c)):
      return True
  return False

def sectionate(nst: List[Dict], baseLvl: int = 0) -> List[Dict]:
  toRet: List[Dict] = []
  activeSection = {
    'type': 'section',
    'level': baseLvl,
    'children': [],
  }
  
  allNonHeading: bool = True
  for tg in nst:
    if (tg['type'] in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
      allNonHeading = False
      lvl: int = int(tg['type'][1])
      if (lvl <= activeSection['level']):
        if (len(activeSection['children']) != 0):
          if not ('heading' in activeSection):
            toRet.extend(activeSection['children'])
          else:
            toRet.append(activeSection)
        activeSection = {
          'type': 'section',
          'heading': tg,
          'level': lvl,
          'children': [],
        }
        continue
    activeSection['children'].append(tg)
  
  if (len(activeSection['children']) != 0):
    if not ('heading' in activeSection):
      toRet.extend(activeSection['children'])
    else:
      toRet.append(activeSection)
    
  if allNonHeading:
    return toRet
  
  for sc in toRet:
    if sc['type'] == 'section':
      sc['children'] = sectionate(sc['children'], sc['level']+1)
    
  return toRet

def getText(nst: List[Dict]) -> Dict:
  for c in mergeText(nst):
    if (c['type'] == 'text'):
      return c
  return {
    'type': 'text',
    'content': '',
  }

def natify(nst: List[Dict]|Dict) -> List[Union["Section", Paragraph]]|Any:
  
  if (isinstance(nst, dict)):
    match(c['type']):
      case 'p':
        return Paragraph(natify(c['children']))
      case 'section':
        return Section(natify(c['children']),  getText(c['heading']['children'])['content'])
      case 'img':
        return Image(c['src'], c['alt'])
      case 'a':
        return Link(c['href'], natify(getText(c['children'])))
      case 'text':
        return Text(c['content'])
      case 'br':
        return Br()
    return
  
  toRet: List[Union["Section", Paragraph]] = []
  for c in nst:
    match(c['type']):
      case 'p':
        toRet.append(Paragraph(natify(c['children'])))
      case 'section':
        toRet.append(Section(natify(c['children']), getText(c['heading']['children'])['content']))
      case 'img':
        toRet.append(Image(c['src'], c['alt']))
      case 'a':
        toRet.append(Link(c['href'], natify(getText(c['children']))))
      case 'text':
        toRet.append(Text(c['content']))
      case 'br':
        toRet.append(Br())
      case _:
        continue
        # raise KeyError(f"Invalid Key {c['type']}")
  return toRet

def generateUUID() -> str:
  docs: set[str] = {
    k
    for k in os.listdir("./docs/")
      if os.path.isdir("./docs/"+k)
  }
  
  while True:
    new_id: str = str(uuid.uuid4())
    if not (new_id in docs):
      return new_id

def updateSrc(doc: Dict, id: str) -> None:
  if 'src' in doc:
    newSrcEndPoint = f'/docs/{id}/'+doc['src']
    if os.path.exists('.'+newSrcEndPoint):
      doc['src'] = API_ROOT_URL+newSrcEndPoint
  if 'elements' in doc:
    for c in doc['elements']: updateSrc(c, id)

def addFiles(doc: Document, image_path: str|None, thumbnail_filepath: str|None):
  
  id: str = doc.id
  
  doc_path = "./docs"
  try:
    os.mkdir(doc_path+"/"+id)
  except FileExistsError as e:
    print("Document already exists!")
    raise e
  except FileNotFoundError as e:
    print("Directory does not exist!")
    raise e
  
  if thumbnail_filepath!=None:
    os.makedirs(doc_path+"/"+id+"/images", exist_ok=True)
    if (os.path.isfile(thumbnail_filepath)):
      shutil.copy2(thumbnail_filepath, doc_path+"/"+id+"/images")
  if image_path!=None:
    os.makedirs(doc_path+"/"+id+"/images", exist_ok=True)
    for i in os.listdir(image_path):
      if (os.path.isfile(image_path+"/"+i)):
        shutil.copy2(image_path+"/"+i, doc_path+"/"+id+"/images")
  
  doc_json = {}
  doc_json["$schema"] = API_ROOT_URL+"/parser/document_content_schema.json"
  doc_json.update(asdict(doc))
  
  updateSrc(doc_json, id)
  
  with open(doc_path+"/"+id+"/content.json", "x") as of:
    json.dump(doc_json, of, indent=2)

def getUserInput() -> Dict:
  
  while True:
    folder_path: str = os.path.abspath(input(">> Path to Exported Directory: "))
    page_title: str = input(">> Page Title: ")
    author: str = input(">> Author: ")
    publish_date: str = input(">> Publish Date: ")
    
    is_ok: bool = input("Is the above information correct (Enter 'Y' for yes) [Y/N]:") == "Y"
    if is_ok:
      break
  
  return {
    'folder_path': folder_path,
    'page_title': page_title,
    'author': author,
    'publish_date': publish_date,
  }

def updateRootContentJSON(id, title, author, publish_date, thumbnail_filepath, thumbnail_alt):
  with open('./content.json', 'r') as f:
    orig = json.load(f)
  
  if id in orig:
    raise KeyError("ID Already in Content Manager")
  
  orig[id] = {
    'title': title,
    'author': author,
    'publishDate': publish_date,
    'img': {
      'src': '/assets/images/books.avif' if thumbnail_filepath==None else f'{API_ROOT_URL}/docs/{id}/images/{os.path.basename(thumbnail_filepath)}',
      'alt': title if thumbnail_alt==None else thumbnail_alt
    },
    'showTitleOverlay': False,
  }
  with open('./content.json', 'w') as of:
    json.dump(orig, of, indent=2)

if __name__ == '__main__':
  
# >- GET FROM USER ----------------------< #
  user_inp: Dict = getUserInput()
  folder_path = user_inp["folder_path"]
  page_title = user_inp["page_title"]
  author = user_inp["author"]
  publish_date = user_inp["publish_date"]
# >--------------------------------------< #
  
  html_path, image_path, thumbnail_filepath = getPaths(folder_path)
  
  thumbnail_alt = page_title
  
  if thumbnail_filepath != None:
    thumbnail_alt_inp = input('Enter Alt Text for Thumbnail Image (Or leave blank for page title): ').strip()
    if len(thumbnail_alt_inp) != 0:
      thumbnail_alt = thumbnail_alt_inp
  
  soup: BeautifulSoup = getSoup(html_path)
  de_spanned = resolveSpans(nest(soup))
  m_text = mergeText(de_spanned)
  rem_empty = list(filter(isNonEmpty, m_text))
  
  sectioned = sectionate(rem_empty, 1)
  native: List[Section | Paragraph] = natify(sectioned)
  
  final = Document(generateUUID(), page_title, native)
  
  updateRootContentJSON(final.id, page_title, author, publish_date, thumbnail_filepath, thumbnail_alt)
  addFiles(final, image_path, thumbnail_filepath)