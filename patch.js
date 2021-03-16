// XMLDiff provides a nice interface that could be used specifically for SVGs
// function get_svg_node(path) {
//   return document.evaluate(path, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
// }


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


/**
 * A base64 object is sometimes wrapped such that each line
 * is `length` (defaults to 76). This does not apply to the
 * prefix (i.e: "data:image/png;base64,") so you need to
 * specify this offset (length of prefix) if it has already
 * been added.
 * @param {string} doc
 * @param {number} offset
 * @param {number} length
 * @returns {string}
 */
function rewrap_base64(doc, offset = 26, length=76) {
  // Note: 0xa is used instead of newlines to facilitate code injection
  let chunks = [];
  doc = doc.replaceAll(String.fromCharCode(0xa), '');
  for (let i = 0; i < doc.length; i += length) {
    chunks.push(doc.slice(offset).substring(i, i + length));
  }
  return doc.slice(0, offset) + chunks.join(String.fromCharCode(0xa));
}
