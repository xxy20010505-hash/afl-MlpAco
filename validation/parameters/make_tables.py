import csv
from pathlib import Path
p=Path(__file__).resolve().parent
specs=[('mc_summary.csv','MC sampling diagnostics on synthetic features (not predictive accuracy).',['T','median_latency_us','mean_MAE','std_MAE'],['$T$','Latency ($\mu$s)','Mean MAE','Std. MAE']),('lambda_summary.csv','Acceptance probability under the uncertainty bonus on synthetic features.',['lambda_','mean_acceptance','clipped_fraction'],['$\lambda$','Mean acceptance','Clipping fraction']),('aco_summary.csv','Nonstationary synthetic ACO stress test; ten seeds per setting.',['rho','half_life_updates','phase1_nonzero_runs','phase2_nonzero_runs'],['$\rho$','Half-life (updates)','Phase 1 nonzero runs','Phase 2 nonzero runs'])]
chunks=['% Generated from raw diagnostic results; see PARAMETER_REPORT.md for scope.']
for file,caption,keys,labels in specs:
 rows=list(csv.DictReader((p/file).open()))
 lines=['\\begin{table}[t]','\\centering','\\caption{'+caption+'}','\\begin{tabular}{'+'r'*len(keys)+'}','\\hline',' & '.join(labels)+r' \\','\\hline']
 for row in rows:
  vals=[]
  for k in keys:
   try: v=f'{float(row[k]):.4g}'
   except ValueError:v=row[k]
   if 'e-' in v:
    a,b=v.split('e-');v='$'+a+'\\times 10^{-'+str(int(b))+'}$'
   vals.append(v)
  lines.append(' & '.join(vals)+r' \\')
 lines+=['\\hline','\\end{tabular}','\\end{table}'];chunks.append('\n'.join(lines))
(p/'paper_tables.tex').write_text('\n\n'.join(chunks)+'\n')
