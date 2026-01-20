#!/usr/bin/env python3
import torch
import torch.nn as nn
import torch.optim as optim
import redis
import time
import os
import onnx
from onnx.external_data_helper import load_external_data_for_model

# === [修改点 1] 限制 CPU 线程数 ===
# Fuzzing 环境下 CPU 资源宝贵，限制 PyTorch 只用单核
# 避免与 AFL 争抢 CPU 资源，反而能提高整体吞吐量
torch.set_num_threads(1)
torch.set_num_interop_threads(1)

# === 1. 定义模型 ===
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

# === 2. 辅助函数：强制嵌入权重 ===
def make_model_embedded(onnx_model):
    try:
        load_external_data_for_model(onnx_model, ".")
    except Exception:
        pass
    
    for tensor in onnx_model.graph.initializer:
        if tensor.data_location == onnx.TensorProto.EXTERNAL:
            tensor.data_location = onnx.TensorProto.DEFAULT
            del tensor.external_data[:]
            
    return onnx_model

# === 3. 主循环 ===
def main():
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("[Learner] Successfully connected to Redis.")
    except Exception as e:
        print(f"[Learner] Redis connection failed: {e}")
        return

    # 初始化
    INPUT_DIM = 6
    model = SeedModel(INPUT_DIM)
    model.train() 
    
    optimizer = optim.Adam(model.parameters(), lr=0.0001)
    criterion = nn.BCELoss()  
    
    TEMP_ONNX = "temp_learner_export.onnx"
    training_step = 0

    # === [修改点 2] 批量训练配置 ===
    # 现在这里的 STEP 指的是 "Batch Step"
    # 500 个 Batch * 64 条数据 = 32,000 条数据
    # 这样的预热量比之前更有意义，模型会更稳定
    WARMUP_STEPS = 500  
    BATCH_SIZE = 64     # 每次处理 64 条数据 (根据你的 top 截图，内存完全够用)
    
    last_export_time = time.time()

    print(f"[Learner] Waiting for training data from AFL... (Batch Size: {BATCH_SIZE})")

    while True:
        # === [修改点 3] 使用 Pipeline 批量读取 ===
        # 以前是一次读一条 (RTT 高)，现在是一次读 64 条 (RTT 低)
        pipe = r.pipeline()
        for _ in range(BATCH_SIZE):
            pipe.lpop('train_queue')
        
        try:
            raw_batch = pipe.execute() # 一次网络请求拿回所有数据
        except Exception as e:
            print(f"[Learner] Redis Error: {e}")
            time.sleep(1)
            continue

        # 过滤掉 None (如果队列里的数据不足 BATCH_SIZE，会有 None)
        valid_data = [x for x in raw_batch if x is not None]

        # 如果这一轮完全没数据，才休息。只要有数据（哪怕只有 1 条）也立即训练！
        if not valid_data:
            time.sleep(0.01) # 避免死循环空转 CPU
            continue

        # === [修改点 4] 批量解析数据 ===
        batch_features = []
        batch_labels = []

        for raw_bytes in valid_data:
            try:
                data_str = raw_bytes.decode('utf-8')
                feat_str, label_str = data_str.split('|')
                
                features = list(map(float, feat_str.split(',')))
                label_val = float(label_str)
                
                batch_features.append(features)
                # 注意：PyTorch 要求 label 是二维的 [[1], [0], ...]
                batch_labels.append([label_val]) 
            except Exception:
                continue # 跳过损坏的数据
        
        if not batch_features:
            continue

        # 一次性转换为 Tensor (效率极高)
        try:
            input_tensor = torch.tensor(batch_features, dtype=torch.float32)
            target_tensor = torch.tensor(batch_labels, dtype=torch.float32)

            # === [修改点 5] 批量训练 (Batch Training) ===
            optimizer.zero_grad()
            output = model(input_tensor)
            loss = criterion(output, target_tensor)
            loss.backward()
            optimizer.step()
            
            training_step += 1
            
            # --- 下面的逻辑基本保持不变，只是基于 step 的判断 ---

            # 情况 A：处于预热期
            if training_step < WARMUP_STEPS:
                if training_step % 50 == 0: # 稍微减少打印频率
                    print(f"[Learner] Warming up... Batch {training_step}/{WARMUP_STEPS}. Loss={loss.item():.4f}")

            # 情况 B：预热结束，且达到导出间隔
            elif time.time() - last_export_time > 60:
                print(f"[Learner] Time {time.time()}: Loss={loss.item():.4f}. Exporting model...")
                
                model.eval()
                # 导出时只需要一个 dummy 输入即可，batch size 可以是 1
                dummy_input = torch.randn(1, INPUT_DIM, dtype=torch.float32)
                
                try:
                    torch.onnx.export(
                        model,
                        dummy_input,
                        TEMP_ONNX,
                        export_params=True,
                        opset_version=18, 
                        do_constant_folding=False,
                        input_names=['input'],
                        output_names=['output'],
                        keep_initializers_as_inputs=False
                    )
                    
                    if os.path.exists(TEMP_ONNX):
                        onnx_model = onnx.load(TEMP_ONNX)
                        
                        # Hacking IR version
                        if onnx_model.ir_version > 9:
                            # print(f"[Learner] Hacking IR version: {onnx_model.ir_version} -> 9")
                            onnx_model.ir_version = 9
                        
                        final_bytes = onnx_model.SerializeToString()
                        
                        r.set('global_model_main', final_bytes)
                        r.set('global_model_version', str(time.time()))
                        print("[Learner] Model saved to Redis successfully.")
                        
                    else:
                        print("[Learner] Export failed: file not found.")

                except Exception as e:
                    print(f"[Learner] Export Error: {e}")
                    import traceback
                    traceback.print_exc()

                # 清理并恢复
                if os.path.exists(TEMP_ONNX): os.remove(TEMP_ONNX)
                last_export_time = time.time()
                model.train()

        except Exception as e:
            print(f"[Learner] Error processing batch: {e}")

if __name__ == '__main__':
    main()
