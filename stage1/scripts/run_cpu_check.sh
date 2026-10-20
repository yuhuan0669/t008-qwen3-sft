#!/usr/bin/env bash
set -euo pipefail
# Invoke on worker05; no GPU devices, no Kubernetes workload changes.
TASK_ROOT=/tmp/t008-stage1-cpu-20261020
BASE_MODEL=/var/lib/kubelet/pods/26d7f32e-ee55-4a1b-bca8-941e6163ced6/volumes/kubernetes.io~nfs/pvc-70f17a58-94f3-4a2b-a947-3e7dac05e509/released/qwen3-8b-baseline/model
IMAGE=modelscope-registry.cn-hangzhou.cr.aliyuncs.com/modelscope-repo/modelscope@sha256:822d99beed4984a421c8d1da397993c6a8a5f88cdad7dde940bd52df0067d738
mkdir -p "$TASK_ROOT/stage1/evidence" "$TASK_ROOT/cache"
chmod a+rwx "$TASK_ROOT/stage1/evidence" "$TASK_ROOT/cache"
# The only writable inputs are this task's derivative directory and run config.
chown -R 10001:10001 "$TASK_ROOT/stage1/data" "$TASK_ROOT/stage1/training"
nerdctl --namespace k8s.io run --detach --name "${CPU_CONTAINER_NAME:-t008-stage1-cpu-20261020}" \
 --runtime io.containerd.runc.v2 --cpus 2 --memory 8g --user 10001:10001 \
 --env USER=t008-cpu --env LOGNAME=t008-cpu --env CUDA_VISIBLE_DEVICES= --env NVIDIA_VISIBLE_DEVICES=void \
 --env MODELSCOPE_CACHE=/work/cache/modelscope --env MODELSCOPE_HOME=/work/cache/modelscope-home \
 --env HF_HOME=/work/cache/hf --env XDG_CACHE_HOME=/work/cache/xdg --env OMP_NUM_THREADS=2 \
 --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 \
 --mount "type=bind,src=$TASK_ROOT,dst=/work" \
 --mount "type=bind,src=$BASE_MODEL,dst=/base,ro" \
 --mount type=bind,src=/tmp/t008-native-entry-cpu-20261019/ast_index_file.py,dst=/usr/local/lib/python3.12/site-packages/modelscope/utils/ast_index_file.py,ro \
 "$IMAGE" sh -c 'python3 /work/stage1/scripts/cpu_encode.py > /work/stage1/evidence/cpu-encoding.log 2>&1 && python3 /work/stage1/scripts/build_run_spec.py && python3 /work/stage1/scripts/check_recipe.py > /work/stage1/evidence/recipe-validation.log 2>&1 && python3 /work/stage1/scripts/check_template_alignment.py > /work/stage1/evidence/template-alignment.log 2>&1'
