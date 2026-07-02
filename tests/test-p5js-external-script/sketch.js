let t = 0;

function setup() {
  createCanvas(400, 400);
}

function draw() {
  background(20, 20, 30);

  let cx = width / 2;
  let cy = height / 2;
  let maxR = 150;

  for (let i = 0; i < 8; i++) {
    let phase = (i * TWO_PI) / 8;
    let r = maxR * (0.5 + 0.5 * sin(t * 0.02 + i));
    let x = cx + r * cos(t * 0.03 + phase);
    let y = cy + r * sin(t * 0.03 + phase);
    let hue = (i * 45 + t * 0.5) % 360;

    fill(hue, 80, 70);
    noStroke();
    let sz = 20 + 15 * sin(t * 0.05 + i);
    circle(x, y, sz);
  }

  fill(255, 120);
  noStroke();
  textAlign(CENTER, CENTER);
  textSize(16);
  text("p5.js inside Streamlit!", cx, cy);

  t++;
}
