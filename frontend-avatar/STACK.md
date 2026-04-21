# Stack Technique — Frontend Avatars

## Architecture

```
web/
├── templates/
│   ├── avatars.html          <- page principale (5 actes)
│   └── partials/
│       └── _card_avatar.html <- fragment Jinja2 reutilisable
├── static/
│   ├── avatars/              <- images PNG generees (20 fichiers)
│   ├── css/
│   │   └── avatars.css       <- styles cards + layouts + animations
│   └── js/
│       └── avatars.js        <- SSE listener + update cards
└── app.py                    <- route /avatars + SSE endpoint
```

## Phase 1 — Placeholder (0$, immédiat)

### Images placeholder via DiceBear API
Aucune image locale requise. URL directe dans le HTML :
```html
<img src="https://api.dicebear.com/9.x/adventurer/svg?seed=Mikhael&backgroundColor=111111"
     alt="Mikhael" width="200" height="200">
```

Alternatives :
- Multiavatar : `https://api.multiavatar.com/Mikhael.svg`
- Game-icons SVG : telecharger depuis https://game-icons.net/ et colorer en #ffb000

### Layout CSS (4 grilles, zéro framework)
```css
/* Acte I — Pyramide */
.acte-cour {
  display: grid;
  grid-template-areas:
    ".     arikh   ."
    "abba  .       imma"
    ".     zeir    ."
    ".     nukva   .";
  grid-template-columns: 1fr 1fr 1fr;
  gap: 2rem;
  justify-items: center;
  max-width: 900px;
  margin: 0 auto;
}

/* Acte II — Carré 2x2 */
.acte-gardiens {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  max-width: 600px;
  margin: 0 auto;
}

/* Acte III & V — Ligne horizontale */
.acte-officiers, .acte-veilleurs {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 2rem;
  max-width: 1000px;
  margin: 0 auto;
}

/* Acte IV — Triptyque (centre plus grand) */
.acte-ame {
  display: grid;
  grid-template-columns: 1fr 1.5fr 1fr;
  gap: 2rem;
  max-width: 800px;
  margin: 0 auto;
  align-items: center;
}
```

### Card HTML (template Jinja2)
```html
<!-- partials/_card_avatar.html -->
<div class="avatar-card" id="card-{{ personnage.id }}"
     data-etat="idle" data-composant="{{ personnage.composant }}">
  <div class="avatar-image">
    <img src="{{ personnage.image_url }}" alt="{{ personnage.nom }}">
  </div>
  <div class="avatar-role">{{ personnage.role }}</div>
  <div class="avatar-nom">{{ personnage.nom }}</div>
  <div class="avatar-hebreu">{{ personnage.nom_hebreu }}</div>
  <div class="avatar-description">{{ personnage.description }}</div>
  <a href="#" class="avatar-details" data-id="{{ personnage.id }}">
    Voir les details →
  </a>
</div>
```

### Card CSS
```css
.avatar-card {
  background: #111111;
  border: 1px solid #ffb00033;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;
  transition: border-color 0.3s, box-shadow 0.3s;
  font-family: 'IBM Plex Mono', monospace;
}

.avatar-card:hover {
  border-color: #ffb000;
  box-shadow: 0 0 15px #ffb00033;
}

.avatar-card[data-etat="active"] {
  border-color: #ffb000;
  animation: pulse-amber 2s ease-in-out infinite;
}

.avatar-card[data-etat="error"] {
  border-color: #ff3333;
  animation: pulse-red 1.5s ease-in-out infinite;
}

.avatar-card[data-etat="healing"] {
  border-color: #33ff33;
  animation: pulse-green 2s ease-in-out infinite;
}

.avatar-image {
  width: 150px;
  height: 150px;
  margin: 0 auto 1rem;
  border-radius: 50%;
  overflow: hidden;
  border: 2px solid #ffb00044;
}

.avatar-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-role {
  color: #ffb000;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.25rem;
}

.avatar-nom {
  color: #cccccc;
  font-size: 1.25rem;
  font-weight: bold;
  margin-bottom: 0.25rem;
}

.avatar-hebreu {
  color: #ffb00088;
  font-size: 1rem;
  margin-bottom: 0.75rem;
  direction: rtl;
}

.avatar-description {
  color: #888888;
  font-size: 0.8rem;
  line-height: 1.4;
  margin-bottom: 1rem;
}

.avatar-details {
  color: #ffb000;
  font-size: 0.75rem;
  text-decoration: none;
  border-bottom: 1px solid #ffb00033;
}

.avatar-details:hover {
  border-bottom-color: #ffb000;
}

/* Animations */
@keyframes pulse-amber {
  0%, 100% { box-shadow: 0 0 5px #ffb00022; }
  50% { box-shadow: 0 0 20px #ffb00044, 0 0 40px #ffb00022; }
}

@keyframes pulse-red {
  0%, 100% { box-shadow: 0 0 5px #ff333322; }
  50% { box-shadow: 0 0 20px #ff333344; }
}

@keyframes pulse-green {
  0%, 100% { box-shadow: 0 0 5px #33ff3322; }
  50% { box-shadow: 0 0 20px #33ff3344; }
}

/* Zivvug line (between Abba and Imma) */
.zivvug-line {
  position: absolute;
  height: 2px;
  background: linear-gradient(90deg, transparent, #ffcc00, transparent);
  animation: pulse-zivvug 3s ease-in-out infinite;
}

@keyframes pulse-zivvug {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}

/* Katnut/Gadlut (Zeir Anpin) */
.avatar-card[data-mochin="katnut"] {
  transform: scale(0.85);
  opacity: 0.7;
  filter: grayscale(30%);
}

.avatar-card[data-mochin="gadlut"] {
  transform: scale(1.05);
  box-shadow: 0 0 25px #ffcc0033;
}
```

### SSE Integration (JavaScript)
```javascript
// avatars.js
const eventSource = new EventSource('/api/avatars/stream');

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  const card = document.getElementById('card-' + data.id);
  if (!card) return;

  // Update state
  if (data.etat) card.dataset.etat = data.etat;
  if (data.mochin) card.dataset.mochin = data.mochin;

  // Update dynamic text if provided
  if (data.status_text) {
    const desc = card.querySelector('.avatar-description');
    if (desc) desc.textContent = data.status_text;
  }
};

eventSource.onerror = function() {
  console.warn('SSE connection lost, reconnecting...');
};
```

### Flask Route
```python
# In app.py
@app.route('/avatars')
def avatars_page():
    import json
    with open('frontend-avatar/personnages.json') as f:
        data = json.load(f)
    return render_template('avatars.html', actes=data['actes'])
```

## Phase 2 — Images generees (~$0.80)

### FLUX Kontext via Fal.ai
```bash
# Installation
pip install fal-client

# Generation (Python)
import fal_client

# 1. Generer le portrait de reference (style)
result = fal_client.submit("fal-ai/flux-pro/kontext", arguments={
    "prompt": "Noble archetype portrait bust, dark background #0a0a0a, "
              "warm amber gold rim lighting, serious dignified expression, "
              "style of Gustave Dore engraving meets Pixar 3D rendering, "
              "ancient wise king with long white beard, golden crown",
    "image_size": "square_hd",
    "num_images": 1
})
# Sauvegarder comme reference.png

# 2. Generer les 19 autres avec coherence
PERSONNAGES = [
    ("abba", "Creative father figure, hands glowing, bright eyes, short dark beard"),
    ("imma", "Wise mother, hands shaping light, serene, headwrap"),
    ("zeir_anpin", "Young man early twenties, six tools at belt, determined"),
    ("nukva", "Queen looking directly at camera, regal, open expression"),
    ("mikhael", "Guardian angel in light armor, shield, scanning eyes"),
    ("gabriel", "Stern angel enforcer, hand on sheathed blade, minimal expression"),
    ("raphael", "Gentle healer angel, glowing green-white hands, kind eyes"),
    ("uriel", "Contemplative angel with lantern, half-closed eyes, hood"),
    ("metatron", "Tall scribe chancellor, luminous quill and scroll, ageless"),
    ("memuneh", "Sharp-eyed steward with ring of keys, evaluating gaze"),
    ("samael", "Dark diagnostic figure with magnifying glass, clinical"),
    ("sofer", "Scribe at desk with quill and books, concentration, glasses"),
    ("nefesh_behamit", "Dark silhouette red edges, hunched, animal energy, no face"),
    ("beinoni", "Ordinary realistic human, no special attributes, facing camera"),
    ("nefesh_elokit", "Luminous silhouette white-gold edges, upright, no face"),
    ("daemon", "Night watchman with lantern and checklist, tired kind eyes"),
    ("meditant", "Figure in meditation eyes closed, thought bubbles rising"),
    ("kategor", "Austere record keeper, red folders, wire glasses, quill"),
]

for name, desc in PERSONNAGES:
    result = fal_client.submit("fal-ai/flux-pro/kontext", arguments={
        "prompt": f"Noble archetype portrait bust, dark background, "
                  f"warm amber gold rim lighting, serious dignified, "
                  f"same visual style as reference. {desc}",
        "image_url": "reference.png",  # style reference
        "image_size": "square_hd",
        "num_images": 1
    })
    # Sauvegarder comme web/static/avatars/{name}.png
```

### Stockage
```
web/static/avatars/
├── arikh_anpin.png
├── abba.png
├── imma.png
├── zeir_anpin.png
├── zeir_anpin_katnut.png   <- version reduite
├── nukva.png
├── mikhael.png
├── gabriel.png
├── raphael.png
├── uriel.png
├── metatron.png
├── memuneh.png
├── samael.png
├── sofer.png
├── nefesh_behamit.png
├── beinoni.png
├── nefesh_elokit.png
├── daemon.png
├── daemon_karpathy.png     <- version assise
├── meditant.png
└── kategor.png
```

## Phase 3 — HTMX (optionnel, zero JS custom)

### Remplacement du JS par HTMX
```html
<script src="https://unpkg.com/htmx.org@2.0.4"></script>
<script src="https://unpkg.com/htmx-ext-sse@2.2.2/sse.js"></script>

<div hx-ext="sse" sse-connect="/api/avatars/stream">
  {% for acte in actes %}
    <section class="acte acte-{{ acte.id }}">
      <h2>{{ acte.titre }}</h2>
      <p>{{ acte.description }}</p>
      <div class="acte-grid acte-{{ acte.id }}">
        {% for p in acte.personnages %}
          <div sse-swap="{{ p.id }}" hx-swap="innerHTML">
            {% include 'partials/_card_avatar.html' %}
          </div>
        {% endfor %}
      </div>
    </section>
  {% endfor %}
</div>
```

Le serveur envoie des events nommes par personnage :
```python
# Flask SSE
def format_sse(data, event=None):
    msg = f'data: {json.dumps(data)}\n\n'
    if event:
        msg = f'event: {event}\n{msg}'
    return msg

@app.route('/api/avatars/stream')
def avatar_stream():
    def generate():
        q = announcer.listen()
        while True:
            data = q.get()
            # data = {"id": "mikhael", "etat": "checking", ...}
            yield format_sse(data, event=data['id'])
    return Response(generate(), mimetype='text/event-stream')
```

## Ressources externes

### Code et patterns
- CSS Pyramidal Grid : https://css-tricks.com/making-a-responsive-pyramidal-grid-with-modern-css/
- CSS Glow Effects : https://freefrontend.com/css-glow-effects/
- Cyberpunk Dashboard : https://codepen.io/Avoloch/pen/EaabQxo
- Gradient Border Glow : https://codepen.io/thecoderashok/pen/zYbogyR
- vanilla-tilt.js : https://github.com/micku7zu/vanilla-tilt.js
- Flask SSE sans deps : https://maxhalford.github.io/blog/flask-sse-no-deps/
- Flask + HTMX SSE : https://mathspp.com/blog/streaming-data-from-flask-to-htmx-using-server-side-events
- jinja_partials : https://github.com/mikeckennedy/jinja_partials
- HTMX Flask examples : https://github.com/cscortes/htmxflask

### Images et avatars
- FLUX Kontext API : https://fal.ai/models/fal-ai/flux-pro/kontext ($0.04/image)
- DiceBear (placeholder) : https://api.dicebear.com/
- Multiavatar (placeholder) : https://api.multiavatar.com/
- Game-icons.net (SVG fantasy) : https://game-icons.net/
- RPG Awesome (font icons) : https://nagoshiashumari.github.io/Rpg-Awesome/
- Leonardo.ai (LoRA custom) : https://leonardo.ai/
- GPT Image 1.5 API : https://platform.openai.com/docs/guides/image-generation

### Animation (optionnel)
- vanilla-tilt.js : https://micku7zu.github.io/vanilla-tilt.js/ (hover 3D, 3KB)
- anime.js v4 : https://animejs.com/ (stagger, morph, 10KB)
- Atropos.js : https://atroposjs.com/ (parallax multi-couches)
