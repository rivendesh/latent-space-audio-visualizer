import pathlib

import streamlit as st

st.set_page_config(page_title="p5.js in Streamlit (external)", layout="centered")
st.title("p5.js in Streamlit")

st.markdown(
    "Proof of concept: embedding a [p5.js](https://p5js.org/) sketch via "
    "`st.components.v1.html`, with the sketch loaded from an external `.js` file."
)

sketch_path = pathlib.Path(__file__).parent / "sketch.js"
sketch_js = sketch_path.read_text()

P5_HTML = f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.11.3/p5.min.js"></script>
</head>
<body>
<script>
{sketch_js}
</script>
</body>
</html>
"""

st.components.v1.html(P5_HTML, height=420)
