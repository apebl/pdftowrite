import os, tempfile, subprocess, shutil
import argparse, re, asyncio, operator, contextlib
from pathlib import Path
from typing import Any
import pdftowrite.utils as utils
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import shortuuid
from pdftowrite import __version__

PACKAGE_DIR = Path(os.path.dirname(__file__))
DATA_DIR = PACKAGE_DIR / 'data'
DOC_TEMPLATE = None
PAGE_TEMPLATE = None

class Page:
    SVG_NS = 'http://www.w3.org/2000/svg'
    XLINK_NS = 'http://www.w3.org/1999/xlink'

    ET.register_namespace('', SVG_NS)
    ET.register_namespace('xlink', XLINK_NS)

    def __init__(self, page_num, svg):
        self.page_num = page_num
        self.svg = re.sub(r'<\?xml[^(\?>)]*\?>', '', svg)
        tree = ET.ElementTree( ET.fromstring(self.svg) )
        self.__remove_metadata(tree)
        self.__uniquify(tree)
        self.svg = ET.tostring(tree.getroot(), encoding='unicode')

    def __remove_metadata(self, tree):
        root = tree.getroot()
        for el in root:
            _, _, tag = el.tag.partition('}')
            if tag == 'metadata':
                root.remove(el)
                break

    def __uniquify(self, tree):
        suffix = '-' + shortuuid.uuid()[:7] + '-p' + str(self.page_num)
        for el in tree.iter():
            if 'id' in el.attrib:
                el.attrib['id'] += suffix
            if ('{%s}href' % self.XLINK_NS) in el.attrib:
                el.attrib['{%s}href' % self.XLINK_NS] += suffix
            if 'clip-path' in el.attrib:
                attrib = el.get('clip-path')
                match = re.search(r'url\s*\(\s*(.+?)\s*\)', attrib)
                newid = match.group(1) + suffix
                el.set('clip-path', f'url({newid})')

    @property
    def width(self) -> float:
        return float(utils.pattern_get(r'width\s*=\s*"\s*([0-9.]+)', self.svg, 1))

    @width.setter
    def width(self, value: float):
        self.svg = re.sub(r'(width\s*=\s*"\s*)([0-9.]+)', rf'\g<1>{value}', self.svg)

    @property
    def height(self) -> float:
        return float(utils.pattern_get(r'height\s*=\s*"\s*([0-9.]+)', self.svg, 1))

    @height.setter
    def height(self, value: float):
        self.svg = re.sub(r'(height\s*=\s*"\s*)([0-9.]+)', rf'\g<1>{value}', self.svg)

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
    parser.add_argument('-m', '--mode', default='poppler', choices=['poppler', 'inkscape'],
                        help='Specify render mode (default: poppler)')
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
    opts = ['--pdf-poppler'] if ns.mode == 'poppler' else []
    utils.inkscape_run([
        *opts,
        f'--pdf-page={page_num}',
        f'--export-dpi={ns.dpi}',
        '--export-plain-svg',
        '-o', output,
        filename
    ])
    with open(output, 'r') as f:
        svg = f.read()
        return Page(page_num, svg)

async def convert_to_pages(filename: str, page_nums: list[int], ns: argparse.Namespace) -> list[Page]:
    result = []
    with tempfile.TemporaryDirectory() as tmpdir:
        loop = asyncio.get_running_loop()
        tasks = []
        for num in page_nums:
            task = loop.run_in_executor(None, process_page, filename, num, tmpdir, ns)
            tasks.append(task)
        for task in tasks:
            page = await task
            result.append(page)
    return sorted(result, key=operator.attrgetter('page_num'))

def generate_document(pages: list[Page], nodup_pages: set[int], vars: dict[str,str], ns: argparse.Namespace) -> None:
    page_tmp = get_page_template()
    page_results = []
    for page in pages:
        page.width = page.width * ns.scale
        page.height = page.height * ns.scale
        vars['width'] = page.width
        vars['height'] = page.height
        vars['ruleline-classes'] = '' if page.page_num in nodup_pages else 'write-no-dup'
        vars['body'] = page.svg
        text = utils.apply_vars(page_tmp, vars)
        page_results.append(text)
    doc_tmp = get_doc_template()
    body = '\n\n'.join(page_results)
    return utils.apply_vars(doc_tmp, { 'body': body })

def prettify(xml: str) -> str:
    dom = minidom.parseString(xml)
    text = dom.toprettyxml()
    text = '\n'.join([s for s in text.splitlines() if s.strip()])
    return text

def run(args):
    parser = arg_parser()
    ns = parser.parse_args(args)
    filename = ns.file[0]
    vars = {
        'x': ns.x,
        'y': ns.y,
        'width': 0,
        'height': 0,
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
    doc = prettify(doc)

    suffix = '.svg' if ns.nozip else '.svgz'
    output = ns.output if ns.output else str(Path(filename).with_suffix(suffix))
    tmp_output = output if ns.nozip else output + '.tmp'
    with open(tmp_output, 'w') as f:
        f.write(doc)
    if not ns.nozip:
        subprocess.check_call(['gzip', '-f', tmp_output])
        with contextlib.suppress(FileNotFoundError):
            os.remove(output)
        shutil.move(tmp_output + '.gz', output)
