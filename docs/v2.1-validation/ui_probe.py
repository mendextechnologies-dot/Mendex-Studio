"""On-screen Windows Qt audit; no offscreen platform and no production writes."""
import json, os, subprocess, sys, time, traceback
from pathlib import Path
R=Path(__file__).resolve().parents[2]
E=Path(__file__).parent/'evidence'
sys.path.insert(0,str(R/'src'))
os.environ.pop('QT_QPA_PLATFORM',None)
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTabWidget
from PySide6.QtCore import QTimer
from mendex_core.service import StudioService
from mendex_core.controller import MendexEngineeringController
from mendex_ui.window import StudioWindow
ROOT=E/'ui-data'
service=StudioService(ROOT)
product=service.create_product('AUDIT-UI','Generic desktop reference','dc_dc_converter','Independent audit')
service.update_specification(product.active_revision_id, {'vin_nom_v':24,'vout_v':5,'iout_a':4,'source':'Independent generic audit reference'})
controller=MendexEngineeringController(ROOT)
controller.create_workspace('Visible audit workspace')
app=QApplication([])
errors=[]
sys.excepthook=lambda t,v,tb:errors.append(''.join(traceback.format_exception(t,v,tb)))
results={'platform':app.platformName(),'root':str(ROOT),'errors':errors}
window=StudioWindow(service)
window.resize(1440,960)
window.show()
def run():
    try:
        results['visible']=window.isVisible()
        results['native_window_id']=int(window.winId())
        results['navigation']=[window.navigation.item(i).text() for i in range(window.navigation.count())]
        results['pages']=[]
        for i in range(window.navigation.count()):
            window.navigation.setCurrentRow(i);app.processEvents()
            p=E/f'ui-page-{i}.png';window.grab().save(str(p))
            results['pages'].append({'row':i,'current_page':window.pages.currentIndex(),'visible_labels':[x.text() for x in window.pages.currentWidget().findChildren(QLabel) if x.isVisible()],'visible_buttons':[x.text() for x in window.pages.currentWidget().findChildren(QPushButton) if x.isVisible()]})
        results['tabs']=[[w.tabText(i) for i in range(w.count())] for w in window.findChildren(QTabWidget)]
        results['obsolete_instantiated']={x:hasattr(window,x) for x in ['workflow_studio','design_studio','knowledge_panel']}
        # Exercise existing stale search mapping without opening native tools or dialogs.
        results['search_navigation']=[]
        for term in ['LTspice','jobs','workflow','design']:
            window.navigation.setCurrentRow(0)
            window._on_search_item_activated(term);app.processEvents()
            results['search_navigation'].append({'term':term,'selected_row':window.navigation.currentRow(),'page':window.pages.currentIndex()})
        before=window.simulation_center.combo_ws.count()
        new=controller.create_workspace('External workspace after UI startup')
        app.processEvents()
        results['external_workspace_sync']={'before':before,'after_no_refresh':window.simulation_center.combo_ws.count(),'created':new,'database_count':len(service.integrations.list_workspaces())}
        results['dashboard_workspace_metric']=[x.text() for x in window.enterprise_dashboard.card_workspaces.findChildren(QLabel) if x.property('class')=='metric_value']
        window.enterprise_dashboard.refresh_metrics()
        results['dashboard_workspace_metric_after_refresh']=[x.text() for x in window.enterprise_dashboard.card_workspaces.findChildren(QLabel) if x.property('class')=='metric_value']
        window.close()
        reopened=StudioWindow(StudioService(ROOT));reopened.show();app.processEvents()
        results['restart']={'product_count':len(reopened.service.list_products()),'workspace_count':len(reopened.service.integrations.list_workspaces()),'specification':reopened.specification.toPlainText(),'simulation_workspace_count':reopened.simulation_center.combo_ws.count()}
        reopened.close()
    except Exception:
        results['fatal']=traceback.format_exc()
    finally:
        (E/'ui.json').write_text(json.dumps(results,indent=2,default=str),encoding='utf-8')
        app.quit()
QTimer.singleShot(1500,run)
app.exec()
