import os
import re
from urllib.parse import quote
from dataclasses import dataclass, field
import json
import shutil
from typing import Any, Dict, List, Optional, Literal, Tuple, Union
import uuid
from bs4 import BeautifulSoup, NavigableString, Tag
from parser_datatypes import *

API_ROOT_URL = "https://raw.githubusercontent.com/Flame48/kontext-kontent/refs/heads/main/api/"

def getSoup(fp: str) -> BeautifulSoup:
  with open(fp, 'r', encoding='utf-8') as f:
    soup: BeautifulSoup =  BeautifulSoup(f.read(), 'html.parser')
    body = soup.find('body')
    return body

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
          'src': c['src'] if 'src' in c.attrs else '#',
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
  if (tg['type'] in ['hr', 'img']):
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
      case 'hr':
        return Hr()
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
      case 'hr':
        toRet.append(Hr())
      case _:
        continue
        # raise KeyError(f"Invalid Key {c['type']}")
  return toRet

def updateSrc(newRoot: str, doc: Dict) -> None:
  if 'src' in doc:
    newSrcEndPoint = newRoot+doc['src']
    if os.path.exists('./api/'+newSrcEndPoint):
      doc['src'] = API_ROOT_URL+newSrcEndPoint
  if 'elements' in doc:
    for c in doc['elements']: updateSrc(newRoot, c)

def getPaths(dirPath: str) -> Tuple[str, str|None, str|None, str|None]:
  dirPath = os.path.abspath(dirPath)
  
  html_path = None
  image_path = None
  thumbnail_filepath = None
  banner_filepath = None
  
  for d in os.listdir(dirPath):
    if (html_path == None) and (os.path.isfile(dirPath+"/"+d)):
      _, fExt = os.path.splitext(d)
      if (fExt == '.html'):
        html_path = os.path.abspath(dirPath+"/"+d)
    
    if (thumbnail_filepath == None) and (os.path.isfile(dirPath+"/"+d)):
      fName, _ = os.path.splitext(d)
      if (fName == 'thumbnail'):
        thumbnail_filepath = os.path.abspath(dirPath+"/"+d)
    
    if (banner_filepath == None) and (os.path.isfile(dirPath+"/"+d)):
      fName, _ = os.path.splitext(d)
      if (fName == 'banner'):
        banner_filepath = os.path.abspath(dirPath+"/"+d)
    
    if (image_path == None) and (d == 'images'):
      image_path = os.path.abspath(dirPath+"/"+d)
      
  if (html_path==None):
    raise IOError("Html page not found in given directory.")
  
  return html_path, image_path, thumbnail_filepath, banner_filepath

def parse(html_path: str) -> List[Section | Paragraph]:
  soup: BeautifulSoup = getSoup(html_path)
  de_spanned = resolveSpans(nest(soup))
  m_text = mergeText(de_spanned)
  rem_empty = list(filter(isNonEmpty, m_text))
  
  sectioned = sectionate(rem_empty, 1)
  native: List[Section | Paragraph] = natify(sectioned)
  return native

def get_doc_id(page_title: str) -> str:
  doc_id: str = page_title.replace(" ", "_")
  doc_id = re.sub(r'[\\/*?:"<>|#%]', "", doc_id)
  doc_id = doc_id.strip(' .')
  return doc_id