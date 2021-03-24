import os, tempfile, subprocess, shutil
import argparse, re, asyncio, operator, contextlib, copy
from pathlib import Path
from typing import Any
from enum import Enum
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

    def __init__(self, page_num, svg, text_layer_svg):
        self.page_num = page_num
        self.suffix = '-' + shortuuid.uuid()[:7] + '-p' + str(self.page_num)
        self.__process_svg(svg, text_layer_svg)

    def __process_svg(self, svg, text_layer_svg) -> str:
        svg = re.sub(r'<\?xml[^(\?>)]*\?>', '', svg)
        self.tree = ET.ElementTree( ET.fromstring(svg) )
        self.__remove_metadata()
        self.__uniquify()
        if text_layer_svg:
            self.text_layer = self.__create_text_layer(text_layer_svg)
            self.tree.getroot().append(self.text_layer)
        else:
            self.text_layer = None

    def __remove_metadata(self):
        root = self.tree.getroot()
        for el in root:
            _, _, tag = el.tag.partition('}')
            if tag == 'metadata':
                root.remove(el)
                break

    def __uniquify(self):
        for el in self.tree.iter():
            self.__uniquify_element(el, self.suffix)

    def __uniquify_element(self, el: ET.Element, suffix: str):
        if 'id' in el.attrib:
            el.attrib['id'] += suffix
        if ('{%s}href' % self.XLINK_NS) in el.attrib:
            el.attrib['{%s}href' % self.XLINK_NS] += suffix
        if 'clip-path' in el.attrib:
            attrib = el.get('clip-path')
            match = re.search(r'url\s*\(\s*(.+?)\s*\)', attrib)
            newid = match.group(1) + suffix
            el.set('clip-path', f'url({newid})')

    def __create_text_layer(self, text_layer_svg) -> ET.Element:
        tree = ET.ElementTree( ET.fromstring(text_layer_svg) )
        text_layer_vb = tree.getroot().get('viewBox')
        text_layer_vb_width = self.__viewbox_get(text_layer_vb, 3)
        text_layer_vb_height = self.__viewbox_get(text_layer_vb, 4)
        group = self.__create_text_group(tree)

        el = ET.Element('svg')
        el.set('id', 'text-layer' + self.suffix)
        el.set('width', self.viewbox_width)
        el.set('height', self.viewbox_height)
        el.set('viewBox', f'0 0 {text_layer_vb_width} {text_layer_vb_height}')
        el.append(group)
        return el

    def __create_text_group(self, tree) -> ET.Element:
        group = ET.Element('g')
        g = tree.getroot().find('./{%s}g[last()]' % self.SVG_NS)
        if 'transform' in g.attrib:
            group.set('transform', g.get('transform'))

        text_els = self.__get_text_elements(tree)
        for text_el in text_els:
            style = text_el.get('style', '')
            style = self.__style_attr(style, 'fill-opacity', '0')
            style = self.__style_attr(style, 'stroke', 'none')
            text_el.set('style', style)
            group.append(text_el)
        return group

    def __get_text_elements(self, tree) -> list[ET.Element]:
        result = []
        texts = tree.getroot().findall('.//{%s}text' % self.SVG_NS)
        for text in texts:
            for el in text.iter():
                el.attrib.pop('id', None)
                el.attrib.pop('clip-path', None)
            tspans = text.findall('.//{%s}tspan' % self.SVG_NS)
            for tspan in tspans:
                new_tspans = self.__split_tspan(tspan)
                for new_tspan in new_tspans:
                    text.append(new_tspan)
            result.append(text)
        return result

    def __split_tspan(self, tspan: ET.Element) -> list[ET.Element]:
        pattern = r'([0-9.]+\s*[a-zA-Z%]*)'
        x_list = re.findall(pattern, tspan.get('x', ''))
        if len(x_list) > 1:
            result = []
            text = tspan.text
            tspan.set('x', x_list[0].strip())
            tspan.text = text[0]
            for i in range(1, len(x_list)):
                new_tspan = copy.deepcopy(tspan)
                new_tspan.set('x', x_list[i].strip())
                new_tspan.text = text[i]
                result.append(new_tspan)
            return result
        y_list = re.findall(pattern, tspan.get('y', ''))
        if len(y_list) > 1:
            result = []
            text = tspan.text
            tspan.set('y', y_list[0].strip())
            tspan.text = text[0]
            for i in range(1, len(y_list)):
                new_tspan = copy.deepcopy(tspan)
                new_tspan.set('y', y_list[i].strip())
                new_tspan.text = text[i]
                result.append(new_tspan)
            return result
        return []

    def __style_attr(self, style, name, val):
        pattern = rf'({name}\s*:\s*)([^;]+?)(;|$)'
        regex = re.compile(pattern)
        if not regex.search(style):
            return style + f';{name}:{val};'
        else:
            return regex.sub(rf'{name}:{val};', style)

    @property
    def svg(self) -> str:
        return ET.tostring(self.tree.getroot(), encoding='unicode')

    @property
    def width(self) -> float:
        val = self.tree.getroot().get('width')
        return float( utils.pattern_get(r'([0-9.]+)', val, 1) )

    @width.setter
    def width(self, value: float):
        preval = self.tree.getroot().get('width')
        newval = re.sub(r'([0-9.]+)', str(value), preval)
        self.tree.getroot().set('width', newval)

    @property
    def height(self) -> float:
        val = self.tree.getroot().get('height')
        return float( utils.pattern_get(r'([0-9.]+)', val, 1) )

    @height.setter
    def height(self, value: float):
        preval = self.tree.getroot().get('height')
        newval = re.sub(r'([0-9.]+)', str(value), preval)
        self.tree.getroot().set('height', newval)

    @property
    def width_unit(self) -> str:
        val = self.tree.getroot().get('width')
        return utils.pattern_get(r'([0-9.]+)(.*?)$', val, 2)

    @property
    def height_unit(self) -> str:
        val = self.tree.getroot().get('height')
        return utils.pattern_get(r'([0-9.]+)(.*?)$', val, 2)

    @property
    def viewbox_width(self) -> str:
        val = self.tree.getroot().get('viewBox')
        return self.__viewbox_get(val, 3)

    @property
    def viewbox_height(self) -> str:
        val = self.tree.getroot().get('viewBox')
        return self.__viewbox_get(val, 4)

    def __viewbox_get(self, viewbox: str, get: int) -> str:
        num = r'([0-9.]+\s*[a-zA-Z%]*)'
        return utils.pattern_get(rf'{num}\s+{num}\s+{num}\s+{num}', viewbox, get)

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
        return Page(page_num, svg, text_layer_svg)

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
        vars['width'] = str(page.width) + page.width_unit
        vars['height'] = str(page.height) + page.height_unit
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
