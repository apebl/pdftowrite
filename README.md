# pdftowrite: PDF <-> Write with text

![](pdftowrite.png)

A utility that converts PDF to [Stylus Labs Write](http://www.styluslabs.com/)
document with text, and vice versa.

## How does it work

`pdftowrite` converts PDF pages to SVG paths, adds an invisible but selectable
text layer to each page, and merges them into a Write document.

`writetopdf` converts a Write document to a PDF.

### Why do I need `writetopdf`? Write itself can export PDF

The PDF exporter of Write does not support some features (e.g. Unicode text,
multi-coords tspans, etc.), but `writetopdf` does.

### If I convert PDF -> Write -> PDF, Is the latter PDF is 100% the same as the former?

No, the program does not guarantee it. `pdftowrite` converts PDF pages to SVG
paths, so original text elements are deleted. Instead, a text layer is added to
the page as mentioned earlier.

## Install

```
pip install --user pdftowrite
```

### Requirements

`pdftowrite`:

 * Poppler
 * Inkscape (either native or flatpak)
 * ImageMagick
 * gzip

`writetopdf`:

 * wkhtmltopdf
 * PDFtk(pdftk-java) or Poppler
 * gzip

You need to manually install the packages. e.g.:

- Debian/Ubuntu: `sudo apt install poppler-utils inkscape imagemagick gzip wkhtmltopdf pdftk`
- Fedora: `sudo dnf install poppler inkscape ImageMagick gzip wkhtmltopdf pdftk`
- Arch: `sudo pacman -S poppler inkscape imagemagick gzip wkhtmltopdf pdftk`

## Example

```
pdftowrite example.pdf
```

```
writetopdf example.svgz
```

## Usage

### pdftowrite

```
usage: pdftowrite [-h] [-v] [-o OUTPUT] [-m {mixed,poppler,inkscape}] [-C]
                  [-d DPI] [-g PAGES] [-u NODUP_PAGES] [-Z] [-s SCALE] [-x X]
                  [-y Y] [-X XRULING] [-Y YRULING] [-l MARGIN_LEFT]
                  [-p PAPERCOLOR] [-r RULECOLOR]
                  FILE

Convert PDF to Stylus Labs Write document

positional arguments:
  FILE                  A pdf file

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -o OUTPUT, --output OUTPUT
                        Specify output filename
  -m {mixed,poppler,inkscape}, --mode {mixed,poppler,inkscape}
                        Specify render mode (default: mixed)
  -C, --no-compat-mode  Turn off Write compatibility mode
  -d DPI, --dpi DPI     Specify resolution for bitmaps and rasterized filters
                        (default: 96)
  -g PAGES, --pages PAGES
                        Specify pages to convert (e.g. "1 2 3", "1-3")
                        (default: all)
  -u NODUP_PAGES, --nodup-pages NODUP_PAGES
                        Specify no-dup pages (e.g. "1 2 3", "1-3") (default:
                        all)
  -Z, --nozip           Do not compress output
  -s SCALE, --scale SCALE
                        Scale page size (default: 1.0)
  -x X                  Specify the x coordinate of the viewport of <svg>
                        (default: 10.0)
  -y Y                  Specify the y coordinate of the viewport of <svg>
                        (default: 10.0)
  -X XRULING, --xruling XRULING
                        Specify x rulling (default: 0.0)
  -Y YRULING, --yruling YRULING
                        Specify y rulling (default: 40.0)
  -l MARGIN_LEFT, --margin-left MARGIN_LEFT
                        Specify margin left (default: 100.0)
  -p PAPERCOLOR, --papercolor PAPERCOLOR
                        Specify paper color (default: #FFFFFF)
  -r RULECOLOR, --rulecolor RULECOLOR
                        Specify rule color (default: #9F0000FF)
```

### writetopdf

```
usage: writetopdf [-h] [-v] [-o OUTPUT] [-g PAGES] [-s SCALE] FILE

Convert Stylus Labs Write document to PDF

positional arguments:
  FILE                  A Write document

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -o OUTPUT, --output OUTPUT
                        Specify output filename
  -g PAGES, --pages PAGES
                        Specify pages to convert (e.g. "1 2 3", "1-3")
                        (default: all)
  -s SCALE, --scale SCALE
                        Scale page size (default: 1.0)
```
