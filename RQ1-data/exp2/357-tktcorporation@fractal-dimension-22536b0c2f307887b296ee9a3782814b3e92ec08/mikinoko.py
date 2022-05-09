import sys
from PIL import Image
import math

def koch(xs,ys,xt,yt,l):
    """
左から各点は
(xs,ys), (x1,y1), (x2,y2), (x3,y3), (xt,yt)
"""

    pl = l/3.0 # 1/3の長さ

    x1 = (2*xs+xt)/3.0
    y1 = (2*ys+yt)/3.0
    x3 = (2*xt+xs)/3.0
    y3 = (2*yt+ys)/3.0

    a = abs(x3-x1)/pl
    if a > 1.0:
        a = 1.0
    if a < -1.0:
        a = -1.0
    theta = math.acos(a)

    if xt > xs:
        if yt > ys:
            x2 = x3 - math.cos(math.pi/3 + theta) * pl
            y2 = y3 - math.sin(math.pi/3 + theta) * pl
        else:
            x2 = x1 + math.cos(math.pi/3 + theta) * pl
            y2 = y1 - math.sin(math.pi/3 + theta) * pl
    else:
        if yt > ys:
            x2 = x1 - math.cos(math.pi/3 + theta) * pl
            y2 = y1 + math.sin(math.pi/3 + theta) * pl
        else:
            x2 = x3 + math.cos(math.pi/3 + theta) * pl
            y2 = y3 + math.sin(math.pi/3 + theta) * pl

    # 長さが閾値以下になったら描画
    if pl < 10:
        draw.line((xs,ys)+(x1,y1), 0, width=1)
        draw.line((x1,y1)+(x2,y2), 0, width=1)
        draw.line((x2,y2)+(x3,y3), 0, width=1)
        draw.line((x3,y3)+(xt,yt), 0, width=1)
        return

    # 次のレベル
    koch(xs,ys,x1,y1,pl)
    koch(x1,y1,x2,y2,pl)
    koch(x2,y2,x3,y3,pl)
    koch(x3,y3,xt,yt,pl)

if __name__== '__main__':
    width = height = int(sys.argv[1])
    im = Image.new("L",(width,height),255)
    draw = ImageDraw.Draw(im)
    xs = 0
    ys = height/2
    xt = xs+width
    yt = ys
    l = math.sqrt((xs-xt)**2+(ys-yt)**2)
    koch(xs,ys,xt,yt,l)
    new_im.save("koch.png","PNG")