import glob, os, pymupdf
from PIL import Image
for f in glob.glob('ref/check/final-*.png'): os.remove(f)
for f,t in [('Agentic-Z Guide.pdf','guide'),('Agentic-Z Agent Team.pdf','team')]:
    d=pymupdf.open(f)
    for i,p in enumerate(d): p.get_pixmap(dpi=50).save(f'ref/check/final-{t}-p{i+1:02d}.png')
    fs=sorted(glob.glob(f'ref/check/final-{t}-p*.png'))
    w,h=Image.open(fs[0]).size
    for g in glob.glob(f'chrome-tmp/sheet-{t}-*.png'): os.remove(g)
    for k in range(0,len(fs),8):
        sh=Image.new('RGB',(w*4,h*2),'white')
        for j,x in enumerate(fs[k:k+8]): sh.paste(Image.open(x),((j%4)*w,(j//4)*h))
        sh.save(f'chrome-tmp/sheet-{t}-{k//8+1}.png')
    print(t,len(fs))
