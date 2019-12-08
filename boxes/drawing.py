import math
from affine import Affine 

EPS = 1e-4
PADDING = 3

def points_equal(x1,y1,x2,y2):
   return abs(x1-x2)<EPS and abs(y1-y2)<EPS

def pdiff(p1,p2):
    x1,y1 = p1
    x2,y2 = p2
    return (x1-x2,y1-y2)

class Drawing:
    def __init__(self,**args):
        self.args = args
        self.parts = []
        self._p = self.new_part('default')

    def render(self,renderer):
        renderer.init(**self.args)
        for p in self.parts:
            p.render(renderer)
        renderer.finish()

    def new_part(self,name='part'):
        if self.parts and len(self.parts[-1].pathes)==0: 
            return self._p
        p = Part(name)
        self.parts.append(p)
        self._p = p
        return p

    def append(self,*path):
        self._p.append(*path)

    def stroke(self,**params):
        return self._p.stroke(**params)

    def move_to(self,*xy):
        self._p.move_to(*xy)

    def extents(self):
        return sum( [ p.extents() for p in self.parts ] )

class Part:
    def __init__(self,name):
        self.pathes = []
        self.path = []

    def extents(self):
        return sum( [ p.extents() for p in self.pathes ] )

    def append(self,*path):
        self.path.append(path)
 
    def stroke(self,**params):
        if len(self.path)==0: return
        # search for path ending at new start coordinates to append this path to
        xy0 = self.path[0][1:3]
        for p in reversed(self.pathes):
            xy1 = p.path[-1][1:3]
            if points_equal(*xy0,*xy1):
                p.path.extend(self.path[1:])
                self.path = []
                return p
        p = Path(self.path,params)
        self.pathes.append(p)
        self.path = []
        return p

    def move_to(self,*xy):
        if len(self.path)==0:
            self.path.append( ('M',*xy) )
        elif self.path[-1][0]=='M':
            self.path[-1]=('M',*xy)
        else:
            xy0 = self.path[-1][1:3]
            if not points_equal(*xy0,*xy):
                self.path.append( ('M',*xy) )



class Path:
    def __init__(self,path,params):
        self.path = path
        self.params = params
        #self._extents = None

    def __repr__(self):
        l = len(self.path)
        #x1,y1 = self.path[0][1:3]
        x2,y2 = self.path[-1][1:3]
        return f'Path[{l}] to ({x2:.2f},{y2:.2f})'

    def extents(self):
        #if self._extents is not None: return self._extents
        e = Extents()
        for p in self.path:
            e.add(*p[1:3])
        return e


class Context:
    def __init__(self,renderer,*al,**ad):
        self._dwg = Drawing(**ad)
        self._renderer = renderer
 
        self._bounds = Extents()
        self._padding = PADDING
        
        self._stack = []
        self._m = Affine.translation(0,0)
        self._xy = (0,0)
        self._lw = 0
        self._rgb = (0,0,0)
        self._ff = 'sans-serif'
        self._last_path = None

    def _update_bounds_(self,mx,my):
        self._bounds.update(mx,my)

    def save(self):
        self._stack.append( (self._m, self._xy, self._lw, self._rgb, self._xy, self._last_path) )
        self._xy = (0,0)

    def restore(self):
        self._m,self._xy, self._lw, self._rgb, self._xy, self._last_path = self._stack.pop()

    ## transformations

    def translate(self,x,y):
        self._m *= Affine.translation(x,y)
        self._xy = (0,0)

    def scale(self,sx,sy):
        self._m *= Affine.scale(sx,sy)

    def rotate(self,r):
        self._m *= Affine.rotation(180*r/math.pi)

    def set_line_width(self,lw):
        self._lw = lw

    def set_source_rgb(self,r,g,b):
        self._rgb = (r,g,b)

    ## path methods

    def _line_to(self,x,y):
        self._add_move()
        x1,y1 = self._mxy
        self._xy = x,y
        x2,y2 = self._mxy = self._m*self._xy
        if not points_equal(x1,y1,x2,y2): 
            self._dwg.append('L',x2,y2)

    def _add_move(self):
        self._dwg.move_to(*self._mxy)

    def move_to(self,x,y):
        self._xy = (x,y)
        self._mxy = self._m*self._xy

    def line_to(self,x,y):
        self._line_to(x,y)
 
    def _arc(self,xc,yc,radius,angle1,angle2,direction):
        x1,y1 = radius*math.cos(angle1)+xc,radius*math.sin(angle1)+yc
        x2,y2 = radius*math.cos(angle2)+xc,radius*math.sin(angle2)+yc
        mx1,my1 = self._m*(x1,y1)
        mx2,my2 = self._m*(x2,y2)
        mxc,myc = self._m*(xc,yc)
        self._line_to(x1,y1)
        self._dwg.append('A',mx2,my2,mxc,myc,radius,direction)
        self._xy = (x2,y2)
        self._mxy = (mx2,my2)

    def arc(self,xc,yc,radius,angle1,angle2):
        self._arc(xc,yc,radius,angle1,angle2,1)

    def arc_negative(self,xc,yc,radius,angle1,angle2):
        self._arc(xc,yc,radius,angle1,angle2,-1)

    def curve_to(self,x1, y1, x2, y2, x3, y3):
        # mx0,my0 = self._m*self._xy
        mx1,my1 = self._m*(x1,y1)
        mx2,my2 = self._m*(x2,y2)
        mx3,my3 = self._m*(x3,y3)
        self._add_move()
        self._dwg.append('C',mx3,my3,mx1,my1,mx2,my2) # destination first!
        self._xy = (x3,y3)

    def stroke(self):
        #print('stroke stack-level=',len(self._stack),'lastpath=',self._last_path,)        
        self._last_path=self._dwg.stroke(rgb=self._rgb, lw=self._lw)            
        self._xy = (0,0)

    def fill(self):
        self._xy = (0,0) 
        raise NotImplementedError()

    def select_font_face(self,ff):
        self._ff = ff 

    def set_font_size(self,fs):
        self._fs = fs

    def show_text(self,text,**args):
        params = { 'ff': self._ff, 'fs': self._fs, 'lw': self._lw }
        params.update(args)
        mx0,my0 = self._m*self._xy
        self._dwg.append('T',mx0,my0,text,params)

    def text_extents(self,text):
        #todo
        return (10,10,10*len(text),10,10,10*len(text))

    def rectangle(self,x,y,width,height):
      
        #todo: better check for empty path?
        self.stroke()

        self.move_to(x,y)
        self.line_to(x+width,y)
        self.line_to(x+width,y+height)
        self.line_to(x,y+height)
        self.line_to(x,y)
        self.stroke()

    def get_current_point(self):
        return self._xy

    def flush(self):
        pass
        #todo: check, if needed
        #self.stroke()

    ## additional methods
    def new_part(self):
        self._dwg.new_part()

class SurfaceMixin:
    def flush(self): pass
    def finish(self): pass
    

class SVGWriteRenderer(SurfaceMixin):
    def __init__(self,fname,width,height):
        self._fname = fname

    def render_drawing(self,drawing):
        import svgwrite

        extents = drawing.extents()

        w = extents.width+2*PADDING
        h = extents.height+2*PADDING

        dwg = svgwrite.Drawing(filename=self._fname)
        #dwg.debug = False

        dwg['width']=f'{w:.2f}mm'
        dwg['height']=f'{h:.2f}mm'
        dwg['viewBox']=f'{extents.xmin-PADDING:.2f} {extents.ymin-PADDING:.2f} {w:.2f} {h:.2f}'

        for i,part in enumerate(drawing.parts):          
            g = dwg.add( dwg.g(id=f'p-{i}',style='fill:none') )
            for j,path in enumerate(part.pathes):
                p = []
                x,y = 0,0
                for c in path.path:
                    x0,y0=x,y
                    C,x,y = c[0:3]
                    if C=='M':
                        p.append( f'M {x:.2f} {y:.2f}' )
                    elif C=='L':
                        p.append( f'L {x:.2f} {y:.2f}' )
                    elif C=='A':
                        radius,direction = c[5:]
                        flag = 0 if direction>0 else 1
                        # use commata to help svgutil find coordinates
                        p.append( f'A {radius:.2f},{radius:.2f},0,0,{flag},{x:.2f} {y:.2f}')
                    elif C=='C':
                        x1,y1,x2,y2 = c[3:]
                        p.append( f'C {x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f} {x:.2f} {y:.2f}')
                color = random_svg_color() # to check for continuity of pathes   
                if p: #todo: might be empty since text is not implemented yet                    
                    g.add( 
                        dwg.path(d=' '.join(p),
                        stroke=color,
                        stroke_width=path.params['lw'] )
                    )
        dwg.save(pretty=True)


class CairoRenderer(SurfaceMixin):
    def __init__(self,fname,width,height):
        self._fname = fname

    def render_drawing(self,drawing):
        # do the actual rendering here
        import cairo

        for i,part in enumerate(drawing.parts):          
            for j,path in enumerate(part.pathes):
                p = []
                x,y = 0,0
                color = random_rgb() # to check for continuity of pathes   

                for c in path.path:
                    x0,y0=x,y
                    C,x,y = c[0:3]
                    if C=='M': 
                        pass
                    elif C=='L': 
                        pass
                    elif C=='A':
                        pass
                        radius,direction = c[5:]
                    elif C=='C': 
                        pass
                        x1,y1,x2,y2 = c[3:]


SVGSurface = SVGWriteRenderer

class Extents:
    __slots__ = "xmin ymin xmax ymax".split()

    def __init__(self,xmin=float('inf'),ymin=float('inf'),xmax=float('-inf'),ymax=float('-inf')):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax 
        self.ymax = ymax

    def add(self,x,y):
        self.xmin = min(self.xmin,x)
        self.xmax = max(self.xmax,x)
        self.ymin = min(self.ymin,y)
        self.ymax = max(self.ymax,y)

    def extend(self,l):
        for x,y in l:
            self.add(x,y)

    def __add__(self,extent):
        return Extents(
            min(self.xmin,extent.xmin),min(self.ymin,extent.ymin),
            max(self.xmax,extent.xmax),max(self.ymax,extent.ymax)
        )

    def __radd__(self,extent):
        if extent == 0:
            return Extents(self.xmin,self.ymin,self.xmax,self.ymax)
        return self.__add__(extent)
       
    def get_width(self):
        return self.xmax-self.xmin
    
    def get_height(self):
        return self.ymax-self.ymin

    width = property(get_width)
    height = property(get_height)
    
    def __repr__(self):
        return f'Extents ({self.xmin},{self.ymin})-({self.xmax},{self.ymax})'


from random import random
def random_svg_color():
    r,g,b = random(),random(), random()
    return f'rgb({r*255:.0f},{g*255:.0f},{b*255:.0f})'                        

