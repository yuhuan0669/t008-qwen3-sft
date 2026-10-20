#!/usr/bin/env bash
set -euo pipefail
# Run on worker05 only, after staging code in this NEW isolated CPU directory.
ROOT=/tmp/t008-native-entry-cpu-20261019
IMAGE=modelscope-registry.cn-hangzhou.cr.aliyuncs.com/modelscope-repo/modelscope@sha256:822d99beed4984a421c8d1da397993c6a8a5f88cdad7dde940bd52df0067d738
BASE=/var/lib/kubelet/pods/4cdca1ae-c999-4ef5-807f-1807e215005f/volumes/kubernetes.io~nfs/pvc-70f17a58-94f3-4a2b-a947-3e7dac05e509/released/qwen3-8b-baseline/model
COMMON=(--runtime io.containerd.runc.v2 --cpus 2 --memory 8g --user 10001:10001
 --env USER=t008-cpu --env LOGNAME=t008-cpu --env CUDA_VISIBLE_DEVICES= --env NVIDIA_VISIBLE_DEVICES=void
 --env MODELSCOPE_HOME=/work/cache/modelscope-home --env MODELSCOPE_CACHE=/work/cache/modelscope --env HF_HOME=/work/cache/huggingface
 --env REQUESTS_CA_BUNDLE=/work/trust-bundle.pem --env SSL_CERT_FILE=/work/trust-bundle.pem --env XDG_CACHE_HOME=/work/cache/xdg --env OMP_NUM_THREADS=2 --env PYTHONPATH=/work/code
 --mount "type=bind,src=$ROOT,dst=/work"
 --mount type=bind,src=/tmp/t008-identity-v12-cpu-20261019,dst=/reference,ro
 --mount "type=bind,src=$BASE,dst=/base,ro")
if [[ ${1:-} == init ]]; then
 nerdctl --namespace k8s.io run --name t008-native-entry-ast-init "${COMMON[@]}" "$IMAGE" python3 -c "from modelscope.utils.ast_utils import generate_ast_template; generate_ast_template(file_path='/work/ast_index_file.py')"
elif [[ ${1:-} == checks ]]; then
 nerdctl --namespace k8s.io run --detach --name t008-native-entry-cpu-checks "${COMMON[@]}" \
 --mount "type=bind,src=$ROOT/ast_index_file.py,dst=/usr/local/lib/python3.12/site-packages/modelscope/utils/ast_index_file.py,ro" \
 "$IMAGE" sh -c 'cd /work/code && python3 -W error::ResourceWarning -m unittest discover -s tests -v > /work/image-tests.log 2>&1 && python3 /work/check_final_save.py --out /work/final-save-callback.json > /work/final-save-callback.log 2>&1 && python3 /work/check_native_guard.py --proof /work/native-proof-final-v3/native-preflight.json --out /work/native-guard-checks.json > /work/native-guard-checks.log 2>&1'
else
 nerdctl --namespace k8s.io run --detach --name t008-native-entry-cpu-final-v3 "${COMMON[@]}" \
 --mount "type=bind,src=$ROOT/ast_index_file.py,dst=/usr/local/lib/python3.12/site-packages/modelscope/utils/ast_index_file.py,ro" \
 "$IMAGE" sh -c 'cd /work/code && bash train_identity.sh cpu-check --model /base --identity-spec identity-spec.example.json --evidence-dir /work/native-proof-final-v3 --reference-snapshot /reference/original-v1.2/train.jsonl --base-files /reference/evidence/template/original-final/base-files.json > /work/cpu-check-final-v3.log 2>&1'
fi
