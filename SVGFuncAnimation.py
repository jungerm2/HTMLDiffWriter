import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET
from io import StringIO

from matplotlib.artist import Artist
from matplotlib.text import Text


# Javascript template for HTMLWriter
JS_INCLUDE = """
<link rel="stylesheet"
href="https://maxcdn.bootstrapcdn.com/font-awesome/4.4.0/css/font-awesome.min.css">
<script language="javascript">
  function isInternetExplorer() {
    ua = navigator.userAgent;
    /* MSIE used to detect old browsers and Trident used to newer ones*/
    return ua.indexOf("MSIE ") > -1 || ua.indexOf("Trident/") > -1;
  }

  /* Define the Animation class */
  function Animation(frames, doc_id, slider_id, interval, loop_select_id){
    this.doc_id = doc_id;
    this.slider_id = slider_id;
    this.loop_select_id = loop_select_id;
    this.interval = interval;
    this.current_frame = 0;
    this.direction = 0;
    this.timer = null;
    this.frames = frames;

    var slider = document.getElementById(this.slider_id);
    slider.max = this.frames.length - 1;
    if (isInternetExplorer()) {
        // switch from oninput to onchange because IE <= 11 does not conform
        // with W3C specification. It ignores oninput and onchange behaves
        // like oninput. In contrast, Microsoft Edge behaves correctly.
        slider.setAttribute('onchange', slider.getAttribute('oninput'));
        slider.setAttribute('oninput', null);
    }
    this.set_frame(this.current_frame);
  }

  Animation.prototype.get_loop_state = function(){
    var button_group = document[this.loop_select_id].state;
    for (var i = 0; i < button_group.length; i++) {
        var button = button_group[i];
        if (button.checked) {
            return button.value;
        }
    }
    return undefined;
  }

  Animation.prototype.set_frame = function(frame){
    this.current_frame = frame;
    for (var id of Object.keys(this.frames[frame])) {
        document.getElementById(id).outerHTML = this.frames[frame][id];
    }
    document.getElementById(this.slider_id).value = this.current_frame;
  }

  Animation.prototype.next_frame = function()
  {
    this.set_frame(Math.min(this.frames.length - 1, this.current_frame + 1));
  }

  Animation.prototype.previous_frame = function()
  {
    this.set_frame(Math.max(0, this.current_frame - 1));
  }

  Animation.prototype.first_frame = function()
  {
    this.set_frame(0);
  }

  Animation.prototype.last_frame = function()
  {
    this.set_frame(this.frames.length - 1);
  }

  Animation.prototype.slower = function()
  {
    this.interval /= 0.7;
    if(this.direction > 0){this.play_animation();}
    else if(this.direction < 0){this.reverse_animation();}
  }

  Animation.prototype.faster = function()
  {
    this.interval *= 0.7;
    if(this.direction > 0){this.play_animation();}
    else if(this.direction < 0){this.reverse_animation();}
  }

  Animation.prototype.anim_step_forward = function()
  {
    this.current_frame += 1;
    if(this.current_frame < this.frames.length){
      this.set_frame(this.current_frame);
    }else{
      var loop_state = this.get_loop_state();
      if(loop_state == "loop"){
        this.first_frame();
      }else if(loop_state == "reflect"){
        this.last_frame();
        this.reverse_animation();
      }else{
        this.pause_animation();
        this.last_frame();
      }
    }
  }

  Animation.prototype.anim_step_reverse = function()
  {
    this.current_frame -= 1;
    if(this.current_frame >= 0){
      this.set_frame(this.current_frame);
    }else{
      var loop_state = this.get_loop_state();
      if(loop_state == "loop"){
        this.last_frame();
      }else if(loop_state == "reflect"){
        this.first_frame();
        this.play_animation();
      }else{
        this.pause_animation();
        this.first_frame();
      }
    }
  }

  Animation.prototype.pause_animation = function()
  {
    this.direction = 0;
    if (this.timer){
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  Animation.prototype.play_animation = function()
  {
    this.pause_animation();
    this.direction = 1;
    var t = this;
    if (!this.timer) this.timer = setInterval(function() {
        t.anim_step_forward();
    }, this.interval);
  }

  Animation.prototype.reverse_animation = function()
  {
    this.pause_animation();
    this.direction = -1;
    var t = this;
    if (!this.timer) this.timer = setInterval(function() {
        t.anim_step_reverse();
    }, this.interval);
  }
</script>
"""


# Style definitions for the HTML template
STYLE_INCLUDE = """
<style>
.animation {
    display: inline-block;
    text-align: center;
}
input[type=range].anim-slider {
    width: 374px;
    margin-left: auto;
    margin-right: auto;
}
.anim-buttons {
    margin: 8px 0px;
}
.anim-buttons button {
    padding: 0;
    width: 36px;
}
.anim-state label {
    margin-right: 8px;
}
.anim-state input {
    margin: 0;
    vertical-align: middle;
}
</style>
"""


# HTML template for HTMLWriter
DISPLAY_TEMPLATE = """
<div class="animation">
  <div id="_anim_doc{id}">{base_document}</div>
  <div class="anim-controls">
    <input id="_anim_slider{id}" type="range" class="anim-slider"
           name="points" min="0" max="1" step="1" value="0"
           oninput="anim{id}.set_frame(parseInt(this.value));"></input>
    <div class="anim-buttons">
      <button title="Decrease speed" aria-label="Decrease speed" onclick="anim{id}.slower()">
          <i class="fa fa-minus"></i></button>
      <button title="First frame" aria-label="First frame" onclick="anim{id}.first_frame()">
        <i class="fa fa-fast-backward"></i></button>
      <button title="Previous frame" aria-label="Previous frame" onclick="anim{id}.previous_frame()">
          <i class="fa fa-step-backward"></i></button>
      <button title="Play backwards" aria-label="Play backwards" onclick="anim{id}.reverse_animation()">
          <i class="fa fa-play fa-flip-horizontal"></i></button>
      <button title="Pause" aria-label="Pause" onclick="anim{id}.pause_animation()">
          <i class="fa fa-pause"></i></button>
      <button title="Play" aria-label="Play" onclick="anim{id}.play_animation()">
          <i class="fa fa-play"></i></button>
      <button title="Next frame" aria-label="Next frame" onclick="anim{id}.next_frame()">
          <i class="fa fa-step-forward"></i></button>
      <button title="Last frame" aria-label="Last frame" onclick="anim{id}.last_frame()">
          <i class="fa fa-fast-forward"></i></button>
      <button title="Increase speed" aria-label="Increase speed" onclick="anim{id}.faster()">
          <i class="fa fa-plus"></i></button>
    </div>
    <form title="Repetition mode" aria-label="Repetition mode" action="#n" name="_anim_loop_select{id}"
          class="anim-state">
      <input type="radio" name="state" value="once" id="_anim_radio1_{id}"
             {once_checked}>
      <label for="_anim_radio1_{id}">Once</label>
      <input type="radio" name="state" value="loop" id="_anim_radio2_{id}"
             {loop_checked}>
      <label for="_anim_radio2_{id}">Loop</label>
      <input type="radio" name="state" value="reflect" id="_anim_radio3_{id}"
             {reflect_checked}>
      <label for="_anim_radio3_{id}">Reflect</label>
    </form>
  </div>
</div>


<script language="javascript">
  /* Instantiate the Animation class. */
  /* The IDs given should match those used in the template above. */
  (function() {{
    var doc_id = "_anim_doc{id}";
    var slider_id = "_anim_slider{id}";
    var loop_select_id = "_anim_loop_select{id}";
    var frames = {fill_frames};

    /* set a timeout to make sure all the above elements are created before
       the object is initialized. */
    setTimeout(function() {{
        anim{id} = new Animation(frames, doc_id, slider_id, {interval},
                                 loop_select_id);
    }}, 0);
  }})()
</script>
"""


def get_all_children(artist):
    if isinstance(artist, Artist):
        for child in artist.get_children():
            yield from get_all_children(child)
        yield artist


class SVGFuncAnimation:
    NAMESPACES = {
        'svg': 'http://www.w3.org/2000/svg',
        'xlink': 'http://www.w3.org/1999/xlink'
    }

    def __init__(self, fig, func, frames, init_func=None, fargs=None, default_mode='loop', interval=200):
        self._fig = fig
        self._func = func
        self._iter_gen = frames  # TODO: Deal with integers, and generators (with itertools.tee?)
        self._init_func = init_func
        self._args = fargs if fargs else ()
        self._default_mode = default_mode
        self._interval = interval
        self._html_representation = ''
        self._base_document = None
        self._embed_frames = []

    @staticmethod
    def _tree_tostring(tree):
        ET.register_namespace('', 'http://www.w3.org/2000/svg')
        ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
        return ET.tostring(tree, encoding='unicode')

    @staticmethod
    def _recursive_remove(root, xpath, ns):
        for child in root.findall(xpath, ns):
            root.remove(child)

        for child in list(root):
            SVGFuncAnimation._recursive_remove(child, xpath, ns)

    def _gather_defs(self):
        # SVG definitions (i.e: <defs>) are generated on the fly by each artist if they
        # haven't yet been created. Therefore we need to gather them and place them
        # in the base document such that every frame has access to them.
        # Note: This step could be improved. Currently it depends on python's builtin
        # XML library which cannot handle XML chunks so we need to hack together a
        # valid doc for it to parse, then remove the excess (see below).

        # Find the first <defs> in the base document and add all defs to it
        base_document_tree = ET.fromstring(self._base_document)
        defs = []

        # Gather all defs from the base document that isn't the main defs
        for ds in base_document_tree.findall('.//*/svg:defs', self.NAMESPACES):
            defs.append(ds)

        # Purge all defs from main document
        for child in list(base_document_tree):
            self._recursive_remove(child, 'svg:defs', self.NAMESPACES)

        # Now filter through the embedded frames and remove any defs in those
        filtered_frames = []
        start, end = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">', '</svg>'

        for embedded_frame in self._embed_frames:
            drawn_artists = {}
            for gid, doc in embedded_frame.items():
                # Make the doc a valid XML file, otherwise we can't parse it
                doc = start + doc + end
                doc = ET.fromstring(doc)
                for ds in doc.findall('.//*/svg:defs', self.NAMESPACES):
                    defs.append(ds)
                self._recursive_remove(doc, 'svg:defs', self.NAMESPACES)
                # We can't simply do _tree_tostring on the doc's (only) child, because
                # the XML package will add namespace info to that child... It's annoying
                drawn_artists[gid] = self._tree_tostring(doc).replace(start, '', 1).replace(end, '', 1)
            filtered_frames.append(drawn_artists)
        self._embed_frames = filtered_frames

        # Add all defs to main_def, regenerate the base doc
        main_defs = ET.SubElement(base_document_tree, 'defs')
        for d in defs:
            for child in list(d):
                main_defs.append(child)

        self._base_document = self._tree_tostring(base_document_tree)

    def grab_frames(self):
        # Clear previous data
        self._base_document = None
        self._embed_frames = []

        with StringIO() as f:
            # Init figure by adding all artists returned by init_func
            # TODO: Check that these are actually artists
            if self._init_func:
                for artist in self._init_func():
                    self._fig.add_artist(artist)
                    # artist.set_visible(True)

            # Set the gid of every artist to it's hash, the idea here is that
            # when an artist is drawn in SVG it will be encased in a group with
            # an id equal to the artist's gid and the hash of an artist doesn't
            # change when the artist's data changes.
            for artist in get_all_children(self._fig):
                # artist.set_gid(str(hash(artist)))
                artist.set_gid(uuid.uuid4().hex)

            # Now we can save the initial figure, this creates a cached
            # SVG rendered, and will produce our base SVG document
            self._fig.savefig(f, format='svg')
            f.seek(0)
            self._base_document = f.read()

            # Read this document and parse out all SVG groups.
            # This will help us detect if an artist that we haven't
            # encountered before gets drawn. These artists are problematic
            # because the SVG group associated with them won't be in the
            # base document so we won't be able to update it properly.
            tree = ET.fromstring(self._base_document)
            known_groups = {g.get('id') for g in tree.findall('.//*/svg:g', namespaces=self.NAMESPACES)}

            # Get all subsequent frames by only drawing
            # the artists returned by the user's func
            for framedata in self._iter_gen:
                drawn_artists = {}
                for artist in self._func(framedata, *self._args):
                    # artist_gid = str(hash(artist))
                    artist_gid = artist.get_gid()

                    # Check that this artist is known
                    if artist_gid not in known_groups:
                        raise ValueError(f'Artist {artist}, with gid={artist.get_gid()}, not recognized.')

                    # Note that there's some real "blitting" potential here,
                    # We could figure out if the artist data changed at all
                    # and not redraw if it didn't, for now let's redraw all.
                    start_pos = f.tell()
                    self._fig.draw_artist(artist)
                    f.seek(start_pos)
                    drawn_artist = f.read()
                    drawn_artists[artist_gid] = drawn_artist
                self._embed_frames.append(drawn_artists)
        self._gather_defs()

    def save(self, filename):
        if not self._base_document:
            self.grab_frames()

        mode_dict = dict(once_checked='', loop_checked='', reflect_checked='')
        mode_dict[self._default_mode + '_checked'] = 'checked'

        with open(filename, 'w', encoding='utf-8') as of:
            of.write(JS_INCLUDE + STYLE_INCLUDE)
            of.write(DISPLAY_TEMPLATE.format(id=uuid.uuid4().hex,
                                             Nframes=len(self._embed_frames),
                                             fill_frames=self._embed_frames,
                                             base_document=self._base_document,
                                             interval=self._interval,
                                             **mode_dict))

    def to_jshtml(self):
        if not self._html_representation:
            with TemporaryDirectory() as tmpdir:
                path = Path(tmpdir, "temp.html")
                self.save(str(path))
                self._html_representation = path.read_text()
        return self._html_representation

    def _repr_html_(self):
        """IPython display hook for rendering."""
        return self.to_jshtml()
