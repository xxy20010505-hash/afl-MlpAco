ARG parent_image
FROM gcr.io/fuzzbench/base-image AS source_fetch
ARG MLPACO_REF=7561fe50da24608f8263f7cccd083edd3470a3c4
RUN unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY; echo "${MLPACO_REF}" | grep -Eq "^[0-9a-f]{40}$" && curl --ipv4 --http1.1 --fail --location --retry 5 --retry-delay 2 --connect-timeout 15 --max-time 900 "https://codeload.github.com/xxy20010505-hash/afl-MlpAco/tar.gz/${MLPACO_REF}" -o /tmp/mlpaco-source.tar.gz && mkdir -p /afl && tar -xzf /tmp/mlpaco-source.tar.gz --strip-components=1 -C /afl && printf "%s\n" "${MLPACO_REF}" > /afl/SOURCE_COMMIT && sha256sum /tmp/mlpaco-source.tar.gz > /afl/SOURCE_ARCHIVE_SHA256 && rm /tmp/mlpaco-source.tar.gz
FROM $parent_image
RUN unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY; apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends git curl ca-certificates make libhiredis-dev clang-12 llvm-12 llvm-12-dev libc++-12-dev libc++abi-12-dev zlib1g-dev && rm -rf /var/lib/apt/lists/*
COPY --from=source_fetch /afl /afl
WORKDIR /afl
ENV LD_LIBRARY_PATH=/afl/onnxruntime/lib
RUN cp diagnostics/AFL/* . && AFL_NO_X86=1 make CC=clang-12 CXX=clang++-12 afl-fuzz afl-showmap && python3 diagnostics/write_build_identity.py AFL
RUN clang-12 -O3 -Wall -g -Wno-pointer-sign -DAFL_PATH=\"/afl\" -DBIN_PATH=\"/usr/bin\" -DVERSION=\"2.57b\" llvm_mode/afl-clang-fast.c -o afl-clang-fast && clang++-12 -O3 -fno-rtti -fPIC -shared $(llvm-config-12 --cxxflags) llvm_mode/afl-llvm-pass.so.cc -o afl-llvm-pass.so && clang-12 -O3 -fPIC -c llvm_mode/afl-llvm-rt.o.c -o afl-llvm-rt.o && ln -sf afl-clang-fast afl-clang-fast++ && ln -sf /afl/afl-clang-fast /usr/bin/afl-clang-fast && ln -sf /afl/afl-clang-fast++ /usr/bin/afl-clang-fast++
RUN clang++-12 -stdlib=libc++ -std=c++11 -O2 -c afl_driver.cpp -o /tmp/afl_driver.o && ar rcs /libAFL.a /tmp/afl_driver.o
ENV AFL_PATH=/afl AFL_CC=clang-12 AFL_CXX=clang++-12 CC=/usr/bin/afl-clang-fast CXX=/usr/bin/afl-clang-fast++ FUZZER_LIB=/libAFL.a
