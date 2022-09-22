import logging
from typing import Iterable
from libxmp import XMPFiles, consts
from PIL import Image

from helpers import short_fname


def get_metadata(fname:str) -> tuple[set[str],int]:
  xmpfile = XMPFiles(file_path=fname)
  xmp = xmpfile.get_xmp()
  if xmp is None:
    return set(), 0
  xmpfile.close_file()

  def get_tags():
    propname = (consts.XMP_NS_Lightroom, "hierarchicalSubject")
    if not xmp.does_property_exist(*propname):
      propname = (consts.XMP_NS_DC, "subject")
      if not xmp.does_property_exist(*propname):
        logging.warning("No tags in metadata of %s", short_fname(fname))
        return set()
      logging.warning("No hierarchical tags in %s", short_fname(fname))
    n = xmp.count_array_items(*propname)
    if n==0:
      logging.warning("ZERO tags in %s", short_fname(fname))
    return {xmp.get_array_item(*propname, i+1) for i in range(n)}

  def get_rating():
    propname = (consts.XMP_NS_XMP, "Rating")
    if not xmp.does_property_exist(*propname):
      return 0

    return xmp.get_property_int(*propname)

  return get_tags(), get_rating()


def write_metadata(fname:str, tags:Iterable[str]=None, rating:int=None, append:bool=True) -> None:
  xmpfile = XMPFiles(file_path=fname, open_forupdate=True)
  xmp = xmpfile.get_xmp()
  if not xmpfile.can_put_xmp(xmp):
    raise RuntimeError(f"file {fname}: metadata not writable")

  def write_tag(property, tag):
    if not xmp.does_array_item_exist(*property, tag):
      xmp.append_array_item(*property, tag, {'prop_array_is_ordered': False, 'prop_value_is_array': True})
  if tags:
    hier_tag_prop = (consts.XMP_NS_Lightroom, "hierarchicalSubject")
    subj_tag_prop = (consts.XMP_NS_DC, "subject")
    if not append:
      xmp.delete_property(*hier_tag_prop)
      xmp.delete_property(*subj_tag_prop)
    for tag in tags:
      write_tag(hier_tag_prop, tag)
      write_tag(subj_tag_prop, tag.split('|')[-1])

  if rating is not None:
    r_prop = (consts.XMP_NS_XMP, "Rating")
    xmp.set_property_int(*r_prop, rating)

  xmpfile.put_xmp(xmp)
  xmpfile.close_file()


def get_metadata2(fname:str) -> tuple[set[str],int]:
  not_image = fname.split('.')[-1].lower() in ['mp4', 'gif', 'mov']
  if not_image:
    raise NotImplementedError(f"{fname} is not an image")

  with Image.open(fname) as im:
    xmp = im.getxmp()
    if 'xmpmeta' not in xmp:
      return set(), 0

    desc = xmp['xmpmeta']['RDF']['Description']
    tags = []
    if (hier:='hierarchicalSubject') in desc.keys():
      tags = desc[hier]['Bag']['li']
    elif (fmt:='format') in desc.keys():
      logging.warning("no hierarchical tags in %s", fname)
      tags = desc[fmt]['Bag']['li']
    else:
      logging.warning("no tags in %s", fname)
      tags = []

    rating = -1
    if (rat:='Rating') in desc.keys():
      rating = int(desc[rat])
    else:
      rating = 0

    return set(tags), rating
