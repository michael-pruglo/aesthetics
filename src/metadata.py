import logging
from libxmp import XMPFiles, consts, XMPError

from ae_rater_types import ManualMetadata
import helpers as hlp


PROP_TAGS_HIERARCHICAL = (consts.XMP_NS_Lightroom, "hierarchicalSubject")
PROP_TAGS_BACKUP = (consts.XMP_NS_DC, "subject")
PROP_STARS = (consts.XMP_NS_XMP, "Rating")
PROP_AWARDS = (consts.XMP_NS_XMP, "Label")


def get_metadata(fullname:str, vocab:list[str]=None) -> ManualMetadata:
  xmpfile = XMPFiles(file_path=fullname)
  xmp = xmpfile.get_xmp()
  if xmp is None:
    return ManualMetadata()
  xmpfile.close_file()

  def get_tags():
    no_hierarchical = False
    propname = PROP_TAGS_HIERARCHICAL
    if not xmp.does_property_exist(*propname):
      propname = PROP_TAGS_BACKUP
      if not xmp.does_property_exist(*propname):
        logging.warning("No tags in metadata of %s", hlp.short_fname(fullname))
        return None
      no_hierarchical = True
      logging.warning("No hierarchical tags in %s", hlp.short_fname(fullname))
    n = xmp.count_array_items(*propname)
    if n==0:
      logging.warning("ZERO tags in %s", hlp.short_fname(fullname))
    ret = set()
    for i in range(n):
      tag = xmp.get_array_item(*propname, i+1)
      if no_hierarchical and vocab is not None:
        for voc_tag in vocab:
          if voc_tag.endswith(tag):
            tag = voc_tag
            break
      ret.add(tag)
    return ret or None

  def get_stars():
    propname = PROP_STARS
    if not xmp.does_property_exist(*propname):
      return 0

    return xmp.get_property_int(*propname)

  def get_awards():
    propname = PROP_AWARDS
    if not xmp.does_property_exist(*propname):
      return None

    awards = xmp.get_property(*propname)
    return set(awards.split())

  return ManualMetadata(
    tags=get_tags(),
    stars=get_stars(),
    awards=get_awards(),
  )


def has_metadata(fullname:str) -> bool:
  return get_metadata(fullname) != ManualMetadata()


def write_metadata(fullname:str, metadata:ManualMetadata, append:bool=True) -> None:
  xmpfile = XMPFiles(file_path=fullname, open_forupdate=True)
  xmp = xmpfile.get_xmp()
  if not xmp or not xmpfile.can_put_xmp(xmp):
    raise RuntimeError(f"file {fullname}: metadata not writable")

  def write_tag(property, tag):
    if not xmp.does_array_item_exist(*property, tag):
      xmp.append_array_item(*property, tag, {'prop_array_is_ordered': False, 'prop_value_is_array': True})
  if metadata.tags:
    hier_tag_prop = PROP_TAGS_HIERARCHICAL
    subj_tag_prop = PROP_TAGS_BACKUP
    try:
      xmp.register_namespace(hier_tag_prop[0], "pref1")
      xmp.register_namespace(subj_tag_prop[1], "pref2")
    except:
      logging.warning("problems registering namespace")
    if not append:
      try:
        xmp.delete_property(*hier_tag_prop)
        xmp.delete_property(*subj_tag_prop)
      except XMPError as e:
        logging.warning("Could not delete property: ^s", e)
    for tag in metadata.tags:
      write_tag(hier_tag_prop, tag)
      write_tag(subj_tag_prop, tag.split('|')[-1])

  if metadata.stars is not None:
    r_prop = PROP_STARS
    xmp.set_property_int(*r_prop, metadata.stars)

  if metadata.awards is not None:
    awa_prop = PROP_AWARDS
    xmp.set_property(*awa_prop, ' '.join(metadata.awards))

  xmpfile.put_xmp(xmp)
  xmpfile.close_file()
