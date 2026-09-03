window.MOTIFS = {
  bridge: function (api, W, H, L) {
    // Strichstärken bewusst kräftig: das Wasser ringsum wird mit 8-24 px
    // breiten Zügen gemalt, und eine Brücke aus 3-px-Strichen verschwindet
    // dazwischen, statt darüber zu liegen.
    var r = api.rand, p = L.pigments, a = L.accent;
    var hy = H * L.horizon, cx = W * r(0.46, 0.54);
    var span = W * r(0.58, 0.72), rise = H * r(0.075, 0.12);
    var left = cx - span / 2, deck = hy + H * r(0.05, 0.12);
    var wood = api.shade(p[1 % p.length], 0.62);
    var lightWood = api.shade(p[2 % p.length], 0.9);
    var green = api.shade(p[0], 0.64);
    var i, t, x, y, col;

    for (i = 0; i < 95; i++) {
      t = r(0, 1); x = left + span * t;
      y = deck - Math.sin(t * Math.PI) * rise + r(-3, 3);
      col = i % 4 ? wood : lightWood;
      api.stroke(x, y, r(11, 24), r(6, 13), r(-0.1, 0.1), col, r(0.6, 0.9));
    }
    for (i = 0; i < 30; i++) {
      t = i / 29; x = left + span * t + r(-2, 2);
      y = deck - Math.sin(t * Math.PI) * rise;
      api.stroke(x, y - H * 0.026, r(12, 22), r(5, 10), Math.PI / 2,
        i % 3 ? wood : lightWood, r(0.62, 0.88));
    }
    for (i = 0; i < 80; i++) {
      t = r(0, 1); x = left + span * t;
      y = deck - Math.sin(t * Math.PI) * rise - H * 0.052 + r(-2, 2);
      api.stroke(x, y, r(10, 20), r(5, 9), r(-0.12, 0.12), lightWood, r(0.55, 0.82));
    }
    for (i = 0; i < 115; i++) {
      x = cx + r(-span * 0.58, span * 0.58);
      var edge = Math.abs(x - cx) / (span * 0.58);
      y = hy - H * r(0.11, 0.34) + edge * H * 0.07;
      var drop = H * r(0.025, 0.16) * (1 - edge * 0.45);
      col = i % 5 < 2 ? api.shade(a[i % a.length], r(0.75, 1.05)) : green;
      api.stroke(x, y + drop / 2, drop, r(2.5, 7), Math.PI / 2 + r(-0.16, 0.16), col, r(0.3, 0.7));
    }
  },

  haystacks: function (api, W, H, L) {
    var r = api.rand, p = L.pigments, a = L.accent;
    var hy = H * L.horizon, count = Math.floor(r(2, 3.99));
    var shift = W * r(-0.07, 0.07), i, j;
    for (i = 0; i < count; i++) {
      var depth = count === 2 ? i / 2 : i / 3;
      var scale = 1 - depth * 0.28;
      var cx = W * (0.3 + i * (0.42 / Math.max(1, count - 1))) + shift;
      var base = hy + H * (0.22 + depth * 0.035);
      var half = W * 0.105 * scale, height = H * 0.26 * scale;
      var shadow = api.shade(p[(i + 1) % p.length], 0.48);
      for (j = 0; j < 38; j++) {
        var st = j / 37;
        api.stroke(cx + half * 0.4 + st * half * 1.55, base + st * H * 0.055,
          r(10, 24) * scale, r(3, 8) * scale, r(-0.16, 0.12), shadow, r(0.25, 0.55));
      }
      for (j = 0; j < 145; j++) {
        var yy = base - r(0, height), q = (base - yy) / height;
        var reach = half * (1 - q) + half * 0.08;
        var xx = cx + r(-reach, reach);
        var sunward = xx < cx ? 1.02 : 0.68;
        var baseCol = j % 6 < 2 ? a[j % a.length] : p[(j + i) % p.length];
        api.stroke(xx, yy, r(7, 17) * scale, r(3, 7) * scale,
          (xx < cx ? -1 : 1) * r(0.22, 0.8), api.shade(baseCol, sunward * r(0.82, 1.12)), r(0.48, 0.88));
      }
    }
  },

  poplars: function (api, W, H, L) {
    var r = api.rand, p = L.pigments, a = L.accent;
    var hy = H * L.horizon, n = Math.floor(r(8, 12)), side = r(0, 1) < 0.5 ? -1 : 1;
    var origin = side < 0 ? W * r(0.16, 0.25) : W * r(0.75, 0.84);
    var i, j;
    for (i = 0; i < n; i++) {
      var depth = i / (n - 1), scale = 1 - depth * 0.68;
      // Minus, nicht Plus: die Reihe steht am Rand und flieht INS Bild hinein.
      // Mit Plus lief sie vom Rand aus nach außen, und gut ein Viertel der
      // Bäume stand neben der Leinwand.
      var x = origin - side * W * 0.54 * (1 - Math.pow(1 - depth, 1.65));
      var base = hy + H * (0.18 * scale + 0.018);
      var height = H * 0.48 * scale, width = W * 0.038 * scale;
      var trunk = api.shade(p[(i + 2) % p.length], 0.48);
      for (j = 0; j < 15; j++) {
        api.stroke(x + r(-width * 0.15, width * 0.15), base - r(0, height * 0.78),
          r(8, 18) * scale, r(1.5, 4) * scale, Math.PI / 2 + r(-0.08, 0.08), trunk, r(0.35, 0.68));
      }
      for (j = 0; j < 72; j++) {
        var q = r(0, 1), yy = base - height * (0.2 + 0.8 * q);
        var bulge = Math.sin(q * Math.PI) * width + width * 0.25;
        var col = j % 7 === 0 ? a[j % a.length] : p[(j + i) % p.length];
        api.stroke(x + r(-bulge, bulge), yy, r(7, 18) * scale, r(3, 8) * scale,
          Math.PI / 2 + r(-0.35, 0.35), api.shade(col, r(0.58, 1.05)), r(0.32 + depth * 0.12, 0.78));
      }
    }
  },

  sailboats: function (api, W, H, L) {
    var r = api.rand, p = L.pigments, a = L.accent;
    var hy = H * L.horizon, n = Math.floor(r(2, 4.99)), offset = W * r(-0.06, 0.06);
    var i, j;
    for (i = 0; i < n; i++) {
      var depth = i / Math.max(1, n - 1), scale = 1 - depth * 0.48;
      var x = W * (0.2 + i * (0.6 / Math.max(1, n - 1))) + offset + r(-W * 0.035, W * 0.035);
      var water = hy + H * r(0.09, 0.2), mast = H * r(0.19, 0.31) * scale;
      var sailW = W * r(0.05, 0.09) * scale, pale = api.shade(p[(i + 2) % p.length], r(1.04, 1.22));
      for (j = 0; j < 42; j++) {
        var q = r(0.06, 0.96), yy = water - mast * q;
        var reach = sailW * (1 - q);
        api.stroke(x + reach * r(0.1, 0.95), yy, r(7, 16) * scale, r(2.5, 6) * scale,
          r(-0.18, 0.18), j % 6 === 0 ? api.shade(a[j % a.length], 0.85) : pale, r(0.42, 0.8));
      }
      for (j = 0; j < 14; j++) api.stroke(x + r(-2, 2), water - r(0, mast), r(7, 14), r(1.2, 2.8), Math.PI / 2, api.shade(p[0], 0.46), r(0.48, 0.75));
      for (j = 0; j < 18; j++) api.stroke(x + r(-sailW * 0.22, sailW), water + r(-2, 3), r(8, 19) * scale, r(2, 5), r(-0.08, 0.08), api.shade(p[(i + 1) % p.length], 0.48), r(0.5, 0.82));
      for (j = 0; j < 38; j++) {
        var ry = water + r(5, mast * 0.72), fade = 1 - (ry - water) / (mast * 0.8);
        api.stroke(x + r(-sailW * fade * 0.5, sailW * fade), ry, r(6, 16), r(2, 6), Math.PI / 2 + r(-0.18, 0.18), j % 4 ? pale : a[j % a.length], r(0.1, 0.32));
      }
    }
  },

  willow: function (api, W, H, L) {
    var r = api.rand, p = L.pigments, a = L.accent;
    var hy = H * L.horizon, crownX = W * r(0.35, 0.65), top = Math.max(H * 0.03, hy - H * 0.34);
    var spread = W * r(0.48, 0.65), i;
    for (i = 0; i < 245; i++) {
      var x = crownX + r(-spread / 2, spread / 2), edge = Math.abs(x - crownX) / (spread / 2);
      var start = top + H * r(0, 0.16) + edge * H * 0.1;
      var length = H * r(0.08, 0.36) * (1 - edge * 0.4);
      var col = i % 10 === 0 ? a[i % a.length] : p[i % p.length];
      api.stroke(x, start + length / 2, length, r(2.5, 8), Math.PI / 2 + r(-0.16, 0.16), api.shade(col, r(0.48, 0.92)), r(0.25, 0.7));
    }
    for (i = 0; i < 75; i++) {
      var tx = crownX + r(-spread * 0.18, spread * 0.18), ty = hy + H * r(0.02, 0.22);
      api.stroke(tx, ty, r(8, 24), r(3, 8), Math.PI / 2 + r(-0.25, 0.25), api.shade(p[(i + 1) % p.length], 0.38), r(0.2, 0.55));
    }
  },

  poppies: function (api, W, H, L) {
    var r = api.rand, p = L.pigments, a = L.accent;
    var hy = H * L.horizon, slope = H * r(-0.06, 0.06), i, j;
    for (i = 0; i < 72; i++) {
      var x = W * r(0.04, 0.96), base = hy + slope * (x / W - 0.5);
      var h = H * r(0.035, 0.12), col = api.shade(p[i % p.length], r(0.48, 0.82));
      api.stroke(x, base - h / 2, h, r(2, 6), Math.PI / 2 + r(-0.25, 0.25), col, r(0.35, 0.72));
      for (j = 0; j < 2; j++) api.stroke(x + r(-7, 7), base - h + r(-5, 5), r(5, 12), r(3, 7), r(-0.3, 0.3), col, r(0.35, 0.7));
    }
    for (i = 0; i < 155; i++) {
      var depth = Math.pow(r(0, 1), 1.45), py = hy + H * (0.025 + depth * 0.39);
      var px = W * r(0.05, 0.95) + slope * depth;
      var size = 2.5 + depth * 7;
      var red = api.shade(a[i % a.length], r(0.72, 1.15));
      api.stroke(px, py, r(3, 8) + size, r(2.5, 6) + size * 0.35, r(-0.4, 0.4), red, r(0.55, 0.92));
    }
  },

  cathedral: function (api, W, H, L) {
    var r = api.rand, p = L.pigments, a = L.accent;
    var hy = H * L.horizon, cx = W * r(0.47, 0.53), width = W * r(0.48, 0.6);
    var ground = hy + H * 0.31, left = cx - width / 2, right = cx + width / 2;
    var topL = hy - H * r(0.28, 0.39), topR = hy - H * r(0.18, 0.29), i, j;
    for (i = 0; i < 255; i++) {
      var x = r(left, right), sideTop = x < cx ? topL : topR;
      var y = r(sideTop, ground), edge = Math.min(x - left, right - x) / (width / 2);
      var col = i % 9 < 2 ? a[i % a.length] : p[i % p.length];
      api.stroke(x, y, r(8, 20), r(3, 9), Math.PI / 2 + r(-0.12, 0.12), api.shade(col, r(0.7 + edge * 0.08, 1.1)), r(0.34, 0.76));
    }
    for (i = 0; i < 9; i++) {
      var ribX = left + width * (i + 0.5) / 9;
      for (j = 0; j < 22; j++) api.stroke(ribX + r(-3, 3), ground - j * H * 0.018, r(7, 15), r(2, 5), Math.PI / 2, api.shade(p[(i + 1) % p.length], i % 2 ? 0.58 : 1.05), r(0.42, 0.72));
    }
    for (i = 0; i < 3; i++) {
      var pcx = cx + (i - 1) * width * 0.22, pw = width * (i === 1 ? 0.13 : 0.1), ph = H * (i === 1 ? 0.17 : 0.13);
      for (j = 0; j < 52; j++) {
        var q = r(0, 1), ang = Math.PI * q;
        var px = pcx + Math.cos(ang) * pw, py = ground - Math.sin(ang) * ph * 0.75 - r(0, ph * 0.4);
        api.stroke(px, py, r(7, 14), r(3, 7), Math.PI / 2 + r(-0.14, 0.14), api.shade(p[(j + 2) % p.length], 0.38), r(0.45, 0.78));
      }
    }
  },

  cliff: function (api, W, H, L) {
    var r = api.rand, p = L.pigments, a = L.accent;
    var hy = H * L.horizon, side = r(0, 1) < 0.5 ? -1 : 1;
    var coast = side < 0 ? W * r(0.54, 0.63) : W * r(0.37, 0.46);
    var edge = side < 0 ? 0 : W, base = hy + H * 0.28, i;
    for (i = 0; i < 270; i++) {
      var q = r(0, 1), x = coast + (edge - coast) * q;
      var top = hy - H * (0.08 + 0.3 * Math.pow(q, 0.7));
      var y = r(top, base), col = i % 8 === 0 ? a[i % a.length] : p[i % p.length];
      api.stroke(x, y, r(9, 23), r(4, 10), r(-0.28, 0.28), api.shade(col, r(0.42, 0.82)), r(0.42, 0.82));
    }
    var archX = coast + (edge - coast) * 0.29, archW = W * 0.11, archH = H * 0.19;
    for (i = 0; i < 105; i++) {
      var aq = r(-1, 1), ax = archX + aq * archW;
      var archTop = base - archH * Math.sqrt(Math.max(0, 1 - aq * aq));
      api.stroke(ax, r(archTop, base + 3), r(7, 17), r(3, 8), Math.PI / 2 + r(-0.16, 0.16), api.shade(p[(i + 1) % p.length], 0.3), r(0.5, 0.85));
    }
    var needleX = coast - side * W * r(0.08, 0.13), needleH = H * r(0.22, 0.32);
    for (i = 0; i < 95; i++) {
      var nq = r(0, 1), ny = base - needleH * nq, nw = W * 0.035 * (1 - nq) + 2;
      api.stroke(needleX + r(-nw, nw), ny, r(7, 18), r(3, 8), Math.PI / 2 + r(-0.2, 0.2), api.shade(i % 6 ? p[i % p.length] : a[i % a.length], r(0.38, 0.72)), r(0.42, 0.8));
    }
  }
};
