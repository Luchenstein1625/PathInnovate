"""Recompute diagnostics from archived answers. No API calls and no new model runs."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from copilot.evaluator_asesor import fmt_ok

def summarize_evidence(path):
    path=Path(path);d=json.loads(path.read_text(encoding='utf-8'));out={}
    for cfg in d['configs']:
        rows=[v[cfg] for v in d['respuestas'].values() if cfg in v]
        if not rows:continue
        checks=[lambda r:fmt_ok(r['answer']),lambda r:r.get('citas_ok') is True,lambda r:r.get('cifras_ok') is True,lambda r:r.get('correcta') is True]
        current=rows[:];stages=[]
        for name,fn in zip(['formato','citas_sintacticas','cifras_en_contexto','etiqueta_referencia'],checks):
            previous=len(current);current=[r for r in current if fn(r)]
            stages.append(dict(etapa=name,n_entrada=previous,n_aprobadas=len(current),tasa_condicional=len(current)/previous if previous else None))
        out[cfg]=dict(n_respuestas_archivadas=len(rows),repeticion=0,etapas=stages,tasa_conjunta=len(current)/len(rows))
    return dict(archivo=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),meta=d['meta'],diagnosticos=out,
        limitacion='El JSON conserva respuestas individuales de la repeticion 0. Las metricas agregadas internas cubren 3 repeticiones; no se reconstruyen las 96 respuestas desde 32. Citas y cifras son controles sintacticos, no validacion semantica ni juicio independiente. Tasas condicionales calculadas sobre supervivientes; no se multiplican marginales independientes.')
if __name__=='__main__':
    out=[summarize_evidence(p) for p in ['eval_asesor/resultados_asesor_FINAL3.json','eval_asesor/externas/resultados_asesor.json']]
    Path('docs/evidencia_feedback.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False,indent=2))
