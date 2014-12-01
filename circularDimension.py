
from dimensioning import *
from dimensioning import __dir__ # not imported with * directive
from drawingSelectionLib import generateSelectionGraphicsItems
from dimensionSvgConstructor import circularDimensionSVG


class CircularDimensioningRect( DimensioningRectPrototype ):

    def activate(self, graphicsScene, graphicsView, page, width, height, 
                 VRT_scale, VRT_ox, VRT_oy, 
                 dimPreview, dimSVGRenderer, **otherKWs):
        ' called each time before dimensioning '
        self.graphicsScene = graphicsScene
        self.graphicsView = graphicsView
        self.drawingPage = page
        self.drawingPageWidth = width
        self.drawingPageHeight = height
        self.VRT_ox = VRT_ox
        self.VRT_oy = VRT_oy
        self.VRT_scale = VRT_scale
        self.dimPreview = dimPreview
        self.dimSVGRenderer = dimSVGRenderer

        self.action_ind = 0
        self.dim_svg_KWs = dict(
            svgParms='width="%(width)i" height="%(height)i" transform="translate( %(VRT_ox)f, %(VRT_oy)f) scale( %(VRT_scale)f, %(VRT_scale)f)"' % locals(),
            svgTag='svg'
            )
        
        debugPrint(3, 'adding dimPreview object to scene')
        graphicsScene.addItem( dimPreview )
        dimPreview.hide()
        self.cleanUpList = [ dimPreview ]
        self.cleanedUp = False

        self.setRect(0, 0, width, height)
        self.setAcceptHoverEvents(True)
        self.setFlag( QtGui.QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True )
        self.setCursor( QtCore.Qt.ArrowCursor ) # http://qt-project.org/doc/qt-5/qt.html#CursorShape-enum
        graphicsScene.addItem( self )

        maskPen =      QtGui.QPen( QtGui.QColor(0,255,0,100) )
        maskPen.setWidth(2.0)
        maskHoverPen = QtGui.QPen( QtGui.QColor(0,255,0,255) )
        maskHoverPen.setWidth(2.0)

        selectGraphicsItems = generateSelectionGraphicsItems( 
            [obj for obj in self.drawingPage.Group  if not obj.Name.startswith('dim')], 
            self.selectDimensioningPoint , doCircles=True, doFittedCircles=True, 
            maskPen=maskPen, maskHoverPen=maskHoverPen, maskBrush = QtGui.QBrush() #clear
            )
        for g in selectGraphicsItems:
            graphicsScene.addItem(g)

        debugPrint(3, 'CircularDimensioningRect.Activated')

    def selectDimensioningPoint( self, event, referer, elementXML, elementParms, elementViewObject ):
        if self.action_ind <> 0:
            return
        x,y = elementParms['x'], elementParms['y']
        self.point1 = x, y
        debugPrint(2, 'center selected at x=%3.1f y=%3.1f' % (x,y))
        self.radius = elementParms['r']
        self.dimScale = 1/elementXML.rootNode().scaling()
        self.action_ind = 1
        referer.lockSelection()

    def mousePressEvent( self, event ):
        if self.action_ind == 0:
            event.ignore() #parse onto parents ...
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            pos = event.scenePos()
            x = ( pos.x() - self.VRT_ox )/ self.VRT_scale
            y = ( pos.y() - self.VRT_oy )/ self.VRT_scale
            debugPrint(3, 'mousePressEvent: x %f, y %f' % (x, y))
            
            if self.action_ind == 1:
                self.point2 = x,y
                debugPrint(2, 'dimension radial direction point set to x=%3.1f y=%3.1f' % (x,y))
                self.action_ind = self.action_ind + 1
            elif self.action_ind == 2:
                self.point3 = x, y
                debugPrint(2, 'radius dimension tail defining point set to x=%3.1f y=%3.1f' % (x,y))
                self.action_ind = self.action_ind + 1
            elif self.action_ind == 3: #'placeDimensionText'
                XML = circularDimensionSVG( self.point1[0], self.point1[1], self.radius,
                                          self.point2[0], self.point2[1], 
                                          self.point3[0], self.point3[1], 
                                          x, y, dimScale=self.dimScale)
                if XML <> None:
                    debugPrint(3, XML)
                    viewName = findUnusedObjectName('dim')
                    debugPrint(2, 'creating dimension %s' % viewName)
                    App.ActiveDocument.addObject('Drawing::FeatureView',viewName)
                    App.ActiveDocument.getObject(viewName).ViewResult = XML                    
                    self.drawingPage.addObject(App.ActiveDocument.getObject(viewName))
                self.cleanUp()

        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            pass
            #if self.action_ind > 0:
            #    self.action_ind = self.action_ind - 1
            #else:
            #    self.cleanUp()

    def hoverMoveEvent(self, event):
        if self.action_ind == 0 :
            return
        XML = None
        pos = event.scenePos()
        x = ( pos.x() - self.VRT_ox )/ self.VRT_scale
        y = ( pos.y() - self.VRT_oy )/ self.VRT_scale
        debugPrint(4, 'hoverMoveEvent: x %f, y %f'%(x,y))
        if self.action_ind == 1 :
            XML = circularDimensionSVG( self.point1[0], self.point1[1], self.radius, x, y, dimScale=self.dimScale, **self.dim_svg_KWs )
        elif self.action_ind == 2:
            XML = circularDimensionSVG( self.point1[0], self.point1[1], self.radius, 
                                self.point2[0], self.point2[1], x, y, dimScale=self.dimScale, **self.dim_svg_KWs )
        else: 
            XML = circularDimensionSVG( self.point1[0], self.point1[1], self.radius, 
                                self.point2[0], self.point2[1], 
                                self.point3[0], self.point3[1], 
                                x, y, dimScale=self.dimScale,**self.dim_svg_KWs )
        if XML <> None:
            self.dimSVGRenderer.load( QtCore.QByteArray( XML ) )
            self.dimPreview.update()
            self.dimPreview.show()
        else:
            self.dimPreview.hide()
    


moduleGlobals = {}
class circularDimension:
    "this class will create a line after the user clicked 2 points on the screen"
    def Activated(self):
        if not get_FreeCAD_drawing_variables(moduleGlobals):
            return #an error has occurred ...    
        if not moduleGlobals.has_key('dimensioningRect') or not moduleGlobals['dimensioningRect'].cleanedUp: 
            # then initialize graphicsScene Objects, otherwise dont recreate objects. 
            # initializing dimPreview is particularly troublesome, as in FreeCAD 0.15 this is unstable and occasionally causes FreeCAD to crash.

            debugPrint(4, 'creating dimPreview')
            dimPreview = QtSvg.QGraphicsSvgItem()
            dimSVGRenderer = QtSvg.QSvgRenderer()
            dimSVGRenderer.load( QtCore.QByteArray( '''<svg width="%i" height="%i"> </svg>''' % (moduleGlobals['width'], moduleGlobals['height']) ) )
            dimPreview.setSharedRenderer( dimSVGRenderer )

            debugPrint(4, 'Adding CircularDimensioningRect to graphicsScene')
            dimensioningRect = CircularDimensioningRect()

            moduleGlobals.update(locals())
            del moduleGlobals['self']
            assert not moduleGlobals.has_key('moduleGlobals')
        moduleGlobals['dimensioningRect'].activate(**moduleGlobals)
        
    def GetResources(self): 
        return {
            'Pixmap' : os.path.join( __dir__ , 'circularDimension.svg' ) , 
            'MenuText': 'Circular Dimension', 
            'ToolTip': 'Creates a circular dimension'
            } 

FreeCADGui.addCommand('circularDimension', circularDimension())
