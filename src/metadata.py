import logging
from dataclasses import dataclass, field
from libxmp import XMPFiles, consts, XMPError

from tags_vocab import VOCAB, SPECIAL_AWARDS


@dataclass
class ManualMetadata:
  tags : set[str] = field(default_factory=set)
  stars : int = 0
  awards : set[str] = field(default_factory=set)

  @classmethod
  def from_str(cls, tagsstr:str, stars:int, awardsstr:str):
    return cls(set(tagsstr.split()), stars, set(awardsstr.split()))

  def get_errors(self) -> list[str]:
    err = []
    if self.stars < 0:
      err.append(f"negative stars: {self.stars}")
    if not self.tags:
      err.append("empty tags")
    if (bad_tags := [t for t in self.tags if t not in VOCAB]):
      err.append(f"tags not in vocab: {bad_tags}")
    if (orphan_tags := [t for t in self.tags if '|' in t and t.rsplit('|',maxsplit=1)[0] not in self.tags]):
      err.append(f"orphan tags: {orphan_tags}")
    if (bad_awards := [a for a in self.awards
                       if a.startswith("e_") and a[2:] not in VOCAB
                       or a.startswith("wow_") and a[4:] not in VOCAB
                       or a.isdigit()]):
      err.append(f"bad exemplary awards: {bad_awards}")
    return err

  def get_warnings(self) -> list[str]:
    warn = []
    if (unk_awards := [a for a in self.awards
                       if not a.startswith(("e_", "wow_")) and a not in SPECIAL_AWARDS]):
      warn.append(f"unknown awards: {unk_awards}")
    return warn


def get_metadata(fullname:str) -> ManualMetadata:
  with MetadataIO(fullname, 'r') as mio:
    return mio.read()

def has_metadata(fullname:str) -> bool:
  meta = get_metadata(fullname)
  return meta and meta.tags

def can_write_metadata(fullname:str) -> bool:
  with MetadataIO(fullname, 'w') as mio:
    return mio.can_write()

def write_metadata(fullname:str, metadata:ManualMetadata) -> None:
  with MetadataIO(fullname, 'w') as mio:
    assert mio.can_write()
    mio.write(metadata)



class MetadataIO:
  PROP_TAGS_HIERARCHICAL = (consts.XMP_NS_Lightroom, "hierarchicalSubject")
  PROP_TAGS_BACKUP = (consts.XMP_NS_DC, "subject")
  PROP_STARS = (consts.XMP_NS_XMP, "Rating")
  PROP_AWARDS = (consts.XMP_NS_XMP, "Label")

  def __init__(self, fullname:str, mode:str) -> None:
    self.fullname = fullname
    self.mode = mode
    self.xmpfile = None
    self.xmp = None

  def __enter__(self):
    self.xmpfile = XMPFiles(file_path=self.fullname, open_forupdate='w' in self.mode)
    self.xmp = self.xmpfile.get_xmp()
    return self

  def __exit__(self, exc_type, exc_value, exc_traceback):
    self.xmpfile.close_file()

  def read(self) -> ManualMetadata:
    if self.xmp is None:
      return None
    return ManualMetadata.from_str(self._read_tags(), self._read_stars(), self._read_awards())

  def _read_tags(self) -> str:
    tag_prop = self.PROP_TAGS_HIERARCHICAL
    if not self.xmp.does_property_exist(*tag_prop):
      logging.warning("No hierarchical tags in %s", self.fullname)
      tag_prop = self.PROP_TAGS_BACKUP
      if not self.xmp.does_property_exist(*tag_prop):
        logging.error("No tags in metadata of %s", self.fullname)
        return ""
    n = self.xmp.count_array_items(*tag_prop)
    if n==0:
      logging.warning("ZERO tags in %s", self.fullname)
    return ' '.join([self._read_one_tag(i, tag_prop) for i in range(n)])

  def _read_one_tag(self, i, propname):
    tag = self.xmp.get_array_item(*propname, i+1)
    if propname==self.PROP_TAGS_BACKUP:
      return next(voc_tag for voc_tag in VOCAB if voc_tag.endswith(tag))
    return tag

  def _read_stars(self) -> int:
    if not self.xmp.does_property_exist(*self.PROP_STARS):
      return 0
    return self.xmp.get_property_int(*self.PROP_STARS)

  def _read_awards(self) -> str:
    if not self.xmp.does_property_exist(*self.PROP_AWARDS):
      return ""
    return self.xmp.get_property(*self.PROP_AWARDS)

  def can_write(self) -> bool:
    return bool(self.xmp) and self.xmpfile.can_put_xmp(self.xmp)

  def write(self, meta) -> None:
    tag_prop = self.PROP_TAGS_HIERARCHICAL
    if self._register_namespace(tag_prop[0]) is None:
      tag_prop = self.PROP_TAGS_BACKUP
      if self._register_namespace(tag_prop[0]) is None:
        raise RuntimeError(f"file {self.fullname}: couldn't register neither primary nor backup namespaces")
    self.xmp.delete_property(*self.PROP_TAGS_HIERARCHICAL)
    self.xmp.delete_property(*self.PROP_TAGS_BACKUP)
    for tag in meta.tags:
      if tag_prop == self.PROP_TAGS_BACKUP:
        tag = tag.split('|')[-1]
      if not self.xmp.does_array_item_exist(*tag_prop, tag):
        self.xmp.append_array_item(*tag_prop, tag, {'prop_array_is_ordered': False, 'prop_value_is_array': True})

    self.xmp.set_property_int(*self.PROP_STARS, meta.stars)
    self.xmp.set_property(*self.PROP_AWARDS, ' '.join(meta.awards))

    self.xmpfile.put_xmp(self.xmp)

  def _register_namespace(self, namespace:str) -> str:
    try:
      return self.xmp.get_prefix_for_namespace(namespace)
    except XMPError as not_registered_yet_ex:
      try:
        return self.xmp.register_namespace(namespace, "sugg_pref")
      except XMPError as registration_ex:
        logging.warning("couldn't register namespace '%s': exeption '%s'", namespace, registration_ex)
        return None
