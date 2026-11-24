import sys,time,torch,onnx,redis,numpy as np,onnxruntime as ort
sys.path.insert(0,'.')
from learner_onnx import SeedModel
model=SeedModel(6); model.train()
torch.onnx.export(model,torch.randn(1,6),'validation/mc.onnx',opset_version=18,training=torch.onnx.TrainingMode.TRAINING,do_constant_folding=False,dynamo=False,input_names=['input'],output_names=['output'])
m=onnx.load('validation/mc.onnx');onnx.checker.check_model(m)
assert any(n.op_type=='Dropout' for n in m.graph.node)
r=redis.Redis(port=16379); r.mset({'global_model_main':m.SerializeToString(),'global_model_version':'1'})
print('Export/checker/atomic publication PASS',flush=True)
