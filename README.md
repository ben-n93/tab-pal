# tab-pal

`tab-pal` is a TUI that makes it easier to add and edit custom colour palettes in Tableau.

## Installation

You can install via `pip` although I suggest using [`pipx`](https://pipx.pypa.io/stable/) so you can use it regardless of which virtual environmental you have (or don't have) activated:

```
pipx install tab-pal
```

## Configuration

`tab-pal` will automatically search for your `Preferences.tsp` file on launch however if it can't be found you'll be prompted for the file path.

Alternatively, and what is recommended, is to create an enviromental variable called `TAB_PAL_FILE`, which `tab-pal` will search for on launch. This will ensure you don't need to keep supplying the file path every time you launch `tab-pal`.

## Usage

Add, edit and delete palettes to your heart's content!

You might need to restart Tableau if you're using `tab-pal` concurrently to add/edit palettes in order to see the changes applied in Tableau.

Note that if you're using Terminal on Macbook some palette colour previews might not render correctly, as Terminal is limited to 256 colors. Instead, use [iTerm2](https://iterm2.com/) or [kitty](https://sw.kovidgoyal.net/kitty/).


