import sys, pathlib
from PIL import Image, ImageDraw
d = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2]); per = int(sys.argv[3]) if len(sys.argv)>3 else 6
for t in 'gt':
    files = sorted(d.glob(t+'[0-9][0-9].png'))
    for s in range(0, len(files), per):
        ims = [Image.open(f) for f in files[s:s+per]]
        w, h = ims[0].size
        cols = min(per, 3)
        rows = (len(ims)+cols-1)//cols
        sheet = Image.new('RGB', (cols*(w+10), rows*(h+24)), 'white')
        dr = ImageDraw.Draw(sheet)
        for i, (im, f) in enumerate(zip(ims, files[s:s+per])):
            x, y = (i%cols)*(w+10), (i//cols)*(h+24)
            sheet.paste(im, (x, y+22)); dr.text((x+4, y+4), f.stem, fill='black')
        sheet.save(out / f'sheet-{t}{s+1:02d}.png')
