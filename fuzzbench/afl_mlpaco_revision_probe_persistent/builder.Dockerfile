ARG parent_image
FROM $parent_image
ARG MLPACO_REF=d071369b930a7c4d0077c7f51e0418c67a469e47
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates make libhiredis-dev clang-12 llvm-12 llvm-12-dev libc++-12-dev libc++abi-12-dev zlib1g-dev && rm -rf /var/lib/apt/lists/*
RUN git init /afl && cd /afl && git remote add origin https://github.com/xxy20010505-hash/afl-MlpAco.git && git fetch --depth 1 origin ${MLPACO_REF} && git checkout --detach FETCH_HEAD
WORKDIR /afl
ENV LD_LIBRARY_PATH=/afl/onnxruntime/lib
RUN cp diagnostics/AFL_revision/* . && AFL_NO_X86=1 make CC=clang-12 CXX=clang++-12 afl-fuzz afl-showmap && python3 -c 'import json,subprocess; json.dump({"variant":"AFL_revision","commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()},open("build_identity.json","w"))'
RUN clang-12 -O3 -Wall -g -Wno-pointer-sign -DAFL_PATH=\"/afl\" -DBIN_PATH=\"/usr/bin\" -DVERSION=\"2.57b\" llvm_mode/afl-clang-fast.c -o afl-clang-fast && clang++-12 -O3 -fno-rtti -fPIC -shared $(llvm-config-12 --cxxflags) llvm_mode/afl-llvm-pass.so.cc -o afl-llvm-pass.so && clang-12 -O3 -fPIC -c llvm_mode/afl-llvm-rt.o.c -o afl-llvm-rt.o && ln -sf afl-clang-fast afl-clang-fast++ && ln -sf /afl/afl-clang-fast /usr/bin/afl-clang-fast && ln -sf /afl/afl-clang-fast++ /usr/bin/afl-clang-fast++
RUN clang++-12 -stdlib=libc++ -std=c++11 -O2 -c afl_driver.cpp -o /tmp/afl_driver.o && ar rcs /libAFL.a /tmp/afl_driver.o
ENV AFL_PATH=/afl AFL_CC=clang-12 AFL_CXX=clang++-12 CC=/usr/bin/afl-clang-fast CXX=/usr/bin/afl-clang-fast++ FUZZER_LIB=/libAFL.a
