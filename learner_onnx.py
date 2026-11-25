from learner_profile import micro_scope
import torch
import torch.nn as nn
import torch.optim as optim
import redis
import time
import os
import onnx
from onnx.external_data_helper import load_external_data_for_model
torch.set_num_threads(1)
torch.set_num_interop_threads(1)

class SeedModel(nn.Module):

    def __init__(self, input_dim):
        super(SeedModel, self).__init__()
        self.fc1 = nn.Linear(input_dim, 64)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(p=0.2)
        self.fc2 = nn.Linear(64, 32)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(p=0.2)
        self.fc3 = nn.Linear(32, 1)

    def forward(self, x):
        out = self.fc1(x)
        out = self.relu1(out)
        out = self.dropout1(out)
        out = self.fc2(out)
        out = self.relu2(out)
        out = self.dropout2(out)
        out = self.fc3(out)
        return torch.sigmoid(out)

def make_model_embedded(onnx_model):
    try:
        load_external_data_for_model(onnx_model, '.')
    except Exception:
        pass
    for tensor in onnx_model.graph.initializer:
        if tensor.data_location == onnx.TensorProto.EXTERNAL:
            tensor.data_location = onnx.TensorProto.DEFAULT
            del tensor.external_data[:]
    return onnx_model

def main():
    try:
        r = redis.Redis(host='localhost', port=int(os.getenv('AFL_REDIS_PORT', '6379')), db=0)
        r.ping()
        print('[Learner] Successfully connected to Redis.')
    except Exception as e:
        print(f'[Learner] Redis connection failed: {e}')
        return
    if os.getenv('AFL_TORCH_SEED'):
        torch.manual_seed(int(os.environ['AFL_TORCH_SEED']))
    INPUT_DIM = 6
    model = SeedModel(INPUT_DIM)
    model.train()
    optimizer = optim.Adam(model.parameters(), lr=0.0001)
    criterion = nn.BCELoss()
    TEMP_ONNX = 'temp_learner_export.onnx'
    training_step = 0
    metrics_file = None
    if os.getenv('AFL_LEARNER_METRICS'):
        metrics_file = open(os.environ['AFL_LEARNER_METRICS'], 'w', buffering=1)
        metrics_file.write('unix_time,step,samples,positives,loss\n')
    WARMUP_STEPS = int(os.getenv('AFL_LEARNER_WARMUP_STEPS', '500'))
    BATCH_SIZE = 64
    last_export_time = time.time()
    print(f'[Learner] Waiting for training data from AFL... (Batch Size: {BATCH_SIZE})')
    while True:
        pipe = r.pipeline()
        for _ in range(BATCH_SIZE):
            pipe.lpop('train_queue')
        try:
            with micro_scope('redis_fetch'):
                raw_batch = pipe.execute()
        except Exception as e:
            print(f'[Learner] Redis Error: {e}')
            time.sleep(1)
            continue
        valid_data = [x for x in raw_batch if x is not None]
        if not valid_data:
            time.sleep(0.01)
            continue
        batch_features = []
        batch_labels = []
        for raw_bytes in valid_data:
            try:
                data_str = raw_bytes.decode('utf-8')
                feat_str, label_str = data_str.split('|')
                features = list(map(float, feat_str.split(',')))
                label_val = float(label_str)
                batch_features.append(features)
                batch_labels.append([label_val])
            except Exception:
                continue
        if not batch_features:
            continue
        try:
            input_tensor = torch.tensor(batch_features, dtype=torch.float32)
            target_tensor = torch.tensor(batch_labels, dtype=torch.float32)
            optimizer.zero_grad()
            with micro_scope('train_forward'):
                output = model(input_tensor)
            loss = criterion(output, target_tensor)
            with micro_scope('train_backward'):
                loss.backward()
            with micro_scope('optimizer'):
                optimizer.step()
            training_step += 1
            from learner_profile import record_batch
            record_batch(len(batch_features), sum(x[0] for x in batch_labels), float(loss.item()))
            if metrics_file:
                metrics_file.write(f'{time.time()},{training_step},{len(batch_features)},{sum((x[0] for x in batch_labels))},{loss.item()}\n')
            if training_step < WARMUP_STEPS:
                if training_step % 100 == 0:
                    print(f'[Learner] Warming up... Batch {training_step}/{WARMUP_STEPS}. Loss={loss.item():.4f}')
            elif time.time() - last_export_time > float(os.getenv('AFL_MODEL_EXPORT_SECONDS', '60')):
                model.train(not bool(os.getenv('AFL_NO_MC_DROPOUT')))
                dummy_input = torch.randn(1, INPUT_DIM, dtype=torch.float32)
                try:
                    with micro_scope('onnx_export'):
                        torch.onnx.export(model, dummy_input, TEMP_ONNX, export_params=True, training=torch.onnx.TrainingMode.EVAL if os.getenv('AFL_NO_MC_DROPOUT') else torch.onnx.TrainingMode.TRAINING, dynamo=False, opset_version=18, do_constant_folding=False, input_names=['input'], output_names=['output'], keep_initializers_as_inputs=False)
                    if os.path.exists(TEMP_ONNX):
                        with micro_scope('onnx_load'):
                            onnx_model = onnx.load(TEMP_ONNX)
                        if onnx_model.ir_version > 9:
                            onnx_model.ir_version = 9
                        final_bytes = onnx_model.SerializeToString()
                        with micro_scope('redis_publish'):
                            r.mset({'global_model_main': final_bytes, 'global_model_version': str(training_step)})
                    else:
                        print('[Learner] Export failed: file not found.')
                except Exception as e:
                    print(f'[Learner] Export Error: {e}')
                    import traceback
                    traceback.print_exc()
                if os.path.exists(TEMP_ONNX):
                    os.remove(TEMP_ONNX)
                last_export_time = time.time()
                model.train()
        except Exception as e:
            print(f'[Learner] Error processing batch: {e}')
if __name__ == '__main__':
    main()
