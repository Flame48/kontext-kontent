from dataclasses import dataclass, field
import dataclasses
from typing import Any, Dict, List, Optional, Literal, Tuple, Union

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
  banner: Optional[Image] = None
  metadata: Dict = field(default_factory=dict)

def asdict(dc) -> Dict:
  return dataclasses.asdict(dc, dict_factory=lambda x: {k: v for (k, v) in x if v is not None})