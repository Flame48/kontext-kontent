import json
import os
from typing import Literal, Optional

people_path: Literal['./api/people'] = './api/people/'
def get_people_dir() -> dict:
  to_ret: dict
  with open(f"{people_path}directory.json", "r") as f:
    to_ret = json.load(f)
  return to_ret

def set_people_dir(to_set) -> None:
  with open(f"{people_path}directory.json", "w") as of:
    json.dump(to_set, of, indent=2)

def add_person(
  name: str,
  roles: list[str],
  img: dict,
  linkTo: str
) -> None:
  direct = get_people_dir()
  for r in roles:
    if r not in direct['roles']:
      raise ValueError(f"Role {r} not a valid role.")
  
  direct["people"].append({
    "name": name,
    "roles": roles,
    "img": img,
    "linkTo": linkTo,
  })
  
  set_people_dir(direct)

def remove_person(indx: int) -> None:
  direct = get_people_dir()
  if (indx<0) or (indx>=len(direct["people"])):
    raise ValueError("Index out of range!")
  direct["people"].pop(indx)
  set_people_dir(direct)

def update_person(
  indx: int,
  name: Optional[str] = None,
  roles: Optional[list[str]] = None,
  img: Optional[dict] = None,
  linkTo: Optional[str] = None,
) -> None:
  direct = get_people_dir()
  if (indx<0) or (indx>=len(direct["people"])):
    raise ValueError("Index out of range!")
  if name != None: direct["people"][indx]["name"] = name
  if roles != None: direct["people"][indx]["roles"] = roles
  if img != None: direct["people"][indx]["img"] = img
  if linkTo != None: direct["people"][indx]["linkTo"] = linkTo
  set_people_dir(direct)

def list_people() -> list[str, str]:
  direct = get_people_dir()
  return [p['name'] for p in direct['people']]

def print_person(p: dict) -> None:
  print(f"NAME: {p['name']}")
  print(f"ROLES: {p['roles']}")
  print(f"LINK: {p['linkTo']}")
  print(f"IMG: {p['img']['src']}")

def load_config(fp: str):
  if (fp!=None) and os.path.exists(fp) and os.path.isfile(fp):
    import yaml
    with open(fp, "r") as cf:
      config = yaml.load(cf, Loader=yaml.SafeLoader)
    return config
  else:
    raise FileNotFoundError("Config file not found!")

def read_cli_config(mayBeNone: bool = False) -> dict:
  direct = get_people_dir()
  while True:
    name: str = input("> Name: ").strip()
    if mayBeNone and (name == ''): name = None
    roles: list[str] = []
    
    print("Inputting Roles [Enter empty to stop]")
    while True:
      inp = input("> ").strip()
      if (inp == ''): break
      if inp not in direct["roles"]:
        print("Invalid Role. Try again.")
        continue
      roles.append(inp)
    if mayBeNone and (len(roles)==0): roles = None
    
    img: dict = {
      'src': input("> Rel Source: ").strip(),
      'alt': f'Image of {name}',
    }
    if mayBeNone and (img['src']==''): img = None
    
    linkTo: str = input("> Link to: ").strip()
    if mayBeNone and (linkTo==''): linkTo = None

    is_ok: bool = input("Is the above information correct (Enter 'Y' for yes) [Y/N]:") == "Y"
    if is_ok: break
  
  return {
    'name': name,
    'roles': roles,
    'img': img,
    'linkTo': linkTo,
  }

def people_cli(*args, **kwargs) -> None:
  while True:
    print("What doin?")
    print("1. Add Person")
    print("2. Remove Person")
    print("3. Update Person")
    print("4. List People")
    print("5. Exit")
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
            conf_fp = './parser/configs/person_config.yaml'
          user_in = load_config(conf_fp)
        else:
          user_in = read_cli_config()
        add_person(
          user_in['name'],
          user_in['roles'],
          user_in['img'],
          user_in['linkTo'],
        )
        print("Successfully Added!")
        continue
      case '2':
        names: list[str] = list_people()
        print("Available People")
        should_remove: bool = False
        while True:
          for i, k in enumerate(names, 1): print(f'{i}. \"{k}\"')
          to_rem_indx = input('Enter number to remove [N/n to go back]:\n> ').strip()
          if to_rem_indx.lower() == 'n': break
          if not to_rem_indx.isnumeric():
            print("INVALID INPUT")
            print()
            continue
          remIndx = int(to_rem_indx)-1
          if (remIndx<0) or (remIndx>=len(names)):
            print("INVALID INPUT")
            print()
            continue
          print_person(get_people_dir()['people'][remIndx])
          i = input("> Is this the person you want to remove? [Y/N]: ").strip().lower()
          if i=='y':
            should_remove = True
            break
        if not should_remove:
          continue
        remove_person(remIndx)
        print("Successfully Removed!")
        continue
      case '3':
        names: list[str] = list_people()
        print("Available People")
        should_modify: bool = False
        while True:
          for i, k in enumerate(names, 1): print(f'{i}. \"{k}\"')
          to_mod_indx = input('Enter number to modify [N/n to go back]:\n> ').strip()
          if to_mod_indx.lower() == 'n': break
          if not to_mod_indx.isnumeric():
            print("INVALID INPUT")
            print()
            continue
          modIndx = int(to_mod_indx)-1
          if (modIndx<0) or (modIndx>=len(names)):
            print("INVALID INPUT")
            print()
            continue
          print_person(get_people_dir()['people'][modIndx])
          i = input("> Is this the person you want to modify? [Y/N]: ").strip().lower()
          if i=='y':
            should_modify = True
            break
        if not should_modify:
          continue
        print("Read Config? [Y/N]:")
        read_conf: str = input("> ").strip().lower()
        user_in: dict
        if read_conf == 'y':
          print("Enter config path [Enter nothing for default fp]:")
          conf_fp: str = input("> ").strip()
          if conf_fp=='':
            conf_fp = './parser/configs/person_config.yaml'
          user_in = load_config(conf_fp)
        else:
          user_in = read_cli_config(mayBeNone=True)
        update_person(
          modIndx,
          user_in['name'] if 'name' in user_in else None,
          user_in['roles'] if 'roles' in user_in else None,
          user_in['img'] if 'img' in user_in else None,
          user_in['linkTo'] if 'linkTo' in user_in else None,
        )
        print("Successfully Modified!")
        continue
      case '4':
        print("Available Memos:")
        for i, k in enumerate(list_people(), 1): print(f'{i}. \"{k}\"')
        continue
      case '5':
        print("Exiting!")
        break
      case _:
        print("INVALID CHOICE")
        print()
        continue
  pass

if __name__ == '__main__':
  people_cli()