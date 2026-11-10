import FreeCAD as App, Part
doc=App.newDocument("MendexSoftwareFixture")
obj=doc.addObject("PartDesign::Feature","GenericBox")
obj.Shape=Part.makeBox(1,1,1)
doc.recompute()
Part.export([obj],'C:\\Users\\Sagar\\AppData\\Local\\Temp\\m100native-lzwnvbpu\\synthetic-cube.step')
App.closeDocument(doc.Name)
