# miles2walk.com — Portfolio Site

Fantasy illustration & worldbuilding portfolio for Miles Walker.
Dark, atmospheric single-page site built in pure HTML/CSS/JS — no frameworks, no build step.

## Setup

```
miles-portfolio/
├── index.html        ← the whole site
├── images/           ← put your art files here
│   ├── foundry-drake.jpg
│   ├── kaiju-picnic.jpg
│   └── ...
└── README.md
```

## Adding Your Art

1. Drop image files into the `images/` folder (JPG, PNG, or WebP all work)
2. Open `index.html` and find the `<!-- gallery -->` section
3. Replace each `<div class="art-placeholder">` block with an `<img>` tag:

```html
<!-- Before -->
<div class="art-placeholder">
  <div class="art-icon">🐉</div>
  <div class="art-title">Foundry Drake</div>
  <div class="art-note">replace with image</div>
</div>

<!-- After -->
<img src="images/foundry-drake.jpg" alt="Foundry Drake" />
```

4. Update the `gallery-title` and `gallery-type` text in the overlay below each item

## Customizing

| What | Where in index.html |
|---|---|
| Email address | Two places: `mailto:` href + visible text in `#contact` |
| Social links | `<a href="#">` tags in `.contact-links` |
| About text | `<p>` blocks in `.about-content` |
| Your photo | Replace the `<!-- <img src="..."> -->` comment in `.portrait-frame` |
| Footer year | Bottom of `<footer>` |
| Gallery layout | `.gi-1` through `.gi-9` classes control grid spans |

## Deploying to GitHub Pages

1. Create a new GitHub repo (e.g. `miles2walk`)
2. Push this folder's contents to the `main` branch
3. Go to **Settings → Pages → Source → Deploy from branch → main / root**
4. Your site will be live at `https://yourusername.github.io/miles2walk`

To use a custom domain (miles2walk.com):
1. Add a file named `CNAME` containing just: `miles2walk.com`
2. In your domain registrar, point DNS to GitHub Pages (see [GitHub docs](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site))

## Features

- Custom animated cursor (hides on mobile)
- Scroll-triggered fade-in reveals
- Bento-style gallery grid with hover overlays
- Fully responsive (mobile nav collapses)
- No JS frameworks, no build tools, no dependencies (fonts load from Google Fonts)
- Fast — one HTML file + your images
