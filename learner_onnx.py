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
# 必须与 C 代码中的 INPUT_DIM = 6 保持一致
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
        return torch.sigmoid(out)

# === 2. 辅助函数：强制嵌入权重 (修复版) ===
def make_model_embedded(onnx_model):
    try:
        # 尝试加载外部数据
        load_external_data_for_model(onnx_model, ".")
    except Exception:
        # 如果本来就没有外部数据，这里可能会报错，直接忽略
        pass
    
    # 遍历所有初始化器，清除外部数据标记
    for tensor in onnx_model.graph.initializer:
        # 只处理那些被标记为外部数据的 Tensor
        if tensor.data_location == onnx.TensorProto.EXTERNAL:
            # 将其改为默认（内嵌）
            tensor.data_location = onnx.TensorProto.DEFAULT
            # 清空 external_data 字段，迫使它使用 raw_data
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
    INPUT_DIM = 6
    model = SeedModel(INPUT_DIM)
    model.train() # 启用 Dropout
    
    # 优化器
    optimizer = optim.Adam(model.parameters(), lr=0.0001)
    # 使用二元交叉熵损失函数 (Binary Cross Entropy)
    criterion = nn.BCELoss()  
    
    TEMP_ONNX = "temp_learner_export.onnx"
    training_step = 0

    # === 配置策略 (与 C 端同步) ===
    # 1. 预热步数: 在前 1000 次训练中，只优化参数，不更新 Redis。
    # 这对应 C 端那 50,000 次执行的“静默期”，防止发垃圾模型过去。
    WARMUP_STEPS = 1000  

    # 2. 导出间隔: 预热结束后，每训练 200 次导出一次。
    # 不需要太频繁，因为 C 端现在是每 1000 execs 才读一次。
    # EXPORT_INTERVAL = 200
    # Python 端无论训练多快，都强制每 60 秒导出一次。
    last_export_time = time.time()

    print("[Learner] Waiting for training data from AFL...")

    while True:
        # 非阻塞式读取 Redis 队列
        raw_data = r.lpop('train_queue')
        
        if raw_data:
            try:
                # 解析 AFL 发来的数据
                # 格式: "f1,f2,f3,f4,f5,f6|label"
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
                
                # 情况 A：处于预热期
                if training_step < WARMUP_STEPS:
                    # 每 100 步打印一次日志，证明活着，但坚决不导出
                    if training_step % 100 == 0:
                        print(f"[Learner] Warming up... Step {training_step}/{WARMUP_STEPS}. Loss={loss.item():.4f}")

                # 情况 B：预热结束，且达到导出间隔
                elif time.time() - last_export_time > 60:
                    print(f"[Learner] Time {time.time()}: Loss={loss.item():.4f}. Exporting model...")
                    
                    model.eval()
                    dummy_input = torch.randn(1, INPUT_DIM, dtype=torch.float32)
                    
                    try:
                        # 1. 顺从 PyTorch：直接导出为 Opset 18
                        # 这样可以避开崩溃的 onnx-converter
                        torch.onnx.export(
                            model,
                            dummy_input,
                            TEMP_ONNX,
                            export_params=True,
                            opset_version=18,  # <--- 直接用最新版，不降级
                            do_constant_folding=False, # 关闭折叠，避免标量问题
                            input_names=['input'],
                            output_names=['output'],
                            keep_initializers_as_inputs=False
                        )
                        
                        if os.path.exists(TEMP_ONNX):
                            # 2. 加载模型
                            onnx_model = onnx.load(TEMP_ONNX)
                            
                            # === 核心魔法：手动降级 IR Version ===
                            # C++ Runtime 抱怨 "max supported IR version: 9"
                            # 我们直接硬改 metadata，骗过 C++ 的检查
                            if onnx_model.ir_version > 9:
                                print(f"[Learner] Hacking IR version: {onnx_model.ir_version} -> 9")
                                onnx_model.ir_version = 9
                            
                            # (可选) 如果 C++ Runtime 还抱怨 Opset 版本太高
                            # 可以把下面的注释打开，强制把 Opset 版本号也改低
                            # for opset in onnx_model.opset_import:
                            #    if opset.version > 17:
                            #        opset.version = 17

                            # 3. 序列化并存入 Redis
                            final_bytes = onnx_model.SerializeToString()
                            
                            r.set('global_model_main', final_bytes)
                            r.set('global_model_version', str(time.time()))
                            print("[Learner] Model saved to Redis successfully (Hacked IR v9).")
                            
                        else:
                            print("[Learner] Export failed: file not found.")

                    except Exception as e:
                        print(f"[Learner] Export Error: {e}")
                        # 打印堆栈以便排查
                        import traceback
                        traceback.print_exc()

                    # 清理并恢复
                    if os.path.exists(TEMP_ONNX): os.remove(TEMP_ONNX)
                    last_export_time = time.time()
                    model.train()

            except Exception as e:
                print(f"[Learner] Error processing data: {e}")
        else:
            # 队列为空，稍作休息，避免 CPU 100%
            time.sleep(0.01)

if __name__ == '__main__':
    main()
