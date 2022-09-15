import logging
from libxmp import XMPFiles, consts
from PIL import Image

from helpers import short_fname


def get_metadata(fname:str) -> tuple[list, int]:
  xmpfile = XMPFiles(file_path=fname)
  xmp = xmpfile.get_xmp()
  if xmp is None:
    raise RuntimeError(f"file {fname} has no xmp")
  xmpfile.close_file()

  def get_tags():
    propname = (consts.XMP_NS_Lightroom, "hierarchicalSubject")
    if not xmp.does_property_exist(*propname):
      logging.warning("no hierarchical tags in %s", short_fname(fname))
      propname = (consts.XMP_NS_DC, "subject")
      if not xmp.does_property_exist(*propname):
        logging.error("No tags in metadata of %s", short_fname(fname))
        return []
    n = xmp.count_array_items(*propname)
    if n==0:
      logging.warning("ZERO tags in %s", short_fname(fname))
    return [xmp.get_array_item(*propname, i+1) for i in range(n)]

  def get_rating():
    propname = (consts.XMP_NS_XMP, "Rating")
    if not xmp.does_property_exist(*propname):
      return 0

    return xmp.get_property_int(*propname)

  return get_tags(), get_rating()

def write_metadata(fname:str, tags:list=None, rating:int=None) -> None:
  xmpfile = XMPFiles(file_path=fname, open_forupdate=True)
  xmp = xmpfile.get_xmp()
  if not xmpfile.can_put_xmp(xmp):
    raise RuntimeError(f"file {fname}: metadata not writable")

  if tags is not None:
    for tag in tags:
      hier_prop = (consts.XMP_NS_Lightroom, "hierarchicalSubject", tag)
      if xmp.does_array_item_exist(*hier_prop):
        logging.warning("%s: hier already exists '%s'", short_fname(fname), tag)
      else:
        xmp.append_array_item(*hier_prop, {'prop_array_is_ordered': False, 'prop_value_is_array': True})
      subj_prop = (consts.XMP_NS_DC, "subject", tag.split('|')[-1])
      if xmp.does_array_item_exist(*subj_prop):
        logging.warning("%s: subj already exists '%s'", short_fname(fname), tag.split('|')[-1])
      else:
        xmp.append_array_item(*subj_prop, {'prop_array_is_ordered': False, 'prop_value_is_array': True})

  if rating is not None:
    r_prop = (consts.XMP_NS_XMP, "Rating")
    xmp.set_property_int(*r_prop, rating)

  xmpfile.put_xmp(xmp)
  xmpfile.close_file()




def get_metadata2(fname):
  not_image = fname.split('.')[-1].lower() in ['mp4', 'gif', 'mov']
  if not_image:
    return [], -1

  try:
    with Image.open(fname) as im:
      xmp = im.getxmp()
      desc = xmp['xmpmeta']['RDF']['Description']

      tags = []
      if (hier:='hierarchicalSubject') in desc.keys():
        tags = desc[hier]['Bag']['li']
      elif (fmt:='format') in desc.keys():
        logging.warning("no hierarchical tags in %s", fname)
        tags = desc[fmt]['Bag']['li']
      else:
        raise RuntimeError(f'No XMP tags in {fname}')

      rating = -1
      if (rat:='Rating') in desc.keys():
        rating = int(desc[rat])
      else:
        rating = 0

      return tags, rating
  except Exception as error:
    logging.error("could not open %s: %s", fname, error)
    return [], -2

