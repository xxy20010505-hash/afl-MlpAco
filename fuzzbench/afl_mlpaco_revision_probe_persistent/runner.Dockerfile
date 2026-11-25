FROM gcr.io/fuzzbench/base-image
ARG MLPACO_REF=3c92a0ae3953120a7e89c834193873f3066563c8
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates redis-server libhiredis0.14 libc++1 libc++abi1 libstdc++6 && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir torch==2.4.0+cpu --index-url https://download.pytorch.org/whl/cpu && python3 -m pip install --no-cache-dir redis==5.0.8 onnx==1.16.2 numpy==1.24.4 protobuf==4.25.5
RUN git init /afl && cd /afl && git remote add origin https://github.com/xxy20010505-hash/afl-MlpAco.git && git fetch --depth 1 origin ${MLPACO_REF} && git checkout --detach FETCH_HEAD && mkdir -p /opt/onnxruntime && cp -a /afl/onnxruntime/lib /opt/onnxruntime/lib
ENV LD_LIBRARY_PATH=/opt/onnxruntime/lib PYTHONPATH=/afl/diagnostics/AFL_revision
WORKDIR /
