import uuid
from functools import partial
from multiprocessing import Pool
from difflib import SequenceMatcher
from matplotlib.animation import HTMLWriter, _log

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
  function Animation(diff_frames, checkpoint_frames, img_id, slider_id, interval, loop_select_id){
    this.img_id = img_id;
    this.slider_id = slider_id;
    this.loop_select_id = loop_select_id;
    this.interval = interval;
    this.current_frame = 0;
    this.direction = 0;
    this.timer = null;
    this.num_frames = diff_frames.length + 1;
    this.diff_frames = diff_frames;
    this.checkpoint_frames = checkpoint_frames;

    var slider = document.getElementById(this.slider_id);
    slider.max = this.num_frames - 1;
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
    let base = undefined, start = undefined;
    if (this.checkpoint_frames.hasOwnProperty(frame)) {
      // Check if requested frame is checkpointed
      base = this.checkpoint_frames[frame];
    } else {
      // Apply diffs in order to reach target frame
      // we could cache computer frames, of have "reverse"
      // diff, or a tree structure, but for now simply recompute.
      if (this.current_frame < frame) {
        start = Math.max(0, this.current_frame);
        base = document.getElementById(this.img_id).src;
      } else {
        start = 0;
        base = this.checkpoint_frames[0];
      }
      for (let i = start; i < frame; i++) {
        base = applyPatch(base, this.diff_frames[i]);
      }
    }

    this.current_frame = frame;
    document.getElementById(this.img_id).src = base;
    document.getElementById(this.slider_id).value = this.current_frame;
  }
  Animation.prototype.next_frame = function()
  {
    this.set_frame(Math.min(this.num_frames - 1, this.current_frame + 1));
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
    this.set_frame(this.num_frames - 1);
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
    if(this.current_frame < this.num_frames){
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

  /**
  * Apply the diff patch to the input string
  * @param {string} base
  * @param {Array<Array<>>} patch
  */
  function applyPatch(base, patch) {
    let target = base.split('');
    for (let [low, high, data] of patch) {
      // Infer operation type based on indices and data
      // If data is the emtpy string then it's a delete op
      // If both indices are equal it's an insert op
      // Otherwise assume replace op as patch is well formed
      if (!data) {
        // Delete Op
        for (let i = low; i < high; i++)
          target[i] = '';
      } else if (low === high) {
        // Insert Op
        if (low >= target.length)
          target.push(data);
        else
          target[low] = data + target[low];
      } else {
        // Replace Op
        for (let i = low; i < high; i++)
          target[i] = '';
        target[low] = data;
      }
    }
    return target.join('');
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
  <img id="_anim_img{id}">
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
    var img_id = "_anim_img{id}";
    var slider_id = "_anim_slider{id}";
    var loop_select_id = "_anim_loop_select{id}";

    var diff_frames = new Array({Ndiffs});
    {diff_frames}
    var checkpoint_frames = new Object();
    {fill_frames}
    /* set a timeout to make sure all the above elements are created before
       the object is initialized. */
    setTimeout(function() {{
        anim{id} = new Animation(diff_frames, checkpoint_frames, img_id, slider_id, {interval},
                                 loop_select_id);
    }}, 0);    
  }})()
</script>
"""


def _add_base64_prefix(frame_list, frame_format):
    """frame_list should be a list of base64-encoded files"""
    if frame_format == 'svg':
        # Fix MIME type for svg
        frame_format = 'svg+xml'
    template = "data:image/{0};base64,{1}"
    return [template.format(frame_format, frame_data) for frame_data in frame_list]


def _embedded_checkpoint_frames(prefixed_frame_dict):
    """prefixed_frame_dict should be a dict of base64-encoded files, with prefix"""
    template = '    checkpoint_frames[{0}] = "{1}"\n'
    return "\n" + "".join(template.format(i, frame_data.replace('\n', '\\\n'))
                          for i, frame_data in prefixed_frame_dict.items())


def _diff_frames(frame1, frame2):
    """diff two base64-encoded frames"""
    # Ignore line-wraps as per RFC 4648
    s = SequenceMatcher(None, frame1.replace('\n', ''), frame2.replace('\n', ''))
    diff = [[i1, i2, frame2[j1:j2]] for tag, i1, i2, j1, j2 in s.get_opcodes() if tag != 'equal']
    return diff


def _embedded_diff_frames(frames, parallel=False):
    frame_pairs = []
    prev_frame = frames[0]
    for next_frame in frames[1:]:
        frame_pairs.append((prev_frame, next_frame))
        prev_frame = next_frame

    if parallel:
        with Pool() as p:
            diffs = p.starmap(_diff_frames, frame_pairs)
    else:
        diffs = [_diff_frames(*fp) for fp in frame_pairs]

    template = '    diff_frames[{0}] = {1}\n'
    return "\n" + "".join(
        template.format(i, frame_data)
        for i, frame_data in enumerate(diffs))


class HTMLDiffWriter(HTMLWriter):
    def __init__(self, *args, parallel=True, **kwargs):
        self.parallel = parallel
        super().__init__(*args, **kwargs)

    def finish(self):
        # save the frames to an html file
        if self.embed_frames:
            # Ignore line-wraps as per RFC 4648
            prefixed_frames = [frame.replace('\n', '') for frame in self._saved_frames]
            prefixed_frames = _add_base64_prefix(prefixed_frames, self.frame_format)
            fill_frames = _embedded_checkpoint_frames({0: prefixed_frames[0]})
            diff_frames = _embedded_diff_frames(prefixed_frames, parallel=self.parallel)
            Ndiffs = len(self._saved_frames) - 1
        else:
            raise NotImplementedError('Only embedded frames are supported at the moment')

        mode_dict = dict(once_checked='',
                         loop_checked='',
                         reflect_checked='')
        mode_dict[self.default_mode + '_checked'] = 'checked'

        interval = 1000 // self.fps

        with open(self.outfile, 'w') as of:
            of.write(JS_INCLUDE + STYLE_INCLUDE)
            of.write(DISPLAY_TEMPLATE.format(id=uuid.uuid4().hex,
                                             Ndiffs=Ndiffs,
                                             fill_frames=fill_frames,
                                             diff_frames=diff_frames,
                                             interval=interval,
                                             **mode_dict))

        # duplicate the temporary file clean up logic from
        # FileMovieWriter.cleanup.  We can not call the inherited
        # versions of finished or cleanup because both assume that
        # there is a subprocess that we either need to call to merge
        # many frames together or that there is a subprocess call that
        # we need to clean up.
        if self._tmpdir:
            _log.debug('MovieWriter: clearing temporary path=%s', self._tmpdir)
            self._tmpdir.cleanup()
        else:
            if self._clear_temp:
                _log.debug('MovieWriter: clearing temporary paths=%s',
                           self._temp_paths)
                for path in self._temp_paths:
                    path.unlink()
