#!/usr/bin/env python3
import torch
import torch.nn as nn
import torch.optim as optim
import redis
import time
import os
import onnx
from onnx.external_data_helper import load_external_data_for_model

# === 1. 定义模型 ===
# 必须与 C 代码中的 INPUT_DIM = 5 保持一致
# 特征顺序: [exec_us, len, bitmap_size, depth, handicap]
class SeedModel(nn.Module):
    def __init__(self, input_dim):
        super(SeedModel, self).__init__()
        self.fc1 = nn.Linear(input_dim, 64)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(p=0.2)
        
        self.fc2 = nn.Linear(64, 32)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(p=0.2)
        
        # 输出层：预测该种子的“能量/价值”
        self.fc3 = nn.Linear(32, 1)

    def forward(self, x):
        out = self.fc1(x)
        out = self.relu1(out)
        out = self.dropout1(out)
        
        out = self.fc2(out)
        out = self.relu2(out)
        out = self.dropout2(out)
        
        out = self.fc3(out)
        return torch.sigmoid(out) * 3200

# === 2. 辅助函数：强制嵌入权重 ===
# 解决 ONNX Runtime 加载外部文件导致的段错误问题
def make_model_embedded(onnx_model):
    # 强制加载外部数据到内存对象
    load_external_data_for_model(onnx_model, ".")
    
    # 清除“外部数据”标记，让 ONNX 认为这是原生内嵌数据
    for tensor in onnx_model.graph.initializer:
        if tensor.data_location == onnx.TensorProto.EXTERNAL:
            tensor.data_location = onnx.TensorProto.DEFAULT
            del tensor.external_data[:]
            
    return onnx_model

# === 3. 主循环 ===
def main():
    # 连接 Redis (与 C 端 init_redis 对应)
    # 如果连接失败会抛出异常，AFL C 端会捕获进程退出信号
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("[Learner] Successfully connected to Redis.")
    except Exception as e:
        print(f"[Learner] Redis connection failed: {e}")
        return

    # 初始化
    INPUT_DIM = 5
    model = SeedModel(INPUT_DIM)
    model.train() # 启用 Dropout
    
    # 优化器
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()
    
    TEMP_ONNX = "temp_learner_export.onnx"
    training_step = 0

    print("[Learner] Waiting for training data from AFL...")

    while True:
        # 非阻塞式读取 Redis 队列
        raw_data = r.lpop('train_queue')
        
        if raw_data:
            try:
                # 解析 AFL 发来的数据
                # 格式: "f1,f2,f3,f4,f5|label"
                data_str = raw_data.decode('utf-8')
                feat_str, label_str = data_str.split('|')
                
                features = list(map(float, feat_str.split(',')))
                label_val = float(label_str)
                
                # 转换为 Tensor
                input_tensor = torch.tensor([features], dtype=torch.float32)
                target_tensor = torch.tensor([[label_val]], dtype=torch.float32)
                
                # 训练一步
                optimizer.zero_grad()
                output = model(input_tensor)
                loss = criterion(output, target_tensor)
                loss.backward()
                optimizer.step()
                
                training_step += 1
                
                # === 定期导出模型 (例如每 1000 次训练) ===
                if training_step % 1000 == 0:
                    print(f"[Learner] Step {training_step}: Loss={loss.item():.4f}. Exporting model...")
                    
                    # 切换到评估模式导出 (或者保持训练模式以利用 Dropout 做贝叶斯推断，这里按标准导出)
                    model.eval()
                    dummy_input = torch.randn(1, INPUT_DIM)
                    
                    # 1. 导出到临时文件
                    torch.onnx.export(
                        model,
                        dummy_input,
                        TEMP_ONNX,
                        export_params=True,
                        opset_version=18, 
                        do_constant_folding=True,
                        input_names=['input'],
                        output_names=['output'],
                        dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
                    )
                    
                    # 2. 重新加载并嵌入权重 (内存化)
                    onnx_model = onnx.load(TEMP_ONNX)
                    onnx_model = make_model_embedded(onnx_model)
                    final_bytes = onnx_model.SerializeToString()
                    
                    # 3. 存入 Redis
                    # 这是一个原子操作，C 端读取时不会读到残缺数据
                    r.set('global_model_main', final_bytes)
                    
                    # 4. 更新版本号 (C 端监控这个 Key 变化)
                    r.set('global_model_version', str(time.time()))
                    
                    # 5. 清理临时文件
                    if os.path.exists(TEMP_ONNX): os.remove(TEMP_ONNX)
                    if os.path.exists(TEMP_ONNX + ".data"): os.remove(TEMP_ONNX + ".data")
                    
                    # 恢复训练模式
                    model.train()

            except Exception as e:
                print(f"[Learner] Error processing data: {e}")
        else:
            # 队列为空，稍作休息，避免 CPU 100%
            time.sleep(0.01)

if __name__ == '__main__':
    main()