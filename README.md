# HTMLDiffWriter

An experimental `HTMLWriter` for matplotlib animations that stores only the first frame as well as the frame 
deltas/diffs of consecutive frames. Frames are therefore computed on the fly which should enable huge memory savings 
but might be slow. 

This was originally intended for use only with animations that use the SVG frame format, but because diffing is done 
on the base64-encoded frames, this also applies to other formats (although the filesize might not reduce as much).

A short example and minimalistic test is provided as a proof of concept. Even so, a savings of 8x is shown. 

See [this matplotlib issue](https://github.com/matplotlib/matplotlib/issues/19694) for more.
