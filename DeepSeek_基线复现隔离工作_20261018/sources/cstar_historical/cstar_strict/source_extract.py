"""Extract paper prose with LaTeX equations, using only the standard library."""
from html.parser import HTMLParser
from pathlib import Path

class Reader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.math_depth = 0
        self.out = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'math':
            self.out.append(' $'+attrs.get('alttext','')+'$ ')
            self.math_depth += 1
        if tag in ('p','h2','h3','h4','h5','h6','tr','li') and not self.math_depth:
            self.out.append('\n')
    def handle_endtag(self, tag):
        if tag == 'math':
            self.math_depth -= 1
    def handle_data(self, data):
        if not self.math_depth:
            self.out.append(data)

if __name__ == '__main__':
    import sys
    r=Reader()
    r.feed((Path(__file__).parent.parent/'cstar_reproduction/sources/paper.html').read_text(encoding='utf8'))
    text=''.join(r.out)
    if len(sys.argv)>1:
        begin=text.rindex(sys.argv[1])
        text=text[begin:begin+int(sys.argv[2] if len(sys.argv)>2 else 12000)]
    print(text)
