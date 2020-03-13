import math
import svgwrite

try:
    import cairo 
except ImportError:
    cairo = None

#cairo = None

from affine import Affine 
from svgwrite import mm 

from random import random

EPS = 1e-2
PADDING = 10

def points_equal(x1,y1,x2,y2):
   return abs(x1-x2)<EPS and abs(y1-y2)<EPS

def pdiff(p1,p2):
    x1,y1 = p1
    x2,y2 = p2
    return (x1-x2,y1-y2)

class SVGSurface:
    def __init__(self,filename,*al,**ad):
        self._filename = filename
        self.dwg = svgwrite.Drawing(filename="nc-"+filename)

        if cairo:    
            self.csurf = cairo.SVGSurface(filename, 10000, 10000)

    def flush(self):
        pass

    def finish(self):
        
        self.dwg['width'] = self._ctx._xmax-self._ctx._xmin+2*self._ctx._padding
        self.dwg['height'] = self._ctx._ymax-self._ctx._ymin+2*self._ctx._padding

        self._ctx._parts.translate( PADDING - self._ctx._xmin, PADDING - self._ctx._ymin )

        self.dwg.save(pretty=True)

        if cairo:
            self.csurf.finish()

def report(func):

    #return func

    def wrapper(self,*l,**d):
        xy = self._xy

        if cairo:
            cxy = self._cctx.get_current_point()
        else:
            cxy = ''

        res = func(self,*l,**d)
        print(func.__name__,l,res,xy,cxy)
        return res

    return wrapper

r = report

class Context:
    def __init__(self,surface,*al,**ad):
        self._dwg = surface.dwg
        self._parts = self._dwg.add( self._dwg.g(id='parts',style='fill:none') )
        surface._ctx = self
   
        self._xmin = self._ymin = 100000
        self._xmax = self._ymax = -100000
        self._padding = PADDING

        self._actions = []
        self._wrappers = {}      
        self._stack = []
        self._path = []
        self._m = Affine.translation(0,0)
        self._xy = (0,0)
        self._lw = 0
        self._rgb = (0,0,0)
        self._ff = 'sans-serif'

        if cairo:
            self._cctx = cairo.Context(surface.csurf)

    def _create_new_wrapper_function(self,key):
        def wrapper(*al,**ad):
            self._record_action(key,*al,**ad)
        return wrapper

    def _record_action(self,key,*al,**ad):
        data = (key,al,ad)
        self._actions.append( data ) 
        print(data)

    def __getattr__(self,key):
        if not key in self._wrappers:
            self._wrappers[key] = self._create_new_wrapper_function(key)
        return self._wrappers[key]

    def _update_bounds_(self,mx,my):
        self._xmin = min(self._xmin,mx)
        self._xmax = max(self._xmax,mx)
        self._ymin = min(self._ymin,my)
        self._ymax = max(self._ymax,my)

    @r
    def save(self):
        self._stack.append( (self._m, self._xy, self._lw, self._rgb, self._xy) )
        self._xy = (0,0)
        if cairo: self._cctx.save()

    @r
    def restore(self):
        self._m,self._xy, self._lw, self._rgb, self._xy = self._stack.pop()
        if cairo: self._cctx.restore()

    ## transformations

    @r
    def translate(self,x,y):
        self._m *= Affine.translation(x,y)
        self._xy = (0,0)
        if cairo: self._cctx.translate(x,y)

    @r
    def scale(self,sx,sy):
        self._m *= Affine.scale(sx,sy)
        if cairo: self._cctx.scale(sx,sy)

    @r
    def rotate(self,r):
        self._m *= Affine.rotation(180*r/math.pi)
        if cairo: self._cctx.rotate(r)

    ##

    @r
    def set_line_width(self,lw):
        self._lw = lw
        if cairo: self._cctx.set_line_width(lw)

    @r
    def set_source_rgb(self,r,g,b):
        self._rgb = (r,g,b)
        if cairo: self._cctx.set_source_rgb(r,g,b)

    def _svg_color(self):
        r,g,b = self._rgb
        r,g,b = random(),random(), random()
        return f'rgb({r*255:.0f},{g*255:.0f},{b*255:.0f})'

    ## path methods

    def _line_to(self,x,y):

        x1,y1 = self._m*self._xy
        self._xy = x,y
        x2,y2 = self._m*self._xy
        self._update_bounds_(x1,y1)
        self._update_bounds_(x2,y2)
        dx,dy = x2-x1,y2-y1

        self._path.append(f'L {x2:.2f},{y2:.2f}')  
        return
        if abs(dx)<EPS:
            if abs(dy)>EPS:
                self._path.append(f'V {y2:.2f}')  
        elif abs(dy)<EPS:
            self._path.append(f'H {x2:.2f}')
        else:
            self._path.append(f'L {x2:.2f},{y2:.2f}')  

    @r
    def move_to(self,x,y):
        self._xy = (x,y)
        x1,y1 = self._m*self._xy
        if self._path and self._path[-1].startswith('M'):
            self._path.pop()
        self._path.append( f'M {x1:.2f},{y1:.2f}' )
        if cairo: self._cctx.move_to(x,y)

    @r
    def line_to(self,x,y):
        self._line_to(x,y)
        if cairo: self._cctx.line_to(x,y)

    @r
    def arc(self,xc,yc,radius,angle1,angle2):
        x1,y1 = radius*math.cos(angle1)+xc,radius*math.sin(angle1)+yc
        x2,y2 = radius*math.cos(angle2)+xc,radius*math.sin(angle2)+yc

        mx2,my2 = self._m*(x2,y2)
        self._line_to(x1,y1)
        self._path.append(
            f'A {radius:.2f},{radius:.2f} 0 0,0 {mx2:.2f},{my2:.2f}'
        )
        self._xy = (x2,y2)
        if cairo: self._cctx.arc(xc,yc,radius,angle1,angle2)

    @r
    def arc_negative(self,xc,yc,radius,angle1,angle2):
        x1,y1 = radius*math.cos(angle1)+xc,radius*math.sin(angle1)+yc
        x2,y2 = radius*math.cos(angle2)+xc,radius*math.sin(angle2)+yc

        mx2,my2 = self._m*(x2,y2)
        self._update_bounds_(mx2,my2)
        self._line_to(x1,y1)
        self._path.append(
            f'A {radius:.2f},{radius:.2f} 0 0,1 {mx2:.2f},{my2:.2f}'
        )

        self._xy = (x2,y2)
        if cairo: self._cctx.arc_negative(xc,yc,radius,angle1,angle2)

    @r
    def curve_to(self,x1, y1, x2, y2, x3, y3):
        self._xy = (x3,y3)
        mx1,my1 = self._m*(x1,y1)
        mx2,my2 = self._m*(x2,y2)
        mx3,my3 = self._m*(x3,y3)
        self._update_bounds_(mx3,my3)
        self._line_to(x3,y3) # TODO
        if cairo: self._cctx.curve_to(x1,y1,x2,y2,x3,y3)

    @r
    def stroke(self):
        if len(self._path)>1:
            self._parts.add(
                self._dwg.path(d=' '.join(self._path),stroke=self._svg_color(),stroke_width=self._lw)            
            )
        else:
            pass # print('stroke without path')
        self._xy = (0,0)
        self._path = []

        if cairo: self._cctx.stroke()

    @r
    def fill(self):
        self._xy = (0,0) 
        self._path = [] #TODO
        if cairo: self._cctx.fill()

    @r
    def select_font_face(self,ff):
        self._ff = ff 
        if cairo: self._cctx.select_font_face(ff)

    @r
    def set_font_size(self,fs):
        self._fs = fs
        if cairo: self._cctx.set_font_size(fs)

    @r
    def show_text(self,text):
        if cairo: self._cctx.show_text(text)

    @r
    def text_extents(self,text):
        if cairo:
            extents = self._cctx.text_extents(text)
            return extents
        return (10,10,10*len(text),10,10,10*len(text))


    @r
    def rectangle(self,x,y,width,height):
        
        x1,y1 = self._m*(x,y)
        x2,y2 = self._m*(x+width,y+height)
        self._update_bounds_(x1,y1)
        self._update_bounds_(x2,y2)

        self._parts.add(
            self._dwg.rect( 
                (f'{min(x1,x2):.2f}',f'{min(y1,y2):.2f}'), #insert
                (f'{abs(x2-x1):.2f}',f'{abs(y2-y1):.2f}'), #size
                stroke=self._svg_color(),stroke_width=self._lw
            )            
        )
        if cairo: self._cctx.rectangle(x,y,width,height)

    @r
    def get_current_point(self):
        
        if cairo:
            cxy = self._cctx.get_current_point()
            if not points_equal(*self._xy,*cxy):
                print(self._xy,cxy)
                raise RuntimeError()

        return self._xy

    @r
    def flush(self):
        if cairo: self._cctx.flush()
        