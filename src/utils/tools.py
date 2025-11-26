from customtkinter import *

from PIL import Image

from types import SimpleNamespace as sn
from tkinter import ttk

def Button(master, text, command, **kwargs):
  return CTkButton(master, text=text, command=command,  **kwargs)

def Label(master,  text,  **kwargs):
  return CTkLabel(master, text=text, **kwargs)

def load_image_to_btn(source, size=(24, 24)):
  try:
    img_pil = Image.open(source)
  except FileNotFoundError:
    print('Error: Imagen no encontrada')
    img_pil = None

  if img_pil:
    return CTkImage(
      light_image=img_pil,
      dark_image=img_pil,
      size=size
    )
  
class MsgBox(CTkToplevel):
   def __init__(self, master, title, msg):
    super().__init__(master)
    self.title(title)
    self.geometry('400x200')
    self.transient(master)
    self.grab_set()

    self.label = Label(self, msg, wraplength=280)
    self.label.pack(pady=20, padx=20)

    self.button = Button(self, 'OK', self.destroy)
    self.button.pack(pady=10)


class TABView(CTkTabview):
  def __init__(self, master, size = (780, 580), **kwargs):
    width, height = size
    super().__init__(master, width=width, height=height, **kwargs)
    self._tabs = {}

  def add_tabs(self, tabs_list:list[dict|sn]):
     for tab_props in tabs_list:
        self.add(**(vars(tab_props) if isinstance(tab_props, sn) else tab_props))

  def add(self, key:str, title:str, content:callable):
    if key in self._tabs:
      print(f"La clave '{ key }' ya existe. No se añadió la pestaña.")
      return None

    frame = super().add(title)
    content = content(frame)

    self._tabs[key] = sn(frame=frame, title=title, content=content)

  def get_tab(self, key):
    return self._tabs.get(key)

  def set_tab(self, key: str):
     tab_info = self.get_tab(key)
     if tab_info:
        super().set(tab_info.title)
     else:
        print(f'Pestaña con la clave "{key}" no se encontró.') 

class Fonts:
  _fonts = {}
  
  @classmethod
  def load_fonts(cls, fonts:dict[str, dict]):
    for key, props in fonts.items():
      if key not in cls._fonts:
        cls._fonts[key] = CTkFont(**props)

  @classmethod
  def get(cls, key):
    try:
      return cls._fonts.get(key)
    except KeyError:
      raise KeyError(f"La fuente con la clave '{key}' no ha sido registrada.")

class Frame(CTkFrame):
  def __init__(self, master, pack: dict|sn = None, grid: dict|sn = None, **kwargs):
    
    style = {
        'fg_color':"#262433" ,
        'corner_radius': 10
    }
    style.update(kwargs)

    super().__init__(master, **style)

    if pack is not None:
      pack_args = vars(pack) if isinstance(pack, sn) else pack
      self.pack(**pack_args)

    if grid is not None:
      grid_args = vars(grid) if isinstance(grid, sn) else grid
      self.grid(**grid_args)

class TreeViewManager:
  def __init__(self, parent, columns, show_scrollbar=True):
    self.frame = ttk.Frame(parent)
    self.columns = columns
    self.row_count = 0

    column_ids = list(self.columns.keys())
    self.tree = ttk.Treeview(self.frame, columns=column_ids, show="headings")

    for col_id, props in self.columns.items():
        text = props.get('text', col_id)
        width = props.get('width', 100)
        anchor = props.get('anchor', 'w')
        self.tree.heading(col_id, text=text)
        self.tree.column(col_id, width=width, anchor=anchor)

    self.tree.tag_configure('oddrow', background='#E8E8E8')
    self.tree.tag_configure('evenrow', background='white')
    
    if show_scrollbar:
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    self.tree.pack(side="left", fill="both", expand=True)

  def pack(self, **kwargs):
    self.frame.pack(**kwargs)

  def grid(self, **kwargs):
    self.frame.grid(**kwargs)

  def place(self, **kwargs):
    self.frame.place(**kwargs)

  def insert_row(self, values, at_end=True):
    tag = 'evenrow' if self.row_count % 2 == 0 else 'oddrow'
    index = 'end' if at_end else 0
    self.tree.insert("", index, values=values, tags=(tag,))
    self.row_count += 1

  def load_data(self, data_list):
    self.clear_data()
    for row_values in data_list:
        self.insert_row(row_values)

  def clear_data(self):
    for item in self.tree.get_children():
        self.tree.delete(item)
    self.row_count = 0

  def get_selected_item_values(self):
    selected_items = self.tree.selection()
    if not selected_items:
        return None
    
    item_id = selected_items[0]
    item = self.tree.item(item_id)
    return item['values']

  def bind_selection(self, callback):
    def _on_select(event):
        values = self.get_selected_item_values()
        if values:
            callback(values)
    
    self.tree.bind("<<TreeviewSelect>>", _on_select)