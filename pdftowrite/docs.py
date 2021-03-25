import xml.etree.ElementTree as ET
import re, copy
import shortuuid
from typing import Optional
import pdftowrite.utils as utils

SVG_NS = 'http://www.w3.org/2000/svg'
XLINK_NS = 'http://www.w3.org/1999/xlink'

ET.register_namespace('', SVG_NS)
ET.register_namespace('xlink', XLINK_NS)

class Page:
    def __init__(self, page_num, svg, text_layer_svg, uniquify=True):
        self.page_num = page_num
        self.suffix = '-' + shortuuid.uuid()[:7] + '-p' + str(self.page_num)
        self.__process_svg(svg, text_layer_svg, uniquify)

    def __process_svg(self, svg, text_layer_svg, uniquify) -> None:
        svg = re.sub(r'<\?xml[^(\?>)]*\?>', '', svg)
        self.tree = ET.ElementTree( ET.fromstring(svg) )
        self.__remove_metadata()
        if uniquify: self.__uniquify()
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
        if ('{%s}href' % XLINK_NS) in el.attrib:
            el.attrib['{%s}href' % XLINK_NS] += suffix
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
        g = tree.getroot().find('./{%s}g[last()]' % SVG_NS)
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
        texts = tree.getroot().findall('.//{%s}text' % SVG_NS)
        for text in texts:
            for el in text.iter():
                el.attrib.pop('id', None)
                el.attrib.pop('clip-path', None)
            tspans = text.findall('.//{%s}tspan' % SVG_NS)
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
    def x(self) -> float:
        val = self.tree.getroot().get('x', '0')
        return float( utils.pattern_get(r'([0-9.]+)', val, 1) )

    @x.setter
    def x(self, value: float):
        preval = self.tree.getroot().get('x', '0')
        newval = re.sub(r'([0-9.]+)', str(value), preval)
        self.tree.getroot().set('x', newval)

    @property
    def y(self) -> float:
        val = self.tree.getroot().get('y', '0')
        return float( utils.pattern_get(r'([0-9.]+)', val, 1) )

    @y.setter
    def y(self, value: float):
        preval = self.tree.getroot().get('y', '0')
        newval = re.sub(r'([0-9.]+)', str(value), preval)
        self.tree.getroot().set('y', newval)

    @property
    def x_unit(self) -> str:
        val = self.tree.getroot().get('x', '0')
        return utils.pattern_get(r'([0-9.]+)(.*?)$', val, 2)

    @x_unit.setter
    def x_unit(self, unit: str):
        val = self.x
        self.tree.getroot().set('x', f'{val}{unit}')

    @property
    def y_unit(self) -> str:
        val = self.tree.getroot().get('y', '0')
        return utils.pattern_get(r'([0-9.]+)(.*?)$', val, 2)

    @y_unit.setter
    def y_unit(self, unit: str):
        val = self.y
        self.tree.getroot().set('y', f'{val}{unit}')

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

    @width_unit.setter
    def width_unit(self, unit: str):
        val = self.width
        self.tree.getroot().set('width', f'{val}{unit}')

    @property
    def height_unit(self) -> str:
        val = self.tree.getroot().get('height')
        return utils.pattern_get(r'([0-9.]+)(.*?)$', val, 2)

    @height_unit.setter
    def height_unit(self, unit: str):
        val = self.height
        self.tree.getroot().set('height', f'{val}{unit}')

    @property
    def width_full(self) -> str:
        return self.tree.getroot().get('width').strip()

    @width_full.setter
    def width_full(self, val: str):
        self.tree.getroot().set('width', val)

    @property
    def height_full(self) -> str:
        return self.tree.getroot().get('height').strip()

    @height_full.setter
    def height_full(self, val: str):
        self.tree.getroot().set('height', val)

    @property
    def viewbox(self) -> Optional[str]:
        return self.tree.getroot().get('viewBox', None)

    @viewbox.setter
    def viewbox(self, value: Optional[str]):
        if value is None:
            self.tree.getroot().pop('viewBox', None)
        else:
            self.tree.getroot().set('viewBox', value)

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

class Document:
    def __init__(self, svg: str, page_nums: set[int]):
        self.tree = ET.ElementTree( ET.fromstring(svg) )
        self.pages = []
        page_els = self.tree.getroot().findall('./{%s}svg' % SVG_NS)
        num = 0
        for page_el in page_els:
            num += 1
            if 'write-page' not in page_el.get('class', ''): continue
            if num not in page_nums: continue
            page_svg = ET.tostring(page_el, encoding='unicode')
            page = Page(num, page_svg, None, False)
            self.pages.append(page)
        if num <= 0: raise Exception('Document has no pages')

def num_pages(svg: str) -> int:
    tree = ET.ElementTree( ET.fromstring(svg) )
    page_els = tree.getroot().findall('./{%s}svg' % SVG_NS)
    num = 0
    for page_el in page_els:
        if 'write-page' not in page_el.get('class', ''): continue
        num += 1
    return num
