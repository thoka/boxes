import math
import svgwrite
import cairo as cairo_o

from affine import Affine 
from svgwrite import mm 

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
        self.dwg = svgwrite.Drawing(filename="new-"+filename)
    
        self.csurf = cairo_o.SVGSurface(filename, 10000, 10000)

    def flush(self):
        pass

    def finish(self):
        
        self.dwg['width'] = self._ctx._xmax-self._ctx._xmin+2*self._ctx._padding
        self.dwg['height'] = self._ctx._ymax-self._ctx._ymin+2*self._ctx._padding

        self._ctx._parts.translate( PADDING - self._ctx._xmin, PADDING - self._ctx._ymin )

        self.dwg.save()

        self.csurf.finish()

def report(func):

    return func

    def wrapper(self,*l,**d):
        xy = self._xy
        cxy = self._cctx.get_current_point()
        res = func(self,*l,**d)
        print(func.__name__,l,res,xy,cxy)
        return res

    return wrapper

r = report
class Context:
    def __init__(self,surface,*al,**ad):
        self._dwg = surface.dwg
        self._parts = self._dwg.add( self._dwg.g(id='parts') )
        surface._ctx = self
   
        self._cctx = cairo_o.Context(surface.csurf)

        self._xmin = self._ymin = 100000
        self._xmax = self._ymax = -100000
        self._padding = 10

        self._actions = []
        self._wrappers = {}      
        self._stack = []
        self._path = None
        self._m = Affine.translation(0,0)
        self._xy = (0,0)
        self._lw = 0
        self._rgb = (0,0,0)
        self._ff = 'sans-serif'

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

    def _update_bounds(self,*xy):
        x,y = self._m*xy
        self._xmin = min(self._xmin,x)
        self._xmax = max(self._xmax,x)
        self._ymin = min(self._ymin,y)
        self._ymax = max(self._ymax,y)

    @r
    def save(self):
        self._stack.append( (self._m, self._xy, self._lw, self._rgb) )
        self._cctx.save()

    @r
    def restore(self):
        self._m,self._xy, self._lw, self._rgb  = self._stack.pop()
        self._xy = (0,0)
        self._cctx.restore()

    @r
    def translate(self,x,y):
        self._m *= Affine.translation(x,y)
        self._xy = (0,0)
        self._cctx.translate(x,y)

    @r
    def scale(self,sx,sy):
        self._m *= Affine.scale(sx,sy)
        self._cctx.scale(sx,sy)

    @r
    def rotate(self,r):
        self._m *= Affine.rotation(180*r/math.pi)
        self._cctx.rotate(r)

    @r
    def set_line_width(self,lw):
        self._lw = lw
        self._cctx.set_line_width(lw)

    @r
    def set_source_rgb(self,r,g,b):
        self._rbg = (r,g,b)
        self._cctx.set_source_rgb(r,g,b)

    @r
    def move_to(self,x,y):
        self._xy = (x,y)
        self._update_bounds(x,y)
        self._cctx.move_to(x,y)

    @r
    def line_to(self,x,y):

        self._update_bounds(x,y)
        x1,y1 = self._xy
        x2,y2 = x,y

        self._xy = (x2,y2)
        self._cctx.line_to(x,y)

        if points_equal(x2,y2,x1,y1):
            return

        self._parts.add(
            self._dwg.line(start=self._m*(x1,y1),end=self._m*(x2,y2),stroke="black",stroke_width=self._lw)            
        )

    @r
    def rectangle(self,x,y,width,height):
        self._update_bounds(x,y)
        self._update_bounds(x+width,y+height)
        self._cctx.rectangle(x,y,width,height)
        pass

    @r
    def select_font_face(self,ff):
        self._ff = ff 
        self._cctx.select_font_face(ff)

    @r
    def set_font_size(self,fs):
        self._fs = fs
        self._cctx.set_font_size(fs)

    @r
    def show_text(self,text):
        self._cctx.show_text(text)
        pass

    @r
    def arc(self,xc,yc,radius,angle1,angle2):
        x1,y1 = radius*math.cos(angle1)+xc,radius*math.sin(angle1)+yc
        x2,y2 = radius*math.cos(angle2)+xc,radius*math.sin(angle2)+yc

        # self.line_to(x1,y1)
        self._xy = (x2,y2)
        self._cctx.arc(xc,yc,radius,angle1,angle2)

    @r
    def arc_negative(self,xc,yc,radius,angle1,angle2):
        x1,y1 = radius*math.cos(angle1)+xc,radius*math.sin(angle1)+yc
        x2,y2 = radius*math.cos(angle2)+xc,radius*math.sin(angle2)+yc

        # self.line_to(x1,y1)
        self._xy = (x2,y2)
        self._cctx.arc_negative(xc,yc,radius,angle1,angle2)

    @r
    def curve_to(self,x1, y1, x2, y2, x3, y3):
        self._xy = (x3,y3)
        self._update_bounds(x3,y3)
        self._cctx.curve_to(x1,y1,x2,y2,x3,y3)

    @r
    def stroke(self):
        self._xy = (0,0)
        self._cctx.stroke()

    @r
    def fill(self):
        self._xy = (0,0)
        self._cctx.fill()

    @r
    def text_extents(self,text):
        extents = self._cctx.text_extents(text)
        return extents
        return (10,10,10*len(text),10,10,10*len(text))

    @r
    def get_current_point(self):
        cxy = self._cctx.get_current_point()
        if not points_equal(*self._xy,*cxy):
            print(self._xy,cxy)
            raise RuntimeError()
        #return cxy
        return self._xy

    @r
    def flush(self):
        self._cctx.flush()
        pass
