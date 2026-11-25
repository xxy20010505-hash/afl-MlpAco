FROM gcr.io/fuzzbench/base-image
RUN unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY; apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends git curl ca-certificates redis-server libhiredis0.14 libc++1 libc++abi1 libstdc++6 && rm -rf /var/lib/apt/lists/*
RUN unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY; python3 -m pip install --timeout 180 --retries 5 --no-cache-dir torch==2.4.0+cpu --index-url https://download.pytorch.org/whl/cpu
ARG PYPI_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY; python3 -m pip install --index-url ${PYPI_INDEX_URL} --timeout 180 --retries 5 --no-cache-dir redis==4.6.0 onnx==1.16.2 numpy==1.23.4 protobuf==4.25.5
ARG MLPACO_REF=3c92a0ae3953120a7e89c834193873f3066563c8
RUN unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY; echo "${MLPACO_REF}" | grep -Eq "^[0-9a-f]{40}$" && curl --fail --location --retry 5 --retry-delay 2 --connect-timeout 15 --max-time 180 "https://codeload.github.com/xxy20010505-hash/afl-MlpAco/tar.gz/${MLPACO_REF}" -o /tmp/mlpaco-source.tar.gz && mkdir -p /afl && tar -xzf /tmp/mlpaco-source.tar.gz --strip-components=1 -C /afl && printf "%s\n" "${MLPACO_REF}" > /afl/SOURCE_COMMIT && sha256sum /tmp/mlpaco-source.tar.gz > /afl/SOURCE_ARCHIVE_SHA256 && rm /tmp/mlpaco-source.tar.gz && mkdir -p /opt/onnxruntime && cp -a /afl/onnxruntime/lib /opt/onnxruntime/lib
ENV LD_LIBRARY_PATH=/opt/onnxruntime/lib PYTHONPATH=/afl/diagnostics/AFL_revision
WORKDIR /
