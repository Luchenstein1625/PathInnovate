"""Figuras exactas a partir de FINAL3, evaluacion externa y presupuesto vigente."""
from pathlib import Path
import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'entrega'/'figuras';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
w=load_workbook(ROOT/'entrega/Anexo_B_PathInnovate.xlsx',data_only=True)
fig,ax=plt.subplots(figsize=(9,4.7));x=np.arange(3);width=.34
for off,row,color,label in [(-width/2,12,'#3979a8','12 meses'),(width/2,13,'#183c60','36 meses')]:
 vals=[w['TCO'].cell(row,c).value for c in [2,3,4]];bars=ax.bar(x+off,vals,width,color=color,label=label);ax.bar_label(bars,labels=[f'{v:,.0f}' for v in vals],padding=3,fontsize=9)
ax.set_xticks(x,['API + RAG + verificador','Mixto 80 % SLM / 20 % API','SLM dedicado']);ax.set_ylabel('TCO en USD');ax.set_ylim(0,290000);ax.legend();ax.set_title('Presupuesto corregido con tokens de FINAL3');fig.tight_layout();fig.savefig(OUT/'fig2_tco.png',dpi=200);plt.close(fig)
rows=[(w['Sensibilidad'].cell(r,2).value,w['Sensibilidad'].cell(r,6).value,w['Sensibilidad'].cell(r,7).value) for r in range(2,9)];rows=sorted(rows,key=lambda x:abs(x[2]-x[1]),reverse=True)[:4];base=w['TCO']['B17'].value
fig,ax=plt.subplots(figsize=(9,4.5));y=np.arange(len(rows));ax.barh(y,[min(a,b)-base for _,a,b in rows],color='#a6bfd3');ax.barh(y,[max(a,b)-base for _,a,b in rows],color='#285879');ax.set_yticks(y,[x[0] for x in rows]);ax.invert_yaxis();ax.axvline(0,color='black',linewidth=.8);ax.set_xlabel('Cambio del VAN a 36 meses frente al caso base (USD)');ax.set_title('Sensibilidad del VAN de la alternativa API (variación ±30 %)');fig.tight_layout();fig.savefig(OUT/'fig3_sensibilidad.png',dpi=200);plt.close(fig)
inside=json.loads((ROOT/'eval_asesor/resultados_asesor_FINAL3.json').read_text());outside=json.loads((ROOT/'eval_asesor/externas/resultados_asesor.json').read_text())
fig,axs=plt.subplots(2,1,figsize=(9,7.5));keys=['correctas','sobredimensionadas','alucinacion','abstenciones'];labs=['Correctas','Sobredim.','Cifras sin\nrespaldo','Abstención']
for ax,d,title,cfgs in [(axs[0],inside,'Interna FINAL3: 32 preguntas × 3',['llm_solo','rag_openai','hibrido','hibrido_local']),(axs[1],outside,'Externa histórica: 31 preguntas × 1',['llm_solo','rag_openai','hibrido','motor_reglas'])]:
 for j,(cfg,color) in enumerate(zip(cfgs,['#9ea5ae','#3d88b8','#184966','#c1944c'])):
  vals=[d['configs'][cfg]['metricas'][k]*100 for k in keys];ax.bar(np.arange(4)+(j-1.5)*.19,vals,.19,label=d['configs'][cfg]['label'],color=color)
 ax.set_xticks(np.arange(4),labs);ax.set_ylim(0,100);ax.set_title(title,fontsize=11);ax.set_ylabel('%');ax.legend(loc='upper right',fontsize=9)
fig.text(.5,.01,'Correctas/abstención/cifras: todas las respuestas. Sobredimensión: casos con referencia respondible (87 internos; 27 externos).',ha='center',fontsize=8);fig.tight_layout(rect=[0,.05,1,1]);fig.savefig(OUT/'fig4_evaluacion.png',dpi=200);plt.close(fig)
# Material visual ya generado para el proyecto, preservado.
import shutil
for fn in ['fig1_escalera.png','fig5_arquitectura.png']:shutil.copy2(ROOT/fn,OUT/fn)
print('5 figuras en',OUT)
