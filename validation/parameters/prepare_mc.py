import sys,torch,onnx,json,platform,subprocess
from pathlib import Path
sys.path.insert(0,'.')
from learner_onnx import SeedModel
root=Path('validation/parameters');torch.manual_seed(20261112)
x=torch.rand(4096,6);x=x*torch.tensor([4.,5.,4.,20.,10.,1.])
y=((x[:,0]/4+x[:,2]/4+0.5*torch.sin(x[:,3]))>1.3).float().unsqueeze(1)
m=SeedModel(6);m.train();opt=torch.optim.Adam(m.parameters(),lr=0.001)
for _ in range(200):
 ix=torch.randint(0,len(x),(64,));opt.zero_grad();loss=torch.nn.functional.binary_cross_entropy(m(x[ix]),y[ix]);loss.backward();opt.step()
torch.onnx.export(m,x[:1],str(root/'diagnostic.onnx'),opset_version=18,training=torch.onnx.TrainingMode.TRAINING,do_constant_folding=False,dynamo=False,input_names=['input'],output_names=['output'])
onnx.checker.check_model(onnx.load(root/'diagnostic.onnx'))
x[:128].numpy().tofile(root/'features.bin')
(root/'environment.json').write_text(json.dumps({'platform':platform.platform(),'torch':torch.__version__,'onnx':onnx.__version__,'cpu':subprocess.check_output(['lscpu'],text=True),'git_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'diagnostic_seed':20261112,'diagnostic_training':'synthetic 4096 examples; 200 batches of 64; not benchmark-derived; not accuracy evidence'},indent=2))
