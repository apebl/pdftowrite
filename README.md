# pdftowrite: Annotate PDFs with Stylus Labs Write

![](pdftowrite.png)

A utility that converts PDF to [Stylus Labs Write](http://www.styluslabs.com/)
document, and vice versa.

## Annotate PDFs

There are two ways to annotate PDFs.

### A. Convert PDF -> SVG -> PDF (literally)

1. `pdftowrite example.pdf`: Convert *.pdf to *.svgz
2. (Open `example.svgz` with Stylus Labs Write and write your notes)
3. `writetopdf example.svgz -o example-annot.pdf`: Convert *.svgz to *.pdf

`pdftowrite` converts PDF pages to SVG paths with invisible but selectable text
layers, so you can preserve text as selectable characters.

You should use `writetopdf` instead of Write's PDF exporter which does not
support some features (e.g. Unicode text, multi-coords tspans, etc.).

The result PDF (excluding annotations) is, however, not 100% the same as the
original PDF. This is because:

- PDF and SVG are not 100% compatible
- Write does not support entire SVG spec, so some modifications are required for compatibility with Write
- Original text elements are deleted. Instead, a text layer is added to the page as mentioned earlier

### B. Annotation mode

1. `pdftowrite example.pdf`: Convert *.pdf to *.svgz
2. (Open `example.svgz` with Stylus Labs Write and write your notes)
3. `writetopdf --annot example.svgz -o example-annot.pdf`: New PDF = Original PDF + Annotations

You can see that `--annot` option is added in *3*. If the option is added,
`writetopdf` creates a new PDF by overlaying annotations on top of the original
PDF pages. This is similar to Xournal's method.

You can annotate different PDF file with `--pdf-file FILE` option. e.g.:

```
writetopdf --annot --pdf-file example2.pdf example.svgz -o example2-annot.pdf
```

## Install

```
pip install --user pdftowrite
```

### Requirements

`pdftowrite`:

 * Poppler (`pdfinfo`)
 * Inkscape (either native or flatpak)
 * ImageMagick (`convert`)
 * gzip
 * lxml (libxml2, libxslt)

`writetopdf`:

 * wkhtmltopdf
 * PDFtk(pdftk-java)
 * librsvg (`rsvg-convert`)
 * gzip

You need to manually install the packages. e.g.:

- Debian/Ubuntu: `sudo apt install poppler-utils inkscape imagemagick gzip libxml2-dev libxslt-dev wkhtmltopdf pdftk librsvg2-bin`
- Fedora: `sudo dnf install poppler inkscape ImageMagick gzip libxml2-devel libxslt-devel wkhtmltopdf pdftk librsvg2-tools`
- Arch: `sudo pacman -S poppler inkscape imagemagick gzip libxslt wkhtmltopdf pdftk librsvg`

## Usage

### pdftowrite

```
usage: pdftowrite [-h] [-v] [-o OUTPUT] [-f] [-m {mixed,poppler,inkscape}]
                  [-C] [-d DPI] [-g PAGES] [-u NODUP_PAGES] [-Z] [-s SCALE]
                  [-x X] [-y Y] [-X XRULING] [-Y YRULING] [-l MARGIN_LEFT]
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
  -f, --force           Overwrite existing files without asking
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
usage: writetopdf [-h] [-v] [--annot] [--pdf-file PDF_FILE] [-o OUTPUT] [-f]
                  [-g PAGES] [-s SCALE]
                  FILE

Convert Stylus Labs Write document to PDF

positional arguments:
  FILE                  A Write document

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  --annot               Use annotation mode
  --pdf-file PDF_FILE   Specify the PDF file to be annotated
  -o OUTPUT, --output OUTPUT
                        Specify output filename
  -f, --force           Overwrite existing files without asking
  -g PAGES, --pages PAGES
                        Specify pages to convert (e.g. "1 2 3", "1-3")
                        (default: all)
  -s SCALE, --scale SCALE
                        Scale page size (default: 1.0)
```
