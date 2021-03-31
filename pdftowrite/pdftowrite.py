import os, tempfile, subprocess, shutil, sys
import argparse, asyncio, operator, contextlib
from pathlib import Path
from enum import Enum
import pdftowrite.utils as utils
from pdftowrite.docs import Page
from pdftowrite import __version__

PACKAGE_DIR = Path(os.path.dirname(__file__))
DATA_DIR = PACKAGE_DIR / 'data'
DOC_TEMPLATE = None
PAGE_TEMPLATE = None

class Mode(Enum):
    MIXED = 'mixed'
    POPPLER = 'poppler'
    INKSCAPE = 'inkscape'

    def __str__(self):
        return self.value

def get_doc_template() -> str:
    global DOC_TEMPLATE
    if not DOC_TEMPLATE:
        path = DATA_DIR / 'document.svg'
        with open(path, 'r') as f:
            DOC_TEMPLATE = f.read()
    return DOC_TEMPLATE

def get_page_template() -> str:
    global PAGE_TEMPLATE
    if not PAGE_TEMPLATE:
        path = DATA_DIR / 'page.svg'
        with open(path, 'r') as f:
            PAGE_TEMPLATE = f.read()
    return PAGE_TEMPLATE

def arg_parser():
    parser = argparse.ArgumentParser(description='Convert PDF to Stylus Labs Write document')
    parser.add_argument('file', metavar='FILE', type=str, nargs=1,
                        help='A pdf file')
    parser.add_argument('-v', '--version', action='version', version=__version__)
    parser.add_argument('-o', '--output', action='store', type=str, default='',
                        help='Specify output filename')
    parser.add_argument('-m', '--mode', type=Mode, default=Mode.MIXED, choices=list(Mode),
                        help='Specify render mode (default: mixed)')
    parser.add_argument('-C', '--no-compat-mode', action='store_true',
                        help='Turn off Write compatibility mode')
    parser.add_argument('-d', '--dpi', type=int, default=96,
                        help='Specify resolution for bitmaps and rasterized filters (default: 96)')
    parser.add_argument('-g', '--pages', action='store', type=str, default='all',
                        help='Specify pages to convert (e.g. "1 2 3", "1-3") (default: all)')
    parser.add_argument('-u', '--nodup-pages', action='store', type=str, default='all',
                        help='Specify no-dup pages (e.g. "1 2 3", "1-3") (default: all)')
    parser.add_argument('-Z', '--nozip', action='store_true',
                        help='Do not compress output')
    parser.add_argument('-s', '--scale', action='store', type=float, default=1.0,
                        help='Scale page size (default: 1.0)')
    parser.add_argument('-x', action='store', type=float, default=10.0,
                        help='Specify the x coordinate of the viewport of <svg> (default: 10.0)')
    parser.add_argument('-y', action='store', type=float, default=10.0,
                        help='Specify the y coordinate of the viewport of <svg> (default: 10.0)')
    parser.add_argument('-X', '--xruling', action='store', type=float, default=0.0,
                        help='Specify x rulling (default: 0.0)')
    parser.add_argument('-Y', '--yruling', action='store', type=float, default=40.0,
                        help='Specify y rulling (default: 40.0)')
    parser.add_argument('-l', '--margin-left', action='store', type=float, default=100.0,
                        help='Specify margin left (default: 100.0)')
    parser.add_argument('-p', '--papercolor', action='store', type=str, default='#FFFFFF',
                        help='Specify paper color (default: #FFFFFF)')
    parser.add_argument('-r', '--rulecolor', action='store', type=str, default='#9F0000FF',
                        help='Specify rule color (default: #9F0000FF)')
    return parser

def process_page(filename: str, page_num: int, output_dir: str, ns: argparse.Namespace) -> Page:
    output = str(Path(output_dir) / f'output-{page_num}.svg')
    opts = ['--pdf-poppler'] if ns.mode is Mode.POPPLER or ns.mode is Mode.MIXED else []
    utils.inkscape_run([
        *opts,
        f'--pdf-page={page_num}',
        f'--export-dpi={ns.dpi}',
        '--export-plain-svg',
        '-o', output,
        filename
    ])

    text_layer_svg = None
    if ns.mode is Mode.MIXED:
        text_layer_output = str(Path(output_dir) / f'output-{page_num}-text.svg')
        utils.inkscape_run([
            f'--pdf-page={page_num}',
            f'--export-dpi={ns.dpi}',
            '--export-plain-svg',
            '-o', text_layer_output,
            filename
        ])
        with open(text_layer_output, 'r') as f:
            text_layer_svg = f.read()

    with open(output, 'r') as f:
        svg = f.read()
        return Page(page_num, svg, text_layer_svg, not ns.no_compat_mode)

async def convert_to_pages(filename: str, page_nums: list[int], ns: argparse.Namespace) -> list[Page]:
    result = []
    with tempfile.TemporaryDirectory() as tmpdir:
        loop = asyncio.get_running_loop()
        tasks = []
        for num in page_nums:
            task = loop.run_in_executor(None, process_page, filename, num, tmpdir, ns)
            tasks.append(task)
        result = await asyncio.gather(*tasks)
    return sorted(result, key=operator.attrgetter('page_num'))

def generate_document(pages: list[Page], nodup_pages: set[int], vars: dict[str,str], ns: argparse.Namespace) -> None:
    page_tmp = get_page_template()
    page_results = []
    for page in pages:
        page.width = page.width * ns.scale
        page.height = page.height * ns.scale
        vars['width'] = page.width_full
        vars['height'] = page.height_full
        vars['ruleline-classes'] = '' if page.page_num in nodup_pages else 'write-no-dup'
        vars['body'] = page.svg
        text = utils.apply_vars(page_tmp, vars)
        page_results.append(text)
    doc_tmp = get_doc_template()
    body = '\n\n'.join(page_results)
    return utils.apply_vars(doc_tmp, { 'body': body })

def run(args):
    parser = arg_parser()
    ns = parser.parse_args(args)
    filename = ns.file[0]
    vars = {
        'x': ns.x,
        'y': ns.y,
        'width': '0',
        'height': '0',
        'xruling': ns.xruling,
        'yruling': ns.yruling,
        'margin-left': ns.margin_left,
        'papercolor': ns.papercolor,
        'rulecolor': ns.rulecolor,
        'ruleline-classes': '',
        'body': ''
    }

    if not Path(filename).exists():
        raise FileNotFoundError('File not found: {}'.format(filename))

    num_pages = utils.number_of_pages(filename)
    page_nums = sorted( utils.parse_range(ns.pages, num_pages) )
    nodup_page_nums = utils.parse_range(ns.nodup_pages, num_pages)

    loop = asyncio.get_event_loop()
    pages = loop.run_until_complete( convert_to_pages(filename, page_nums, ns) )
    loop.close()

    doc = generate_document(pages, nodup_page_nums, vars, ns)

    suffix = '.svg' if ns.nozip else '.svgz'
    output = ns.output if ns.output else str(Path(filename).with_suffix(suffix))
    tmp_output = output if ns.nozip else output + '.tmp'
    if Path(tmp_output).exists():
        if not utils.query_yn(f'Overwrite?: {tmp_output}'): return
    with open(tmp_output, 'w') as f:
        f.write(doc)
    if not ns.nozip:
        if Path(tmp_output + '.gz').exists():
            if not utils.query_yn(f'Overwrite?: {tmp_output}.gz'): return
        subprocess.check_call(['gzip', '-f', tmp_output])
        if Path(output).exists():
            if not utils.query_yn(f'Overwrite?: {output}'): return
        with contextlib.suppress(FileNotFoundError):
            os.remove(output)
        shutil.move(tmp_output + '.gz', output)

def main():
    run(sys.argv[1:])
