import pathlib

import streamlit as st

st.set_page_config(page_title="Advanced p5.js Sketch", layout="wide")
st.title("Advanced p5.js Particle System")

st.markdown(
    "A more complex p5.js sketch embedded in Streamlit. "
    "Features a particle system with flow fields, neighbor connections, "
    "and interactive attractors / repellers."
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
new p5(sketch);
</script>
</body>
</html>
"""

st.components.v1.html(P5_HTML, height=620, width=820)
